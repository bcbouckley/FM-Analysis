import streamlit as st
import pandas as pd
import numpy as np
import re
import unicodedata

## Idea: select team that won the league and use them as a comparison tool/best player in the league.

# Page Setup
## Set page Title
st.set_page_config(page_title="FM Moneyball", layout="wide")
st.title("FM26 Moneyball App")


# Data Functions and processing
## Match accents
def strip_accents(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.category(c).startswith('M'))


## File uploader
def load_data(uploaded_file, possession_file):
    df = pd.read_csv(uploaded_file, sep=';')
    
    # load and process possession data
    df_poss = pd.read_csv(possession_file)
    df_poss['Possession'] = df_poss['Possession'].str.rstrip('%').astype(float) / 100
    
    # Match on accent-stripped club names
    df['_key'] = df['Club'].apply(strip_accents)
    df_poss['_key'] = df_poss['Club'].apply(strip_accents)
    
    df = df.merge(df_poss[['_key', 'Possession']], on='_key', how='left')
    df.drop(columns=['_key'], inplace=True)
    
    df = derived_columns(df)
    return df

## Column Grouping
desc_cols = [
    "Division",
    "Club",
    "Possession",
    "Player",
    "Best Pos",
    "Sec. Position",
    "Position",
    "Age",
    "Height",
    "Left Foot",
    "Right Foot",
    "Recurring Injury",
    "Injury Susceptibility",
    "Wage",
    "Transfer Value", 
]
# Add stats per touch
# Add pizza group stats
pizzacat= {
    "Defence": [
        {"name": "Front-foot defending", "method": "derived_composite", 
        "components": ["P-ad Tck/90", "P-ad Int/90", "Pres A/90", "P-ad Fouls/90", "P-ad Blk/90"]},
        {"name": "Tackle success", "method": "single", "col": "Tck R"},
        {"name": "Back-foot defending", "method": "derived_composite",
        "components": ["P-ad Shts Blckd/90", "P-ad Clr/90"]},
        {"name": "Loose ball recoveries", "method": "single", "col": "P-ad Poss Won/90"},
        {"name": "Aerial volume", "method": "single", "col": "Aer A/90"},
        {"name": "Aerial success", "method": "single", "col": "Hdr %"},
    ],
    "Possession": [
        {"name": "Ball retention", "method": "single", "col": "Pas %"},
        {"name": "Link-up play", "method": "single", "col": "Link-up Rate"},
        {"name": "Progressive Rate", "method": "single", "col": "Progressive Rate"},
    ],
    "Progression": [
        {"name": "Creative threat", "method": "derived_composite",
        "components": ["xA/90","Asts/90"]},
        {"name": "Risk Rate", "method": "single", "col": "Risky Pass Rate"},
        {"name": "OP crossing volume", "method": "single", "col": "Crs Volume"},
        {"name": "OP crossing accuracy", "method": "single", "col": "OP-Cr %"},
        {"name": "Progressive Volume", "method": "single", "col": "Pr passes/90"},
        {"name": "Dribble Volume", "method": "single", "col": "Drb Vol"},
    ],
    "Attack": [
        {"name": "Goal threat", "method": "derived_composite",
        "components": ["xG/90", "Goals/90_derived"]},
        {"name": "Shot frequency", "method": "single", "col": "Shot/90"},
        {"name": "Shot quality", "method": "single", "col": "xG/shot"},
    ],
}

position_stat_groups = {
    "ST": [
        # Scoring
        "P-ad G/90", "P-ad NP-xG/90", "Conv %", "xG/shot", "Shot Bias", "Scoring Dependency",
        #"NP-xG/90", "xG-OP", "Shot/90", "ShT/90", "Goals per 90 minutes", "Longshots Scored/90", "Shots From Outside The Box Per 90 minutes", "Shot %",
        
        # Passing
        "P-ad A/90", "P-ad xA/90", "P-ad OP-KP/90", "Risky Pass Rate",
        # Crossing
        
        # Movement
        "Drb Vol", "P-ad Offside/90",
        # Defending
        "P-ad Pres A/90", "P-ad Poss Won/90", "P-ad Fouls/90",
        # Physicality
        "Aer Imp",
        "Sprints/90", "Aer A/90", "Hdr %", "K Hdrs/90",

        # Scoring
        # "P-ad Shot/90", "P-ad ShT/90", "P-ad Longshots Scored/90", "P-ad Longshots/90",
        # Passing
        # "P-ad Passes/90", "P-ad Ch C/90",  "Asts/90", "xA/90", "Ps A/90", "Ch C/90", "OP-KP/90",
        # Crossing
        "P-ad OP-Crs A/90", "P-ad OP-Crs C/90", "OP-Crs A/90", "OP-Crs C/90", "OP-Cr %",
        # Movement
        # "Drb/90", "Fouls Drawn/90",  "Offside/90", "Poss Lost/90", "P-ad Drb/90", "P-ad Fouls Drawn/90", "P-ad Offside/90", "P-ad Poss Lost/90",
        # Defending
        "Pres A/90", "Poss Won/90", "Tck R", "Fouls/90",
        
        "Fouls/Yellow", "Fouls/Red",
    ],
    "AM": [
        # Scoring
        "Goals per 90 minutes", "NP-xG/90", "xG-OP", "Conv %", "xG/shot", "Shot/90", "ShT/90", 
        "Longshots Scored/90", "Shots From Outside The Box Per 90 minutes", "Shot %",
        "Shot Bias",
        # Passing
        "Asts/90", "xA/90", "Ps A/90", "Ch C/90", "OP-KP/90", "Risky Pass Rate",
        # Crossing
        "OP-Crs A/90", "OP-Crs C/90", "OP-Cr %",
        # Movement
        "Drb/90", "Fouls Drawn/90",  "Offside/90", "Poss Lost/90",
        # Defending
        "Pres A/90", "Poss Won/90", "Tck R", "Fouls/90",
        # Physicality
        "Sprints/90", "Aer A/90", "Hdr %", "K Hdrs/90",

        # Scoring
        "P-ad G/90", "P-ad NP-xG/90", "P-ad Shot/90", "P-ad ShT/90",
        "P-ad Longshots Scored/90", "P-ad Longshots/90",
        # Passing
        "P-ad A/90", "P-ad xA/90", "P-ad Passes/90", "P-ad Ch C/90", "P-ad OP-KP/90",
        # Crossing
        "P-ad OP-Crs A/90", "P-ad OP-Crs C/90",
        # Movement
        "P-ad Drb/90", "P-ad Fouls Drawn/90", "P-ad Offside/90", "P-ad Poss Lost/90",
        # Defending
        "P-ad Pres A/90", "P-ad Poss Won/90", "P-ad Fouls/90",
        "Fouls/Yellow", "Fouls/Red",
    ],
    "M": [
        # Combined important data


        ### Scoring
        "xG/shot", "Shot/90", "ShT/90",
        "Longshots Scored/90", "Shots From Outside The Box Per 90 minutes", "Shot %",


        ### Passing
        "Asts/90", "xA/90", "Ch C/90", "OP-KP/90", "Risky Pass Rate",
        "Pr passes/90", "Progressive Rate",
        "Pas %", "Ps A/90", "Poss Lost/90",

        ### Player Movement
        "Drb/90", "Fouls Drawn/90",

        ### Defending
        "Int/90", "Poss Won/90",
        "Pres A/90", "K Tck/90", "Tck/90", "Tck R",

        ### Physicality - running
        "Dist/90", "Sprints/90",

        ### Physicality - Heading
        "Aer A/90", "Hdr %", "K Hdrs/90",

        ### Discipline
        "Fouls/90", "Yel", "Red cards", "Fouls/Yellow", "Fouls/Red",

        ## Possession Adjusted

        ### Scoring
        "P-ad Shot/90", "P-ad ShT/90",
        "P-ad Longshots Scored/90", "P-ad Longshots/90", 

        ### Passing
        "P-ad A/90", "P-ad xA/90", "P-ad Ch C/90", "P-ad OP-KP/90",
        "P-ad Pr Passes/90",
        "P-ad Passes/90", "P-ad Poss Lost/90",

        ### Player Movement
        "P-ad Drb/90", "P-ad Fouls Drawn/90",

        ### Defending
        "P-ad Int/90", "P-ad Poss Won/90",
        "P-ad Pres A/90", "P-ad K Tck/90", "P-ad Tck/90", "P-ad Tck A/90",
        
        ### Discipline
        "P-ad Fouls/90",
    ],
    "DM": [
        ### Passing
        "Pr passes/90", "Progressive Rate",
        "Pas %", "Ps A/90", "Poss Lost/90",
        "Asts/90", "xA/90",  "Ch C/90", "OP-KP/90", "Risky Pass Rate",

        ### Player Movement
        "Drb/90", "Fouls Drawn/90",

        ### Defending
        "Int/90", "Poss Won/90",
        "Pres A/90", "K Tck/90", "Tck/90", "Tck R",
        "Blk/90","Shts Blckd/90",  "Clr/90",

        ### Discipline
        "Fouls/90", "Yel", "Red cards", "Fouls/Yellow", "Fouls/Red",

        ### Physicality - running
        "Dist/90", "Sprints/90",

        ### Physicality - Heading
        "Aer A/90", "Hdr %", "K Hdrs/90",
        
        ### Scoring
        "NP-xG/90", "xG/shot", "Shot/90",
        "Longshots Scored/90", "Shots From Outside The Box Per 90 minutes",


        ## Possession Adjusted

        ### Passing
        "P-ad Pr Passes/90",
        "P-ad Passes/90", "P-ad Poss Lost/90",
        "P-ad A/90", "P-ad xA/90", "P-ad Ch C/90", "P-ad OP-KP/90",

        ### Player Movement
        "P-ad Drb/90", "P-ad Fouls Drawn/90",

        ### Defending
        "P-ad Int/90", "P-ad Poss Won/90",
        "P-ad Pres A/90", "P-ad K Tck/90", "P-ad Tck/90", "P-ad Tck A/90",
        "P-ad Shts Blckd/90", "P-ad Clr/90", 

        ### Discipline
        "P-ad Fouls/90",
        
        ### Scoring
        "P-ad NP-xG/90", "P-ad Shot/90",
        "P-ad Longshots Scored/90", "P-ad Longshots/90", 

    ],
    "WB": [
        ### Passing
        "Asts/90", "xA/90",  "Ch C/90", "OP-KP/90", "Risky Pass Rate",
        "Pr passes/90", "Progressive Rate",
        "Pas %", "Ps A/90", "Poss Lost/90",

        ### Crossing Open Play
        "OP-Crs A/90", "OP-Crs C/90", "OP-Cr %", 

        ### Player Movement
        "Drb/90", "Fouls Drawn/90", "Offside/90",

        ### Defending
        "Int/90", "Poss Won/90",
        "Pres A/90", "K Tck/90", "Tck/90", "Tck R",
        
        ### Scoring
        "NP-xG/90", "Shot/90",
        "Longshots Scored/90",

        ### Physicality - running
        "Dist/90", "Sprints/90",
        
        ### Discipline
        "Fouls/90", "Yel", "Red cards", "Fouls/Yellow", "Fouls/Red",


        ## Possession Adjusted

        ### Passing
        "P-ad A/90", "P-ad xA/90", "P-ad Ch C/90", "P-ad OP-KP/90",
        "P-ad Pr Passes/90",
        "P-ad Passes/90", "P-ad Poss Lost/90",

        ### Crossing Open Play
        "P-ad OP-Crs A/90", "P-ad OP-Crs C/90",

        ### Player Movement
        "P-ad Drb/90", "P-ad Fouls Drawn/90", "P-ad Offside/90",

        ### Defending
        "P-ad Int/90", "P-ad Poss Won/90",
        "P-ad Pres A/90", "P-ad K Tck/90", "P-ad Tck/90", "P-ad Tck A/90",

        ### Scoring
        "P-ad NP-xG/90", "P-ad Shot/90",
        "P-ad Longshots Scored/90",
        

        ### Discipline
        "P-ad Fouls/90",
    ],
    "D": [
        ### Defending
        "Int/90", "Poss Won/90",
        "Pres A/90", "K Tck/90", "Tck/90", "Tck R",
        "Blk/90","Shts Blckd/90",  "Clr/90",

        ### Physicality - Heading
        "Aer A/90", "Hdr %", "K Hdrs/90",


        ### Passing
        "Pr passes/90", "Progressive Rate",
        "Pas %", "Ps A/90", "Poss Lost/90",

        ### Player Movement
        "Drb/90", "Fouls Drawn/90",

        ### Discipline
        "Fouls/90", "Yel", "Red cards", "Fouls/Yellow", "Fouls/Red",

        ### Physicality - running
        "Dist/90", "Sprints/90",
        

        ## Possession Adjusted
        
        ### Defending
        "P-ad Int/90", "P-ad Poss Won/90",
        "P-ad Pres A/90", "P-ad K Tck/90", "P-ad Tck/90", "P-ad Tck A/90",
        "P-ad Shts Blckd/90", "P-ad Clr/90", 
        
        ### Passing
        "P-ad Pr Passes/90",
        "P-ad Passes/90", "P-ad Poss Lost/90",

        ### Player Movement
        "P-ad Drb/90", "P-ad Fouls Drawn/90",

        ### Discipline
        "P-ad Fouls/90",
    ],
    "GK": [
        ### Goalkeeping
        "Clean Sheets", "xGP Rate", "P-ad xGP/90", "Sv %", "SvH Ratio", "MLG",
        #"xGP/90", "P-ad Saves/90", "Saves/90","Pens Saved Ratio",

        ### Passing
        "Pas %", "Progressive Rate", "P-ad Poss Lost/90",
        #"P-ad Pr Passes/90", "Pr passes/90", "Poss Lost/90", "P-ad Passes/90", "Ps A/90",

        ### Physicality - running
        "Dist/90",
    ],
}

## Columns where lower is better
INVERTED_COLS = [
    "Mins/Gl",
    "P-ad Mins/Gl",
    "Poss Lost/90",
    "P-ad Poss Lost/90",
    "Fouls Made",
    "Yel",
    "Red cards",
    "Off",
    "Offside/90",
    "P-ad Offside/90",
    "Goals Conceded",
    "MLG",
]

## Derived column funcitons
def derived_columns(df):
    # Strip % from percentage columns
    pct_cols = ["Conv %", "Shot %", "Pas %"]
    for col in pct_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.rstrip('%').astype(float)
    #Shooting
    df["P-ad Mins/Gl"] = df["Mins/Gl"] * df["Possession"]
    df["P-ad G/90"] = df["Goals per 90 minutes"] / df["Possession"]
    df["NP-xG/90"] = df["NP-xG"] / df["Minutes"] * 90
    df["P-ad NP-xG/90"] = df["NP-xG/90"] / df["Possession"]
    df["P-ad xG/90"] = df["xG/90"] / df["Possession"]
    df["P-ad Shot/90"] = df["Shot/90"] / df["Possession"]
    df["P-ad ShT/90"] = df["ShT/90"] / df["Possession"]
    df["P-ad Longshots/90"] = df["Shots From Outside The Box Per 90 minutes"] / df["Possession"]
    df["Longshots Scored/90"] = df["Goals From Outside The Box"] / df["Minutes"] * 90
    df["P-ad Longshots Scored/90"] = df["Longshots Scored/90"] / df["Possession"]
    df["xG-OP /90"] = df["xG-OP"] / df["Minutes"] * 90
    #Passing
    df["P-ad A/90"] = df["Asts/90"] / df["Possession"]
    df["P-ad xA/90"] = df["xA/90"] / df["Possession"]
    df["P-ad Passes/90"] = df["Ps A/90"] / df["Possession"]
    df["P-ad Ch C/90"] = df["Ch C/90"] / df["Possession"]
    df["P-ad OP-KP/90"] = df["OP-KP/90"] / df["Possession"]
    df["P-ad Pr Passes/90"] = df["Pr passes/90"] / df["Possession"]
    #Set pieces and crossing
    df["Db Crs A/90"] = df["Crs A/90"] - df["OP-Crs A/90"]
    df["Db Crs C/90"] = df["Cr C/90"] - df["OP-Crs C/90"]
    df["Db Crs %"] = df["Db Crs C/90"] / df["Db Crs A/90"]
    df["P-ad Crs A/90"] = df["Crs A/90"] / df["Possession"]
    df["P-ad Crs C/90"] = df["Cr C/90"] / df["Possession"]
    df["P-ad OP-Crs A/90"] = df["OP-Crs A/90"] / df["Possession"]
    df["P-ad OP-Crs C/90"] = df["OP-Crs C/90"] / df["Possession"]
    df["P-ad Db Crs A/90"] = df["Db Crs A/90"] / df["Possession"]
    df["P-ad Db Crs C/90"] = df["Db Crs C/90"] / df["Possession"]
    #Offensive movement and dribbling
    df["P-ad Drb/90"] = df["Drb/90"] / df["Possession"]
    df["Fouls Drawn/90"] = df["Fouls Against"] / df["Minutes"] * 90
    df["P-ad Fouls Drawn/90"] = df["Fouls Drawn/90"] / df["Possession"]
    df["Offside/90"] = df["Off"] / df["Minutes"] * 90
    df["P-ad Offside/90"] = df["Offside/90"] / df["Possession"]
    #Ball retention
    df["P-ad Poss Lost/90"] = df["Poss Lost/90"] / df["Possession"]
    df["P-ad Poss Won/90"] = df["Poss Won/90"] / (1-df["Possession"])
    #Defending
    df["Tck A/90"] = df["Tck A"] / df["Minutes"] * 90
    df["Tck C/90"] = df["Tck A/90"] * df["Tck R"] / 100 # pad needed
    df["K Tck/90"] = df["K Tck"] / df["Minutes"] * 90
    df["Fouls/90"] = df["Fouls Made"] / df["Minutes"] * 90
    df["P-ad Int/90"] = df["Int/90"] / (1-df["Possession"])
    df["P-ad Pres A/90"] = df["Pres A/90"] / (1-df["Possession"])
    df["P-ad Clr/90"] = df["Clr/90"] / (1-df["Possession"])
    df["P-ad Shts Blckd/90"] = df["Shts Blckd/90"] / (1-df["Possession"])
    df["P-ad Blk/90"] = df["Blk/90"] / (1-df["Possession"])
    df["P-ad Tck/90"] = df["Tck/90"] / (1-df["Possession"])
    df["P-ad Tck A/90"] = df["Tck A/90"] / (1-df["Possession"])
    df["P-ad K Tck/90"] = df["K Tck/90"] / (1-df["Possession"])
    df["P-ad Fouls/90"] = df["Fouls/90"] / (1-df["Possession"])
    df["Fouls/Yellow"] = df["Fouls Made"] / df["Yel"]
    df["Fouls/Red"] = df["Fouls Made"] / df["Red cards"]
    #Physicality
    df["Aer Imp"] = (df["K Hdrs/90"]*df["K Hdrs/90"]) / (df["Aer A/90"] * df["Hdr %"]) * 100
    #Goalkeeping
    df["xGP/90"] = df["xGP"] / df["Minutes"] * 90
    df["P-ad xGP/90"] = df["xGP/90"] / (1-df["Possession"])
    df["Saves/90"] = (df["Svh"] + df["Svp"] + df["Svt"])  / df["Minutes"] * 90
    df["SvH Ratio"] = df["Svh"] / (df["Svh"] + df["Svp"] + df["Svt"])
    df["P-ad Saves/90"] = df["Saves/90"] / (1-df["Possession"])
    df["xGP Rate"] = df["xGP/90"] / df["Tcon/90"] * 100
    #Future additions to index intention:
    df["Progressive Rate"] = df["Pr passes/90"] / df["Ps A/90"] * 100
    df["Risky Pass Rate"] = df["OP-KP/90"] / df["Ps A/90"] * 100
    df["Link-up Rate"] = (df["Ps A/90"] - df["Pr passes/90"] - df["Crs A/90"]) / df["Ps A/90"] * 100
    df["Link-up Volume/90"] = df["Ps A/90"] - df["Pr passes/90"] - df["Crs A/90"]
    df["P-ad Link-up Volume/90"] = df["Link-up Volume/90"] / df["Possession"]
    df["Touches/90"] = df["Shot/90"] + df["Drb/90"] + df["Ps A/90"] + df["Poss Lost/90"]
    df["Shot Bias"] = df["Shot/90"] / df["Touches/90"] * 100
    df["Drb Vol"] = df["Drb/90"] / df["Touches/90"] 
    df["Crs Volume"] = df["OP-Crs A/90"] / df["Touches/90"]
    df["Scoring Dependency"] = df["Goals per 90 minutes"] / df["Tgls/90"]
    df["Creative Dependency"] = df["Asts/90"] / df["Tgls/90"]
    return df

# Position Logic Functions
## Splitting best position into separate roles and sides for dropdowns and filtering
def parse_positions(position_series):
    roles = set()
    sides = set()
    for pos in position_series.unique():
        if pd.isna(pos):
            continue
        segments = pos.split(", ")
        for seg in segments:
            side_match = re.search(r"\(([RLC]+)\)", seg)
            if side_match:
                for char in side_match.group(1):
                    sides.add(char)
                role_part = seg[:side_match.start()].strip()
            else:
                role_part = seg.strip()
            for role in role_part.split("/"):
                r = role.strip()
                if r:
                    roles.add(r)
    # Sort roles dropdown by typical football hierarchy
    role_order = ["ST", "AM", "M", "DM", "WB", "D", "GK"]
    roles = sorted(roles, key=lambda x: role_order.index(x) if x in role_order else 999)
    sides = sorted(sides)
    return roles, sides

## Function to check if a player's position string matches the selected role and sides
def player_matches(position_str, selected_role, selected_sides):
    if pd.isna(position_str):
        return False
    segments = position_str.split(", ")
    for seg in segments:
        side_match = re.search(r"\(([RLC]+)\)", seg)
        if side_match:
            seg_sides = set(side_match.group(1))
            role_part = seg[:side_match.start()].strip()
        else:
            seg_sides = set()
            role_part = seg.strip()
        seg_roles = [r.strip() for r in role_part.split("/")]
        if selected_role in seg_roles:
            if len(selected_sides) == 0:
                return True
            if selected_sides.issubset(seg_sides):
                return True
    return False

## Mask builder to apply player_matches
def build_position_mask(pos_data, selected_role, selected_sides):
    return pos_data.apply(lambda x: player_matches(x, selected_role, selected_sides)
    )


# UI Setup
## File uploader
col_upload1, col_upload2 = st.columns(2)
with col_upload1:
    uploaded_file = st.file_uploader("Upload FM Player CSV", type=["csv"])
with col_upload2:
    possession_file = st.file_uploader("Upload Possession CSV", type=["csv"])


##  Main App
if uploaded_file:
    if possession_file:
        df = load_data(uploaded_file, possession_file)

        unmatched = df[df['Possession'].isna()]['Club'].unique()
        if len(unmatched) > 0:
            st.warning(f"{len(unmatched)} clubs have no possession data - P-ad metrics will be empty for those players.")
            with st.expander("Unmatched clubs"):
                st.write(list(unmatched))
    else:
        df = pd.read_csv(uploaded_file, sep=';')
        st.info("No possession data uploaded - P-ad metrics will not be available.")
    
    # Identify percentile columns
    percentile_cols = [
        col for col in df.columns
        if col not in desc_cols
    ]
    
    #Position names for dropdowns
    available_roles, available_sides = parse_positions(df["Best Pos"].fillna("") + ", " + df["Sec. Position"].fillna(""))

    role_labels = {
        "GK": "Goalkeeper",
        "D": "Defender",
        "WB": "Wing-Back",
        "DM": "Defensive Midfielder",
        "M": "Midfielder",
        "AM": "Attacking Midfielder",
        "ST": "Striker"}
    side_labels = {
        "L": "Left",
        "R": "Right",
        "C": "Centre"}

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Dropdowns for position and sides
    st.markdown("#### Position Selection")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        role_options = [f"{r} - {role_labels.get(r, r)}" for r in available_roles]
        selected_role_display = st.selectbox("Position", role_options)
        selected_role = selected_role_display.split(" - ")[0]

    with col2:
        side_options = [s for s in available_sides]
        selected_sides_display = st.selectbox(
            "Side(s)",
            available_sides,
            index=None,
            format_func=lambda x: side_labels.get(x, x),
            help="Leave empty to ignore sides (GK/DM/ST etc) & Player must be able to play ALL selected sides"
    )
    selected_sides = {selected_sides_display} if selected_sides_display else set()

    with col3:
        use_sec = st.checkbox("Include Secondary Positions", value=True)

    with col4:
        u23_only = st.toggle("U23 Only")

    # Apply position filter
    if use_sec:
        pos_data = df["Best Pos"].fillna("") + ", " + df["Sec. Position"].fillna("")
    else:
        pos_data = df["Best Pos"].fillna("")
    
    mask = build_position_mask(pos_data, selected_role, selected_sides)
    if u23_only:
        mask = mask & (df["Age"] < 23)
    filtered_df = df[mask].copy()
    

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.write(f"{len(filtered_df)} players match filter")
    #st.write("#### Raw Player Data")

    with st.expander("Raw Player Data", expanded=False):
        raw_display = filtered_df.set_index(["Player", "Age", "Club", "Transfer Value"])
        st.dataframe(raw_display, use_container_width=True, height=600)
    

    if len(filtered_df) > 0:
        stat_cols = [c for c in filtered_df.columns if c not in desc_cols]
        for col in stat_cols:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce") #need to convert percentages to a number
        
        ## what columns in the percentiles
        # Get position-specific columns
        visible_cols = position_stat_groups.get(selected_role, stat_cols)
        # Only keep columns that actually exist in the dataframe
        visible_cols = [c for c in visible_cols if c in filtered_df.columns]

        # calculate percentiles for visible columns

        if len(visible_cols) == 0:
            st.warning("Select at least one column to display")
        else:
            # Calculate percentiles within the filtered position group
            percentile_df = filtered_df[["Player", "Age", "Club", "Transfer Value"]].copy()
            
            for col in visible_cols:
                if col in INVERTED_COLS:
                    percentile_df[col] = filtered_df[col].rank(pct=True, ascending=False)
                else:
                    percentile_df[col] = filtered_df[col].rank(pct=True, ascending=True)
            
            # Convert to 0-100 scale
            percentile_df[visible_cols] = (percentile_df[visible_cols] * 100).round(0)
            
            #st.markdown("#### Percentile Rankings")
            
            percentile_display = percentile_df.set_index(["Player", "Age", "Club", "Transfer Value"])

            # Style with red-to-green gradient
            styled_df = percentile_display.style.background_gradient(
                cmap='RdYlGn',
                subset=visible_cols,
                vmin=0,
                vmax=100
            ).format(subset=visible_cols, precision=0)
            
            with st.expander("Percentile Rankings", expanded=False):
                st.dataframe(styled_df, use_container_width=True, height=600)
    

                # Pizza chart composite stats
            st.divider()
            st.markdown("#### Pizza Stats")
            
            filtered_pizza = filtered_df[["Player", "Age", "Club", "Transfer Value"]].copy()

            for category, metrics in pizzacat.items():
                for metric in metrics:
                    if metric["method"] == "single":
                        col = metric["col"]
                        if col in filtered_df.columns:
                            filtered_pizza[metric["name"]] = filtered_df[col].rank(pct=True) * 100
                    elif metric["method"] == "derived_composite":
                        # Average the percentile ranks of all components
                        component_ranks = []
                        for comp in metric["components"]:
                            if comp in filtered_df.columns:
                                component_ranks.append(filtered_df[comp].rank(pct=True))
                        if component_ranks:
                            filtered_pizza[metric["name"]] = (sum(component_ranks) / len(component_ranks)) * 100
            
            filtered_pizza = filtered_pizza.round(0).set_index(["Player", "Age", "Club", "Transfer Value"])
            
            styled_filtered_pizza = filtered_pizza.style.background_gradient(
                cmap='RdYlGn',
                vmin=0,
                vmax=100
            ).format(precision=0)
            
            with st.expander("Pizza Stats", expanded=False):
                st.dataframe(styled_filtered_pizza, use_container_width=True, height=600)




                        # Category summary scores
            category_names = []
            for category, metrics in pizzacat.items():
                metric_names = [m["name"] for m in metrics if m["name"] in filtered_pizza.columns]
                if metric_names:
                    filtered_pizza[category] = filtered_pizza[metric_names].mean(axis=1).round(0)
                    category_names.append(category)
            
            pizza_summary = filtered_df[["Player", "Age", "Club", "Transfer Value"]].copy()
            for cat in category_names:
                pizza_summary[cat] = filtered_pizza[cat].values
            
            pizza_summary_display = pizza_summary.set_index(["Player", "Age", "Club", "Transfer Value"])
            
            styled_filtered_pizza_summary = pizza_summary_display.style.background_gradient(
                cmap='RdYlGn',
                subset=category_names,
                vmin=0,
                vmax=100
            ).format(subset=category_names, precision=0)
            
            with st.expander("Pizza Summary", expanded=False):
                st.dataframe(styled_filtered_pizza_summary, use_container_width=True, height=600)

import streamlit as st
import pandas as pd
import numpy as np
import re
import unicodedata
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.colors import to_rgba
import matplotlib.font_manager as fm

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Inter", "Helvetica Neue", "Arial"],
    "font.size": 9,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 9,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "text.color": "#2b2b2b",
    "axes.labelcolor": "#2b2b2b",
    "xtick.color": "#4a4a4a",
    "ytick.color": "#4a4a4a",
})

## Idea: select team that won the league and use them as a comparison tool/best player in the league.









# Page Setup
## Set page Title
st.set_page_config(page_title="FM Moneyball", layout="wide")
st.title("FM26 Moneyball App")








# Data Functions and processing
## Match accents
def strip_accents(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.category(c).startswith('M'))

## Wages and Value to float
def parse_money(value):
    """
    Converts FM strings like:
    £450K - £500K
    £55M - £65M
    £18K
    £1.2M

    into a numeric average.
    """

    if pd.isna(value):
        return np.nan

    text = str(value)

    matches = re.findall(r"([\d.]+)\s*([KM]?)", text)

    if not matches:
        return np.nan

    values = []

    for num, suffix in matches[:2]:
        num = float(num)

        if suffix == "M":
            num *= 1_000_000
        elif suffix == "K":
            num *= 1_000

        values.append(num)

    return sum(values) / len(values)

## File uploader
def load_data(uploaded_file, possession_file):
    df = pd.read_csv(uploaded_file, sep=';')

    # Convert FM money strings to numbers immediately
    if "Wage" in df.columns:
        df["Wage"] = df["Wage"].apply(parse_money)

    if "Transfer Value" in df.columns:
        df["Transfer Value"] = df["Transfer Value"].apply(parse_money)
    
    # load and process possession data
    df_poss = pd.read_csv(possession_file)
    df_poss['Possession'] = df_poss['Possession'].str.rstrip('%').astype(float) / 100
    
    # Match on accent-stripped club names
    df['_key'] = df['Club'].apply(strip_accents)
    df_poss['_key'] = df_poss['Club'].apply(strip_accents)
    
    df = df.merge(df_poss[['_key', 'Possession']], on='_key', how='left')
    df.drop(columns=['_key'], inplace=True)
    
    df = derived_columns(df)
    df["Player"] = df["Player"].apply(strip_accents)
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
        {"name": "Front-foot Defending", "method": "derived_composite", 
        "components": ["P-ad Tck/90", "P-ad Int/90", "Pres A/90", "P-ad Fouls/90", "P-ad Blk/90"]},
        {"name": "Tackle Success", "method": "single", "col": "Tck R"},
        {"name": "Back-foot Defending", "method": "derived_composite",
        "components": ["P-ad Shts Blckd/90", "P-ad Clr/90"]},
        {"name": "Loose Ball Recoveries", "method": "single", "col": "P-ad Poss Won/90"},
        {"name": "Aerial Volume", "method": "single", "col": "Aer A/90"},
        {"name": "Aerial Success", "method": "single", "col": "Hdr %"},
    ],
    "Possession": [
        {"name": "Ball Retention", "method": "single", "col": "Pas %"},
        {"name": "Link-up Play", "method": "single", "col": "Link-up Rate"},
        {"name": "Progressive Rate", "method": "single", "col": "Progressive Rate"},
    ],
    "Progression": [
        {"name": "Creative Threat", "method": "derived_composite",
        "components": ["P-ad xA/90","P-ad A/90"]},
        {"name": "Risk Rate", "method": "single", "col": "Risky Pass Rate"},
        {"name": "OP Crossing Volume", "method": "single", "col": "Crs Volume"},
        {"name": "OP Crossing Accuracy", "method": "single", "col": "OP-Cr %"},
        {"name": "Pass Progression", "method": "single", "col": "Progressive Rate"},
        {"name": "Dribble Rate", "method": "single", "col": "Drb Vol"},
    ],
    "Attack": [
        {"name": "Goal Threat", "method": "derived_composite",
        "components": ["P-ad xG/90", "P-ad G/90"]},
        {"name": "Shot Frequency", "method": "single", "col": "Shot Bias"},
        {"name": "Shot Quality", "method": "single", "col": "xG/shot"},
        {"name": "Box Threat", "method": "single", "col": "Box Threat"},
    ],
}

position_primary_cat = {
    "ST": "Attack",
    "AM": "Progression",
    "M": "Possession",
    "DM": "Possession",
    "WB": "Defence",
    "D": "Defence",
    "GK": "Possession",
}


pizza_templates = {
    "ST": {
        "Attack": ["Goal Threat", "Shot Frequency", "Shot Quality", "Box Threat"],
        "Defence": ["Front-foot Defending", "Aerial Volume"],
        "Possession": ["Link-up Play"],
        "Progression": ["Pass Progression", "Risk Rate", "Dribble Rate", "Creative Threat",],
    },
    "AM": {
        "Attack": ["Goal Threat", "Shot Frequency", "Box Threat"],
        "Defence": ["Aerial Volume", "Front-foot Defending"],
        "Possession": ["Link-up Play"],
        "Progression": ["Pass Progression", "Risk Rate", "OP Crossing Volume", "Dribble Rate", "Creative Threat",],
    },
    "CM": {
        "Possession": ["Ball retention", "Link-up play", "Progressive Rate"],
        "Progression": ["Creative threat", "Risk Rate", "Progressive Volume"],
        "Defence": ["Front-foot defending", "Tackle success", "Loose ball recoveries", "Aerial volume", "Aerial success"],
    },
    "DM": {
        "Attack": ["Goal Threat", "Shot Frequency",],
        "Defence": ["Aerial Volume", "Loose Ball Recoveries", "Front-foot Defending", "Tackle Success",],
        "Possession": ["Link-up Play", "Ball Retention", "Progressive Rate"],
        "Progression": ["Pass Progression", "Dribble Rate", "Risk Rate"],
    },
    "WB": {
        "Attack": ["Goal Threat"],
        "Defence": ["Tackle Success", "Front-foot Defending", "Back-foot Defending", "Aerial volume"],
        "Possession": ["Link-up Play", "Ball Retention"],
        "Progression": ["OP Crossing Volume", "Dribble Rate", "Creative Threat", "Pass Progression",],

    },
    "D": {
        "Attack": ["Goal Threat"],
        "Defence": ["Tackle Tuccess", "Front-foot Defending", "Back-foot Defending", "Loose Ball Recoveries", "Aerial Volume", "Aerial Success"],
        "Possession": ["Ball Retention", "Link-up Play", "Progressive Rate"],
        "Progression": ["Dribble Rate", "Risk Rate"],
    },
    "GK": {
        "Possession": ["Ball retention", "Progressive Rate"],
    },
}

position_stat_groups = {
    "ST": [
        # Scoring
        "P-ad G/90", "P-ad NP-xG/90", "Conv %", "xG/shot", "Shot Bias", "Scoring Dependency",
        # Passing
        "P-ad A/90", "P-ad xA/90", "P-ad OP-KP/90", "Risky Pass Rate",
        # Movement
        "Drb Vol", "P-ad Offside/90",
        # Physicality
        "Aer Imp", "Sprints/90",
        # Defending
        "Pressing Efficiency",
        
    ],

    "AM": [
        # Passing
        "P-ad A/90", "P-ad xA/90", "P-ad OP-KP/90", "Risky Pass Rate", "Creative Dependency",
        # Scoring
        "P-ad G/90", "P-ad NP-xG/90", "Conv %", "xG/shot", "Shot Bias", "Scoring Dependency",
        # Crossing
        "P-ad OP-Crs A/90", "OP-Cr %",
        # Movement
        "Drb Vol", "P-ad Offside/90",
        # Physicality
        "Sprints/90",
        # Defending
        "Pressing Efficiency",
    ],

    "M": [
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
        # Possession
        "Ps A/90","Pas %","P-ad Poss Lost/90","P-ad Pr Passes/90","Progressive Rate",
        # Creativity
        "P-ad OP-KP/90","Risky Pass Rate",
        # Ball Winning
        "P-ad Int/90","P-ad Poss Won/90","P-ad Tck A/90","P-ad K Tck/90",
        # Pressing
        "P-ad Pres A/90","Pressing Efficiency",
        # Mobility
        "Dist/90","Sprints/90",
        # Aerial
        "Aer A/90","Hdr %",
        # Extras
        "Drb Vol","Shot Bias","xG/shot",
    ],

    "WB": [
        # Progression
        "P-ad Pr Passes/90","Progressive Rate","Drb Vol",
        # Creativity
        "P-ad xA/90","P-ad OP-KP/90","Risky Pass Rate",
        # Crossing
        "P-ad OP-Crs A/90","OP-Cr %",
        # Possession
        "Pas %","P-ad Poss Lost/90",
        # Defending
        "P-ad Poss Won/90","P-ad Int/90","P-ad Blk/90","P-ad Tck A/90","P-ad K Tck/90","P-ad Pres A/90",
        # Physical
        "Dist/90","Sprints/90",
        # Optional attacking flavour
        "Shot Bias",
    ],

    "D": [
        # Defending
        "P-ad Int/90", "P-ad Blk/90", "Int Quality", "P-ad Poss Won/90", "P-ad Tck A/90", "P-ad K Tck/90", "P-ad Shts Blckd/90", "P-ad Clr/90",
        # Aerial
        "Aer A/90", "Hdr %", "K Hdrs/90",
        # Progression
        "P-ad Pr Passes/90", "Progressive Rate",
        # Possession
        "Pas %", "P-ad Poss Lost/90",
        # Pressing
        "P-ad Pres A/90",
        # Physical
        "Dist/90", "Sprints/90",
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
    df["Pressing Efficiency"] =(df["P-ad Fouls/90"] + df["P-ad Poss Won/90"]) * df["Pres A/90"]
    df["Int Quality"] = df["P-ad Int/90"] / (df["P-ad Int/90"] + df["P-ad Blk/90"]) * df["P-ad Int/90"]
    #Physicality
    df["Aer Imp"] = (df["K Hdrs/90"]) / (df["Aer A/90"]) * df["Hdr %"]
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
    df["Link-up Rate"] = (df["P-ad Passes/90"] - df["P-ad Pr Passes/90"] - df["P-ad Crs A/90"]) / df["P-ad Passes/90"]
    df["Link-up Volume/90"] = df["Ps A/90"] - df["Pr passes/90"] - df["Crs A/90"]
    df["P-ad Link-up Volume/90"] = df["Link-up Volume/90"] / df["Possession"]
    df["Long Pass Vol"] = df["Ps A/90"] - df["Link-up Volume/90"]
    df["P-ad Long Pass Vol"] = (df["P-ad Passes/90"] - df["Link-up Volume/90"]) / df["Possession"]
    df["Long Pass Rate"] = df["Long Pass Vol"] / df["Ps A/90"]
    df["Touches/90"] = df["Shot/90"] + df["Drb/90"] + df["Ps A/90"] + df["Poss Lost/90"]
    df["Shot Bias"] = df["Shot/90"] / df["Touches/90"] * 100
    df["Drb Vol"] = df["Drb/90"] / df["Touches/90"] 
    df["Crs Volume"] = df["OP-Crs A/90"] / df["Touches/90"]
    df["Scoring Dependency"] = df["Goals per 90 minutes"] / df["Tgls/90"]
    df["xScoring Dependency"] = df["xG/90"] / df["Tgls/90"]
    df["Creative Dependency"] = df["Asts/90"] / df["Tgls/90"]
    df["xCreative Dependency"] = df["xA/90"] / df["Tgls/90"]
    df["Box Threat"] = df["xG/shot"] * df["Shot Bias"]

    return df



    return pizza











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
    
    
    
    
    
    
    
    
    
    
    
    # Player Filtering - by position, secondary positions, and U23 toggle
    #Position names for dropdowns
    available_roles, available_sides = parse_positions(df["Best Pos"].fillna("") + ", " + df["Position"].fillna(""))

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


    # 4 sections for filtering by position - role, side, include secondary positions, u23 only
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
        pos_data = df["Best Pos"].fillna("") + ", " + df["Position"].fillna("")
    else:
        pos_data = df["Best Pos"].fillna("")
    
    mask = build_position_mask(pos_data, selected_role, selected_sides)
    if u23_only:
        mask = mask & (df["Age"] < 23)
    filtered_df = df[mask].copy()
    

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.write(f"{len(filtered_df)} players match filter")

    with st.expander("Raw Player Data", expanded=False):
        raw_display = filtered_df.set_index(["Player", "Age", "Club", "Transfer Value"])
        st.dataframe(raw_display, use_container_width=True, height=600)










# Creation of Percentile Data
    if len(filtered_df) > 0:
        stat_cols = [c for c in filtered_df.columns if c not in desc_cols]
        for col in stat_cols:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
        
        ## what columns in the percentiles
        # Get position-specific columns
        visible_cols = position_stat_groups.get(selected_role, stat_cols)
        # Only keep columns that actually exist in the dataframe
        visible_cols = [c for c in visible_cols if c in filtered_df.columns] #is this neccessary?

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
            
            with st.expander("Percentile Rankings", expanded=True):
                st.dataframe(styled_df, use_container_width=True, height=600)
    









            st.divider()
            
            
            
            
            
            
            
            
            
            
            # Filtered Pizza stats
            #st.markdown("#### Pizza Stats")
            
            filtered_pizza = filtered_df[["Player", "Age", "Club", "Transfer Value"]].copy()
            # Percentile ranks for pizza metrics
            for category, metrics in pizzacat.items():
                for metric in metrics:
                    if metric["method"] == "single":
                        col = metric["col"]
                        if col in filtered_df.columns:
                            filtered_pizza[metric["name"]] = filtered_df[col].rank(pct=True) * 100
                    elif metric["method"] == "derived_composite":
                        score = filtered_df[metric["components"]].sum(axis=1)
                        filtered_pizza[metric["name"]] = score.rank(pct=True) * 100
            
            filtered_pizza = filtered_pizza.round(0).set_index(["Player", "Age", "Club", "Transfer Value"])
            #Style with red-to-green gradient
            styled_filtered_pizza = filtered_pizza.style.background_gradient(
                cmap='RdYlGn',
                vmin=0,
                vmax=100
            ).format(precision=0)
            
            #with st.expander("Pizza Stats", expanded=False):
            #    st.dataframe(styled_filtered_pizza, use_container_width=True, height=600)












            # ─── Player Radar Chart ───────────────────────────────────────────
            st.markdown("#### Player Radar Chart")

            pizza_players = filtered_pizza.index.get_level_values("Player").tolist()

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                player_1 = st.selectbox("Player 1", pizza_players, index=0, key="radar_p1")
            with col_r2:
                player_2 = st.selectbox("Player 2", pizza_players, index=1, key="radar_p2")

            if player_1 and player_2:
                cat_colours = {
                        "Defence": "#2979FF",
                        "Possession": "#00E676",
                        "Progression": "#FF9100",
                        "Attack": "#FF1744",
                    }

                primary_cat = position_primary_cat.get(selected_role, None)

                template = pizza_templates.get(selected_role, {})
                metric_names = []
                metric_colours = []
                metric_alphas = []
                for category, names in template.items():
                    for name in names:
                        if name in filtered_pizza.columns:
                            metric_names.append(name)
                            metric_colours.append(cat_colours.get(category, "#999999"))
                            if category == primary_cat:
                                metric_alphas.append(1.0)
                            else:
                                metric_alphas.append(0.4)

                N = len(metric_names)
                angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
                angles += angles[:1]

                def get_values(player):
                    row = filtered_pizza.loc[filtered_pizza.index.get_level_values("Player") == player]
                    vals = row[metric_names].values.flatten().tolist()
                    vals += vals[:1]
                    return vals

                vals_1 = get_values(player_1)
                vals_2 = get_values(player_2)

                fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
                ax.set_theta_offset(np.pi / 2)
                ax.set_theta_direction(-1)

                ax.plot(angles, vals_1, linewidth=2, color="#1f77b4", label=player_1)
                ax.fill(angles, vals_1, alpha=0.15, color="#1f77b4")

                ax.plot(angles, vals_2, linewidth=2, color="#e74c3c", label=player_2)
                ax.fill(angles, vals_2, alpha=0.15, color="#e74c3c")

                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(metric_names, size=7)
                ax.set_ylim(0, 100)
                ax.set_yticks([20, 40, 60, 80, 100])
                ax.set_yticklabels(["20", "40", "60", "80", "100"], size=7, color="grey")
                ax.set_rlabel_position(0)
                ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

                                # Pizza plot in col1 (constrained width, radar removed)
                col1, col2 = st.columns([1, 1])
                with col1:

                    fig2, ax2 = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
                    ax2.xaxis.grid(False)
                    ax2.yaxis.grid(True, linestyle="dotted", color="grey", alpha=0.5)
                    ax2.spines['polar'].set_visible(False)
                    ax2.set_theta_offset(np.pi / 2 - np.pi / N)
                    ax2.set_theta_direction(-1)
                    fig2.patch.set_facecolor("white")
                    ax2.set_facecolor("white")

                    angles_pizza = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
                    width = 2 * np.pi / N

                    # Player 2 - full/faded by category
                    p2_colours = [to_rgba(c, alpha=a) for c, a in zip(metric_colours, metric_alphas)]
                    ax2.bar(angles_pizza, vals_2[:-1], width=width, bottom=0,
                            color=p2_colours, edgecolor="white", linewidth=0.5)

                    # Player 1 - translucent fill, bold outline fades for non-primary
                    p1_colours = [to_rgba(c, alpha=0) for c in metric_colours]
                    p1_edges = [to_rgba("black", alpha=a) for a in metric_alphas]
                    ax2.bar(angles_pizza, vals_1[:-1], width=width, bottom=0,
                            color=p1_colours, edgecolor=p1_edges, linewidth=2.5)

                    ax2.set_xticks(angles_pizza)
                    ax2.set_xticklabels(metric_names, size=7)
                    ax2.set_ylim(0, 101)
                    ax2.set_yticks([20, 40, 60, 80, 100])
                    ax2.set_yticklabels(["20", "40", "60", "80", "100"], size=7, color="black")
                    ax2.set_rlabel_position(0)

                    legend_patches = [Patch(color=c, label=cat) for cat, c in cat_colours.items()]
                    legend_patches.append(Patch(facecolor="none", edgecolor="black", linewidth=1, label=player_1))
                    legend_patches.append(Patch(color="black", alpha=1, label=player_2))
                    ax2.legend(handles=legend_patches, loc="upper right", bbox_to_anchor=(1.4, 1.1), fontsize=5)
                    ax2.set_title(f"{player_1} vs {player_2}", size=11, weight="bold", y=1.08)

                    st.pyplot(fig2)





                    # ─── Info Block Comparison (below pizza) ───────────────────────
                    info_metrics = {
                        "Transfer Value": {"col": "Transfer Value", "fmt": "money"},
                        "Wages": {"col": "Wage", "fmt": "money"},
                        "Age": {"col": "Age", "fmt": "money"},
                        "Left Foot": {"col": "Left Foot", "fmt": "str"},
                        "Right Foot": {"col": "Right Foot", "fmt": "str"},
                        "Injury Recurrence": {"col": "Recurring Injury", "fmt": "str"},
                    }

                    # Pull raw data for both players from the unindexed filtered_df
                    p1_info = filtered_df.loc[filtered_df["Player"] == player_1].iloc[0]
                    p2_info = filtered_df.loc[filtered_df["Player"] == player_2].iloc[0]

                    def fmt_value(val, fmt):
                        if fmt == "money":
                            if pd.isna(val) or val == 0:
                                return "N/A"
                            if val >= 1_000_000:
                                return f"£{val/1_000_000:.1f}M"
                            elif val >= 1_000:
                                return f"£{val/1_000:.0f}K"
                            else:
                                return f"£{val:.0f}"
                        return str(val) if not pd.isna(val) else "N/A"

                    # Build comparison figure
                    info_labels = list(info_metrics.keys())
                    n_info = len(info_labels)

                    fig_info, ax_info = plt.subplots(figsize=(5, n_info * 0.3))
                    ax_info.set_xlim(-1, 1)
                    ax_info.set_ylim(-0.5, n_info - 0.5)
                    ax_info.axis("off")
                    ax_info.invert_yaxis()

                    for i, label in enumerate(info_labels):
                        meta = info_metrics[label]
                        v1 = fmt_value(p1_info[meta["col"]], meta["fmt"])
                        v2 = fmt_value(p2_info[meta["col"]], meta["fmt"])

                        # Player 1 value (left)
                        ax_info.text(-0.95, i, v1, ha="left", va="center",
                                    fontsize=9, weight="bold", color="#1f77b4")
                        # Metric label (centre)
                        ax_info.text(0, i, label, ha="center", va="center",
                                    fontsize=8, color="black")
                        # Player 2 value (right)
                        ax_info.text(0.95, i, v2, ha="right", va="center",
                                    fontsize=9, weight="bold", color="#e74c3c")

                    # Header row
                    ax_info.text(-0.95, -0.45, player_1, ha="left", va="bottom",
                                fontsize=8, weight="bold", color="#1f77b4")
                    ax_info.text(0.95, -0.45, player_2, ha="right", va="bottom",
                                fontsize=8, weight="bold", color="#e74c3c")

                    fig_info.tight_layout()
                    st.pyplot(fig_info)


# col2 percentile comparison
                with col2:
                    # Get percentile data for both players
                    p1_pct = percentile_display.loc[
                        percentile_display.index.get_level_values("Player") == player_1,
                        visible_cols
                    ]
                    p2_pct = percentile_display.loc[
                        percentile_display.index.get_level_values("Player") == player_2,
                        visible_cols
                    ]

                    # Get raw values for both players
                    p1_raw = raw_display.loc[
                        raw_display.index.get_level_values("Player") == player_1,
                        visible_cols
                    ]
                    p2_raw = raw_display.loc[
                        raw_display.index.get_level_values("Player") == player_2,
                        visible_cols
                    ]

                    if not p1_pct.empty and not p2_pct.empty:
                        p1_vals = p1_pct.values.flatten()
                        p2_vals = p2_pct.values.flatten()
                        p1_raw_vals = p1_raw.values.flatten()
                        p2_raw_vals = p2_raw.values.flatten()
                        labels = visible_cols

                        cmap = plt.cm.RdYlGn

                        fig3, ax3 = plt.subplots(figsize=(5, max(4, len(labels) * 0.3)))

                        y = np.arange(len(labels))
                        bar_height = 1.0

                        # Player 1 bars (left/negative direction)
                        for i, (val, raw) in enumerate(zip(p1_vals, p1_raw_vals)):
                            ax3.barh(y[i], -val, height=bar_height,
                                    color=cmap(val / 100), edgecolor="white", linewidth=0.5)
                            # Label with raw value (inside bar, right-aligned)
                            ax3.text(-2, y[i], f"{raw:.1f}", ha="right", va="center",
                                    fontsize=6, color="black", weight="bold")

                        # Player 2 bars (right/positive direction)
                        for i, (val, raw) in enumerate(zip(p2_vals, p2_raw_vals)):
                            ax3.barh(y[i], val, height=bar_height,
                                    color=cmap(val / 100), edgecolor="white", linewidth=0.5)
                            # Label with raw value (inside bar, left-aligned)
                            ax3.text(2, y[i], f"{raw:.1f}", ha="left", va="center",
                                    fontsize=6, color="black", weight="bold")

                        # Formatting
                        ax3.set_yticks(y)
                        ax3.set_yticklabels(labels, fontsize=7)
                        ax3.axvline(0, color="black", linewidth=0.8)
                        ax3.set_xlim(-105, 105)
                        ax3.set_xticks([-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100])
                        ax3.set_xticklabels(["100", "80", "60", "40", "20", "0", "20", "40", "60", "80", "100"], fontsize=7)
                        ax3.set_xlabel("Percentile", fontsize=8)

                        
                        ax3.set_title(f"{player_1} vs {player_2}", size=11, weight="bold",)
                        ax3.invert_yaxis()
                        fig3.tight_layout()

                        st.pyplot(fig3)








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
            
            #with st.expander("Pizza Summary", expanded=False):
                #st.dataframe(styled_filtered_pizza_summary, use_container_width=True, height=600)











            #st.divider()












            # Filtered Pizza stats
            #st.markdown("#### Unfiltered Pizza Stats")

            unfiltered_pizza = df[["Player", "Age", "Club", "Transfer Value"]].copy()

            for category, metrics in pizzacat.items():
                for metric in metrics:
                    if metric["method"] == "single":
                        col = metric["col"]
                        if col in df.columns:
                            unfiltered_pizza[metric["name"]] = df[col].rank(pct=True) * 100
                    elif metric["method"] == "derived_composite":
                        # Average the percentile ranks of all components
                        component_ranks = []
                        for comp in metric["components"]:
                            if comp in df.columns:
                                component_ranks.append(df[comp].rank(pct=True))
                        if component_ranks:
                            unfiltered_pizza[metric["name"]] = (sum(component_ranks) / len(component_ranks)) * 100
            
            unfiltered_pizza = unfiltered_pizza.round(0).set_index(["Player", "Age", "Club", "Transfer Value"])
            
            #with st.expander("Unfiltered Pizza Stats"):
            #    st.dataframe(unfiltered_pizza)


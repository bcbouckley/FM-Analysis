import streamlit as st
import pandas as pd
import numpy as np
import re

## this is a test now number twoo


# Page Setup
## Set page Title
st.set_page_config(page_title="FM Moneyball", layout="wide")
st.title("FM26 Moneyball App")


# Data Functions and processing
## File uploader
def load_data(uploaded_file):
    df = pd.read_csv(uploaded_file)
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
    "Age",
    "Height",
    "Left Foot",
    "Right Foot",
    "Recurring Injury",
    "Injury Susceptibility"
    #"Wage",
    #"Transfer Value", 
]
pad_cols = [
    "P-ad Mins/Gl",
    "P-ad G/90",
    "P-ad NP-xG/90",
    "P-ad xG/90",
    "P-ad Shot/90",
    "P-ad ShT/90",
    "P-ad Longshots/90",
    "P-ad Longshots Scored/90",
    "P-ad A/90",
    "P-ad xA/90",
    "P-ad Passes/90",
    "P-ad Ch C/90",
    "P-ad OP-KP/90",
    "P-ad Pr Passes/90",
    "P-ad Crs A/90",
    "P-ad Crs C/90",
    "P-ad OP-Crs A/90",
    "P-ad OP-Crs C/90",
    "P-ad Db Crs A/90",
    "P-ad Db Crs C/90",
    "P-ad Drb/90",
    "P-ad Fouls Drawn/90",
    "P-ad Offside/90",
    "P-ad Poss Lost/90",
    "P-ad Poss Won/90",
    "P-ad Int/90",
    "P-ad Pres A/90",
    "P-ad Clr/90",
    "P-ad Shts Blckd/90",
    "P-ad Fouls/90",
    "P-ad xGP/90",
]
sho_cols = [
    "Goals",
    "Mins/Gl",
    "Goals per 90 minutes",
    "xG",
    "NP-xG",
    "xG-OP",
    "xG/90",
    "Conv %",
    "xG/shot",
    "Shot/90",
    "ShT/90",
    "Shots From Outside The Box Per 90 minutes",
    "Shot %",
    "Goals From Outside The Box",
    "Pens",
    "Pen/R",
    "P-ad Mins/Gl",
    "P-ad G/90",
    "NP-xG/90",
    "P-ad NP-xG/90",
    "P-ad xG/90",
    "P-ad Shot/90",
    "P-ad ShT/90",
    "P-ad Longshots/90",
    "Longshots Scored/90",
    "P-ad Longshots Scored/90"
]
pass_cols = [
    "Assists",
    "Asts/90",
    "xA",
    "xA/90",
    "Pas %",
    "Ps A/90",
    "Ch C/90",
    "OP-KP/90",
    "Pr passes/90",
    "OP-Crs A/90",
    "OP-Crs C/90",
    "OP-Cr %",
    "P-ad A/90",
    "P-ad xA/90",
    "P-ad Passes/90",
    "P-ad Ch C/90",
    "P-ad OP-KP/90",
    "P-ad Pr Passes/90",
    "P-ad Crs A/90",
    "P-ad Crs C/90",
    "P-ad OP-Crs A/90",
    "P-ad OP-Crs C/90"
]
#def_cols = [
#gk_colss = [
#phys_cols = [

## Columns where lower is better
INVERTED_COLS = [
    "Mins/Gl",
    "Poss Lost/90",
    "Fouls Made",
    "Yel",
    "Red cards",
    "Off",
    "Goals Conceded",
]

## Derived column funcitons
def derived_columns(df):
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
    df["Tck C/90"] = df["Tck A/90"] * df["Tck R"] / 100
    df["K Tck/90"] = df["K Tck"] / df["Minutes"] * 90
    df["Fouls/90"] = df["Fouls Made"] / df["Minutes"] * 90
    df["P-ad Int/90"] = df["Int/90"] / (1-df["Possession"])
    df["P-ad Pres A/90"] = df["Pres A/90"] / (1-df["Possession"])
    df["P-ad Clr/90"] = df["Clr/90"] / (1-df["Possession"])
    df["P-ad Shts Blckd/90"] = df["Shts Blckd/90"] / (1-df["Possession"])
    df["P-ad Fouls/90"] = df["Fouls/90"] / (1-df["Possession"])
    df["Fouls/Yellow"] = df["Fouls Made"] / df["Yel"]
    df["Fouls/Red"] = df["Fouls Made"] / df["Red cards"]
    #Goalkeeping
    df["xGP/90"] = df["xGP"] / df["Minutes"] * 90
    df["P-ad xGP/90"] = df["xGP/90"] / (1-df["Possession"])
    df["Saves/90"] = (df["Svh"] + df["Svp"] + df["Svt"])  / df["Minutes"] * 90
    df["SvH Ratio"] = df["Svh"] / (df["Svh"] + df["Svp"] + df["Svt"])
    df["P-ad Saves/90"] = df["Saves/90"] / (1-df["Possession"])
    #Future additions to index intention:
    df["Shot Bias"] = df["Shot/90"] / df["Ps A/90"] * 100
    df["Progressive Rate"] = df["Pr passes/90"] / df["Ps A/90"] * 100
    df["Risky Pass Rate"] = df["OP-KP/90"] / df["Ps A/90"] * 100
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
uploaded_file = st.file_uploader("Upload FM CSV", type=["csv"])

##  Main App
if uploaded_file:
    df = load_data(uploaded_file)
    
    # Identify percentile columns
    percentile_cols = [
        col for col in df.columns
        if col not in desc_cols
    ]
    
    #Position names for dropdowns
    available_roles, available_sides = parse_positions(df["Best Pos"] + ", " + df["Sec. Position"])

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

    # Dropdowns for position and sides
    st.markdown("#### Positon Selection")
    col1, col2, col3 = st.columns(3)

    with col1:
        role_options = [f"{r} - {role_labels.get(r, r)}" for r in available_roles]
        selected_role_display = st.selectbox("Position", role_options)
        selected_role = selected_role_display.split(" - ")[0]

    with col2:
        side_options = [s for s in available_sides]
        selected_sides_display = st.multiselect(
            "Side(s)",
            available_sides,
            format_func=lambda x: side_labels.get(x, x),
            help="Leave empty to ignore sides (GK/DM/ST etc) & Player must be able to play ALL selected sides"
    )
    selected_sides = set(selected_sides_display)

    with col3:
        use_sec = st.checkbox("Include Secondary Positions", value=True)

    # Apply position filter
    if use_sec:
        pos_data = df["Best Pos"].fillna("") + ", " + df["Sec. Position"].fillna("")
    else:
        pos_data = df["Best Pos"].fillna("")
    
    mask = build_position_mask(pos_data, selected_role, selected_sides)
    filtered_df = df[mask].copy()

    st.write(f"{len(filtered_df)} players match filter")
    st.dataframe(filtered_df)

    if len(filtered_df) > 0:
        stat_cols = [c for c in filtered_df.columns if c not in desc_cols]
        for col in stat_cols:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
        
        ## what columns in the percentiles - review later for custom selection
        visible_cols=stat_cols

        ## calculate percentiles for visible columns

        if len(visible_cols) == 0 :
            st.warning("Select at least one column to display")
        

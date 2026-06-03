
import streamlit as st
import pandas as pd
import re
import numpy as np

st.set_page_config(page_title="FM Player Ranker", layout="wide")
st.title("Football Manager - Percentile Ranker")

# Columns where LOWER is BETTER (will be inverted for percentile calc)
INVERT_COLS = [
    "Mins/Gl",
    "Off",
    "Poss Lost/90",
    "Fouls Made",
    "Yel",
    "Red cards",
    "Recurring Injury",
    "Injury Susceptibility",
    "Goals Conceded",
]

# --- PIZZA CHART CATEGORY DEFINITIONS ---
PIZZA_CATEGORIES_OUTFIELD = {
    "Defence": [
        {"name": "Front-foot defending", "method": "derived_composite", 
         "components": ["Tck A/90_derived", "Int/90", "Pres A/90", "Fouls/90_derived"]},
        {"name": "Tackle success", "method": "single", "col": "Tck R"},
        {"name": "Back-foot defending", "method": "derived_composite",
         "components": ["Blk/90", "Clr/90", "Shts Blckd/90"]},
        {"name": "Loose ball recoveries", "method": "single", "col": "Poss Won/90"},
        {"name": "Aerial volume", "method": "single", "col": "Aer A/90"},
        {"name": "Aerial success", "method": "single", "col": "Hdr %"},
    ],
    "Possession": [
        {"name": "Ball retention", "method": "single", "col": "Pas %"},
        {"name": "Link-up play", "method": "single", "col": "Ps A/90"},
        {"name": "Progressive passing", "method": "single", "col": "Pr passes/90"},
    ],
    "Progression": [
        {"name": "Creative threat", "method": "blend_raw",
         "components": [("xA/90", 0.8), ("Assists/90_derived", 0.2)]},
        {"name": "OP crossing volume", "method": "single", "col": "OP-Crs A/90"},
        {"name": "OP crossing accuracy", "method": "single", "col": "OP-Crs C/90"},
        {"name": "Dribbling", "method": "single", "col": "Drb/90"},
        {"name": "Chance creation", "method": "single", "col": "OP-KP/90"},
    ],
    "Set Pieces": [
        {"name": "SP cross volume", "method": "single", "col": "SP-Crs A/90_derived"},
        {"name": "SP cross accuracy", "method": "single", "col": "SP-Crs C/90_derived"},
        {"name": "SP chance creation", "method": "single", "col": "Ch C/90"},
    ],
    "Attack": [
        {"name": "Goal threat", "method": "blend_raw",
         "components": [("xG/90", 0.7), ("Goals/90_derived", 0.3)]},
        {"name": "Shot frequency", "method": "single", "col": "Shot/90"},
        {"name": "Shot quality", "method": "single", "col": "xG/shot"},
    ],
    "Physical": [
        {"name": "Distance", "method": "single", "col": "Dist/90"},
        {"name": "Sprints", "method": "single", "col": "Sprints/90"},
    ],
}

PIZZA_CATEGORIES_GK = {
    "Goalkeeping": [
        {"name": "Save percentage", "method": "single", "col": "Sv %"},
        {"name": "Saves (high)", "method": "single", "col": "Svh"},
        {"name": "Saves (parried)", "method": "single", "col": "Svp"},
        {"name": "Saves (tipped)", "method": "single", "col": "Svt"},
        {"name": "Post-shot xG prevention", "method": "single", "col": "xGP"},
        {"name": "Clean sheets", "method": "single", "col": "Clean Sheets"},
        {"name": "Goals conceded", "method": "single", "col": "Goals Conceded", "invert": True},
        {"name": "Penalty save ratio", "method": "single", "col": "Pens Saved Ratio"},
    ],
}


def derive_stats(df):
    """Compute derived per-90 stats needed for pizza calculations."""
    minutes_per_90 = df["Minutes"] / 90
    df["Tck A/90_derived"] = df["Tck A"] / minutes_per_90
    df["Fouls/90_derived"] = df["Fouls Made"] / minutes_per_90
    df["Assists/90_derived"] = df["Assists"] / minutes_per_90
    df["Goals/90_derived"] = df["Goals"] / minutes_per_90
    df["SP-Crs A/90_derived"] = df["Crs A/90"] - df["OP-Crs A/90"]
    df["SP-Crs C/90_derived"] = df["Cr C/90"] - df["OP-Crs C/90"]
    return df


def compute_pizza_percentiles(df, categories):
    """Compute percentile for each pizza slice using Athletic methodology."""
    results = {}

    for category, slices in categories.items():
        for s in slices:
            name = s["name"]
            invert = s.get("invert", False)

            if s["method"] == "single":
                col = s["col"]
                if col in df.columns:
                    if invert:
                        results[name] = df[col].rank(pct=True, ascending=False) * 100
                    else:
                        results[name] = df[col].rank(pct=True, ascending=True) * 100
                else:
                    results[name] = pd.Series(np.nan, index=df.index)

            elif s["method"] == "derived_composite":
                composite = pd.Series(0.0, index=df.index)
                valid = True
                for comp_col in s["components"]:
                    if comp_col in df.columns:
                        composite += df[comp_col].fillna(0)
                    else:
                        valid = False
                        break
                if valid:
                    results[name] = composite.rank(pct=True, ascending=True) * 100
                else:
                    results[name] = pd.Series(np.nan, index=df.index)

            elif s["method"] == "blend_raw":
                blended = pd.Series(0.0, index=df.index)
                valid = True
                for comp_col, weight in s["components"]:
                    if comp_col in df.columns:
                        blended += df[comp_col].fillna(0) * weight
                    else:
                        valid = False
                        break
                if valid:
                    results[name] = blended.rank(pct=True, ascending=True) * 100
                else:
                    results[name] = pd.Series(np.nan, index=df.index)

    return pd.DataFrame(results, index=df.index).round(1)


def draw_pizza_chart(player_name, player_pizza, player_age, player_div, pizza_cats, cat_colours, ax):
    """Draw a single pizza chart on a given axes."""
    slice_names = []
    slice_values = []
    slice_colours = []

    for cat_name, slices in pizza_cats.items():
        colour = cat_colours.get(cat_name, "#95a5a6")
        for s in slices:
            slice_names.append(s["name"])
            val = player_pizza.get(s["name"], 0)
            slice_values.append(val if not pd.isna(val) else 0)
            slice_colours.append(colour)

    n = len(slice_names)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    width = 2 * np.pi / n

    bars = ax.bar(angles, slice_values, width=width, bottom=0,
                 color=slice_colours, alpha=0.8, edgecolor="white", linewidth=1)

    ax.set_xticks(angles)
    ax.set_xticklabels(slice_names, size=6, wrap=True)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75])
    ax.set_yticklabels(["25", "50", "75"], size=6, alpha=0.5)

    for angle, val in zip(angles, slice_values):
        ax.text(angle, val + 4, f"{val:.0f}", ha="center", va="bottom", size=5.5, weight="bold")

    ax.set_title(f"{player_name}\n(Age {player_age}, {player_div})",
               size=9, weight="bold", pad=12)


# --- POSITION PARSING ---
def parse_positions(position_series):
    roles = set()
    sides = set()
    for pos in position_series.unique():
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
    return sorted(roles), sorted(sides)


def player_matches(position_str, selected_role, selected_sides):
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
            if selected_sides.issubset(seg_sides):
                return True
            if len(selected_sides) == 0:
                return True
    return False


def safe_eval_formula(df, formula, available_cols):
    """Safely evaluate a user formula against the dataframe.

    Column names with special characters are referenced using backticks in df.eval(),
    or we replace them with safe placeholder names.
    """
    # Create a copy with sanitised column names for eval
    col_map = {}  # safe_name -> original_name
    reverse_map = {}  # original_name -> safe_name

    for col in available_cols:
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", col)
        # Avoid duplicates by appending index if needed
        if safe in col_map:
            safe = safe + "_" + str(len(col_map))
        col_map[safe] = col
        reverse_map[col] = safe

    # Replace column names in formula (longest first to avoid partial matches)
    eval_formula = formula
    for orig in sorted(reverse_map.keys(), key=len, reverse=True):
        eval_formula = eval_formula.replace(orig, reverse_map[orig])

    # Build a dataframe with safe column names
    eval_df = pd.DataFrame()
    for safe_name, orig_name in col_map.items():
        if orig_name in df.columns:
            eval_df[safe_name] = pd.to_numeric(df[orig_name], errors="coerce")

    # Evaluate
    result = eval_df.eval(eval_formula)
    return result


# --- MAIN APP ---
uploaded_file = st.file_uploader("Upload your FM data export (CSV)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, sep=';')
    df = derive_stats(df)

    available_roles, available_sides = parse_positions(df["Position"])

    role_labels = {
        "GK": "Goalkeeper", "D": "Defender", "WB": "Wing-Back",
        "DM": "Defensive Midfielder", "M": "Midfielder",
        "AM": "Attacking Midfielder", "ST": "Striker"
    }
    side_labels = {"L": "Left", "R": "Right", "C": "Centre"}

    # --- FILTERS ---
    st.markdown("### Filters")
    col1, col2 = st.columns(2)

    with col1:
        role_options = [f"{r} - {role_labels.get(r, r)}" for r in available_roles]
        selected_role_display = st.selectbox("Position", role_options)
        selected_role = selected_role_display.split(" - ")[0]

    with col2:
        side_options = [s for s in available_sides]
        selected_sides_display = st.multiselect(
            "Side(s)", options=side_options,
            format_func=lambda x: side_labels.get(x, x),
            help="Player must be able to play ALL selected sides"
        )
        selected_sides = set(selected_sides_display)

    # Filter players
    mask = df["Position"].apply(lambda x: player_matches(x, selected_role, selected_sides))
    filtered_df = df[mask].copy()

    st.markdown(f"**{len(filtered_df)} players** match the position filter")

    if len(filtered_df) > 0:
        # Identify numeric stat columns
        exclude_cols = ["Division", "Player", "Position", "Age", "Height", "Left Foot", "Right Foot"]
        stat_cols = [c for c in filtered_df.columns if c not in exclude_cols 
                     and not c.endswith("_derived")
                     and pd.to_numeric(filtered_df[c], errors="coerce").notna().any()]

        all_stat_cols = stat_cols + [c for c in filtered_df.columns if c.endswith("_derived")]
        for col in all_stat_cols:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")

        # --- CUSTOM METRICS ---
        st.markdown("### Custom Metrics")
        with st.expander("Create custom calculated stats", expanded=False):
            st.markdown("Define custom metrics using column names and arithmetic operators (`+`, `-`, `*`, `/`, `**`, parentheses).")
            st.markdown("Use exact column names from the reference below. The result is added as a new column.")

            # Reference of available columns
            with st.expander("Available column names"):
                col_ref_cols = st.columns(3)
                for i, col in enumerate(stat_cols):
                    with col_ref_cols[i % 3]:
                        st.code(col, language=None)

            # Session state for custom metrics
            if "custom_metrics" not in st.session_state:
                st.session_state["custom_metrics"] = []

            # Input for new metric
            st.markdown("---")
            cm_col1, cm_col2 = st.columns([1, 3])
            with cm_col1:
                new_metric_name = st.text_input("Metric name", placeholder="e.g. Goal Involvement", key="cm_name")
            with cm_col2:
                new_metric_formula = st.text_input("Formula", placeholder="e.g. (xA + xG) / (Minutes / 90)", key="cm_formula")

            cm_col3, cm_col4 = st.columns([1, 1])
            with cm_col3:
                lower_is_better = st.checkbox("Lower is better (invert)", key="cm_invert")
            with cm_col4:
                if st.button("Add metric", key="cm_add"):
                    if new_metric_name and new_metric_formula:
                        # Validate formula
                        try:
                            test_result = safe_eval_formula(filtered_df, new_metric_formula, stat_cols + [c for c in filtered_df.columns if c.endswith("_derived")])
                            st.session_state["custom_metrics"].append({
                                "name": new_metric_name,
                                "formula": new_metric_formula,
                                "invert": lower_is_better
                            })
                            st.success(f"Added: {new_metric_name} = {new_metric_formula}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Formula error: {e}")
                    else:
                        st.warning("Enter both a name and a formula.")

            # Display existing custom metrics
            if st.session_state["custom_metrics"]:
                st.markdown("**Active custom metrics:**")
                for i, cm in enumerate(st.session_state["custom_metrics"]):
                    inv_label = " â†“" if cm["invert"] else ""
                    mcol1, mcol2 = st.columns([4, 1])
                    with mcol1:
                        st.markdown(f"`{cm['name']}`{inv_label} = `{cm['formula']}`")
                    with mcol2:
                        if st.button("Remove", key=f"cm_remove_{i}"):
                            st.session_state["custom_metrics"].pop(i)
                            st.rerun()

                if st.button("Clear all custom metrics"):
                    st.session_state["custom_metrics"] = []
                    st.rerun()

        # Compute custom metrics and add to filtered_df
        custom_col_names = []
        for cm in st.session_state.get("custom_metrics", []):
            try:
                available = stat_cols + [c for c in filtered_df.columns if c.endswith("_derived")]
                filtered_df[cm["name"]] = safe_eval_formula(filtered_df, cm["formula"], available)
                custom_col_names.append(cm["name"])
                if cm["invert"] and cm["name"] not in INVERT_COLS:
                    INVERT_COLS.append(cm["name"])
            except Exception:
                pass  # Skip broken formulas silently

        # Update stat_cols to include custom metrics
        stat_cols = stat_cols + custom_col_names

        # --- STAT GROUP PRESETS ---
        STAT_GROUPS = {
            "Shooting": ["Goals", "Mins/Gl", "xG", "NP-xG", "xG-OP", "xG/90", "Conv %", "xG/shot", 
                        "Shot/90", "ShT/90", "Shots From Outside The Box Per 90 minutes", "Shot %", 
                        "Goals From Outside The Box", "Pens", "Pen/R", "Team Goals"],
            "Passing & Creativity": ["Assists", "xA", "xA/90", "Pas %", "Ps A/90", "Ch C/90", 
                                     "OP-KP/90", "Pr passes/90", "Crs A/90", "Cr C/90", 
                                     "OP-Crs A/90", "OP-Crs C/90"],
            "Dribbling & Possession": ["Drb/90", "Off", "Poss Lost/90", "Poss Won/90"],
            "Defending": ["Tck/90", "Int/90", "Pres A/90", "Tck R", "Tck A", "K Tck", 
                         "Blk/90", "Clr/90", "Shts Blckd/90"],
            "Discipline": ["Fouls Made", "Yel", "Red cards"],
            "Physical": ["Dist/90", "Sprints/90", "Aer A/90", "Hdr %", "K Hdrs/90"],
            "Injury": ["Recurring Injury", "Injury Susceptibility"],
            "Goalkeeping": ["Clean Sheets", "xGP", "MLG", "Sv %", "Svh", "Svp", "Svt", 
                           "Goals Conceded", "Pens Faced", "Pens Saved Ratio"],
            "Performance": ["Rating", "PoM", "Minutes"],
            "Custom": custom_col_names,
        }

        # --- COLUMN SELECTION ---
        st.markdown("### Column Selection")
        with st.expander("Show/Hide Stat Columns", expanded=False):
            st.markdown("**Quick select by group:**")
            preset_cols = st.columns(5)

            if "visible_cols" not in st.session_state:
                st.session_state["visible_cols"] = stat_cols.copy()

            group_names = [g for g in STAT_GROUPS.keys() if STAT_GROUPS[g]]  # only non-empty groups
            for i, group_name in enumerate(group_names):
                col_idx = i % 5
                with preset_cols[col_idx]:
                    if st.button(group_name, key=f"grp_{group_name}"):
                        group_cols = [c for c in STAT_GROUPS[group_name] if c in stat_cols]
                        if all(c in st.session_state["visible_cols"] for c in group_cols):
                            st.session_state["visible_cols"] = [c for c in st.session_state["visible_cols"] if c not in group_cols]
                        else:
                            current = set(st.session_state["visible_cols"])
                            current.update(group_cols)
                            st.session_state["visible_cols"] = [c for c in stat_cols if c in current]
                        st.rerun()

            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Select All"):
                    st.session_state["visible_cols"] = stat_cols.copy()
                    st.rerun()
            with col_b:
                if st.button("Deselect All"):
                    st.session_state["visible_cols"] = []
                    st.rerun()

            visible_cols = st.multiselect(
                "Visible stats", options=stat_cols,
                default=[c for c in st.session_state["visible_cols"] if c in stat_cols], 
                key="col_selector"
            )

        if len(visible_cols) == 0:
            st.warning("Select at least one stat column to display.")
        else:
            # Compute all percentiles
            all_percentiles = pd.DataFrame(index=filtered_df.index)
            for col in stat_cols:
                if col in filtered_df.columns:
                    if col in INVERT_COLS:
                        all_percentiles[col] = filtered_df[col].rank(pct=True, ascending=False) * 100
                    else:
                        all_percentiles[col] = filtered_df[col].rank(pct=True, ascending=True) * 100
            all_percentiles = all_percentiles.round(1)

            def colour_percentiles(val):
                if pd.isna(val):
                    return ""
                if isinstance(val, (int, float)):
                    if val >= 80:
                        return "background-color: #2d8a4e; color: white"
                    elif val >= 60:
                        return "background-color: #7bc47f"
                    elif val >= 40:
                        return "background-color: #f5f5a3"
                    elif val >= 20:
                        return "background-color: #f5a623"
                    else:
                        return "background-color: #d9534f; color: white"
                return ""

            # ===== COMPOSITE SCORE =====
            st.markdown("### Composite Score")
            with st.expander("Configure composite score", expanded=False):
                st.markdown("Set a **weight** (0 = ignore) and a **minimum percentile threshold** for each selected stat.")
                st.markdown("Players below ANY minimum threshold are excluded.")

                weights = {}
                min_thresholds = {}

                for i in range(0, len(visible_cols), 2):
                    cols = st.columns(2)
                    for j, c in enumerate(visible_cols[i:i+2]):
                        with cols[j]:
                            st.markdown(f"**{c}**" + (" â†“" if c in INVERT_COLS else ""))
                            weights[c] = st.slider(
                                f"Weight", min_value=0.0, max_value=3.0, value=1.0, step=0.5,
                                key=f"weight_{c}"
                            )
                            min_thresholds[c] = st.slider(
                                f"Min percentile", min_value=0, max_value=100, value=0, step=5,
                                key=f"min_{c}"
                            )

            composite_df = filtered_df[["Player", "Position", "Age", "Division"]].copy()
            composite_percentiles = all_percentiles[[c for c in visible_cols if c in all_percentiles.columns]].copy()

            exclusion_mask = pd.Series(True, index=filtered_df.index)
            for col in visible_cols:
                if col in all_percentiles.columns and min_thresholds[col] > 0:
                    exclusion_mask = exclusion_mask & (all_percentiles[col] >= min_thresholds[col])

            composite_df = composite_df[exclusion_mask].copy()
            composite_percentiles = composite_percentiles[exclusion_mask].copy()

            active_cols = [c for c in visible_cols if weights[c] > 0 and c in composite_percentiles.columns]

            if len(active_cols) > 0 and len(composite_df) > 0:
                total_weight = sum(weights[c] for c in active_cols)
                composite_df["Composite Score"] = sum(
                    composite_percentiles[c] * weights[c] for c in active_cols
                ) / total_weight
                composite_df["Composite Score"] = composite_df["Composite Score"].round(1)

                for c in active_cols:
                    composite_df[c] = composite_percentiles[c].values

                composite_df = composite_df.sort_values("Composite Score", ascending=False).reset_index(drop=True)

                st.markdown(f"**{len(composite_df)} players** survive the minimum thresholds")

                style_cols = ["Composite Score"] + active_cols
                styled_composite = composite_df.style.map(colour_percentiles, subset=style_cols)
                st.dataframe(styled_composite, use_container_width=True, height=500)
            elif len(composite_df) == 0:
                st.warning("No players meet all minimum thresholds. Relax your cutoffs.")
            else:
                st.warning("Set at least one stat weight above 0.")

            # ===== PIZZA CHARTS =====
            st.markdown("### Player Pizza Comparison")

            is_gk = selected_role == "GK"
            pizza_cats = PIZZA_CATEGORIES_GK if is_gk else PIZZA_CATEGORIES_OUTFIELD

            pizza_percentiles = compute_pizza_percentiles(filtered_df, pizza_cats)
            pizza_percentiles.index = filtered_df.index

            player_names = filtered_df["Player"].tolist()
            pcol1, pcol2 = st.columns(2)

            with pcol1:
                player_1 = st.selectbox("Player 1", player_names, index=0, key="pizza_p1")
            with pcol2:
                player_2 = st.selectbox("Player 2", ["None"] + player_names, index=0, key="pizza_p2")

            import matplotlib.pyplot as plt
            from matplotlib.patches import Patch

            cat_colours = {
                "Defence": "#e74c3c",
                "Possession": "#3498db",
                "Progression": "#2ecc71",
                "Set Pieces": "#9b59b6",
                "Attack": "#f39c12",
                "Physical": "#1abc9c",
                "Goalkeeping": "#e67e22",
            }

            show_two = player_2 != "None"

            if show_two:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5), subplot_kw=dict(polar=True))
            else:
                fig, ax1 = plt.subplots(1, 1, figsize=(5, 5), subplot_kw=dict(polar=True))

            p1_idx = filtered_df[filtered_df["Player"] == player_1].index[0]
            p1_pizza = pizza_percentiles.loc[p1_idx]
            p1_age = filtered_df.loc[p1_idx, "Age"]
            p1_div = filtered_df.loc[p1_idx, "Division"]
            draw_pizza_chart(player_1, p1_pizza, p1_age, p1_div, pizza_cats, cat_colours, ax1)

            if show_two:
                p2_idx = filtered_df[filtered_df["Player"] == player_2].index[0]
                p2_pizza = pizza_percentiles.loc[p2_idx]
                p2_age = filtered_df.loc[p2_idx, "Age"]
                p2_div = filtered_df.loc[p2_idx, "Division"]
                draw_pizza_chart(player_2, p2_pizza, p2_age, p2_div, pizza_cats, cat_colours, ax2)

            legend_patches = [Patch(color=cat_colours.get(cat, "#95a5a6"), label=cat) 
                             for cat in pizza_cats.keys()]
            fig.legend(handles=legend_patches, loc="lower center", ncol=len(pizza_cats), fontsize=7,
                      bbox_to_anchor=(0.5, -0.02))

            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

            with st.expander("Pizza chart values"):
                slice_names = [s["name"] for cat_slices in pizza_cats.values() for s in cat_slices]
                pizza_table = pd.DataFrame({"Slice": slice_names})
                pizza_table[player_1] = [p1_pizza.get(s, 0) for s in slice_names]
                if show_two:
                    pizza_table[player_2] = [p2_pizza.get(s, 0) for s in slice_names]
                pizza_table["Category"] = [cat for cat, slices in pizza_cats.items() for _ in slices]
                st.dataframe(pizza_table, use_container_width=True)

            # ===== PERCENTILE RANKINGS (collapsed) =====
            with st.expander("Percentile Rankings", expanded=False):
                percentile_df = all_percentiles[[c for c in visible_cols if c in all_percentiles.columns]].copy()
                display_df = filtered_df[["Player", "Position", "Age", "Division"]].reset_index(drop=True)
                percentile_display = percentile_df.reset_index(drop=True)
                result_df = pd.concat([display_df, percentile_display], axis=1)

                sort_col = st.selectbox(
                    "Sort by (percentile)", visible_cols,
                    index=visible_cols.index("Rating") if "Rating" in visible_cols else 0,
                    key="pct_sort"
                )
                result_df = result_df.sort_values(sort_col, ascending=False).reset_index(drop=True)

                inverted_visible = [c for c in visible_cols if c in INVERT_COLS]
                if inverted_visible:
                    st.caption(f"Inverted columns (lower is better): {', '.join(inverted_visible)}")

                styled = result_df.style.map(colour_percentiles, subset=[c for c in visible_cols if c in result_df.columns])
                st.dataframe(styled, use_container_width=True, height=600)

            # --- RAW VALUES ---
            with st.expander("Show raw values", expanded=False):
                sort_col_raw = visible_cols[visible_cols.index("Rating") if "Rating" in visible_cols else 0]
                raw_cols = [c for c in visible_cols if c in filtered_df.columns]
                raw_display = filtered_df[["Player", "Position", "Age", "Division"] + raw_cols].sort_values(
                    sort_col_raw, ascending=(sort_col_raw in INVERT_COLS)
                ).reset_index(drop=True)
                st.dataframe(raw_display, use_container_width=True, height=600)
else:
    st.info("Upload a CSV file exported from Football Manager to get started.")



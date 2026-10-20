# -*- coding: utf-8 -*-
"""
Interactive XRF companion dashboard.

This dashboard rebuilds the previous Dash app around the plots used in
explore_data_excel_plot_data_export_staticstics_17.04.26.py.

Run locally:
    python xray_companion_dashboard_rebuild.py

Open:
    http://127.0.0.1:8050/
"""

from pathlib import Path
import os
import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dash
from dash import dcc, html, Input, Output, dash_table


# =============================================================================
# Configuration
# =============================================================================

HOME_PATH = "/home/XRFScrap2026/mysite/"

# For PythonAnywhere deployment
DEPLOY_CHEM_PATH = HOME_PATH + "Dashboard_Daten_20.05.26.xlsx"
DEPLOY_CHEM_PATH = HOME_PATH + "Dashboard_Daten_20.05.26_NORMALIZED.xlsx"
DEPLOY_MORPH_PATH = HOME_PATH + "objektgroessen_von_fotos.xlsx"

# For local testing
LOCAL_CHEM_PATH = "Dashboard_Daten_20.05.26.xlsx"
LOCAL_CHEM_PATH = "Dashboard_Daten_20.05.26_NORMALIZED.xlsx"
LOCAL_MORPH_PATH = "objektgroessen_von_fotos.xlsx"

# Optional: original analysis workbook name
LOCAL_ORIGINAL_XLSX_PATH = "Daten/E40 Schrottliste neu 17.04.26_Gerald.xlsx"

# Prefer local file if present, otherwise PythonAnywhere path
if Path(LOCAL_CHEM_PATH).exists():
    XLSX_PATH = LOCAL_CHEM_PATH
elif Path(LOCAL_ORIGINAL_XLSX_PATH).exists():
    XLSX_PATH = LOCAL_ORIGINAL_XLSX_PATH
else:
    XLSX_PATH = DEPLOY_CHEM_PATH

# Morphological measurement workbook, used for the morphology tab.
if Path(LOCAL_MORPH_PATH).exists():
    MORPH_PATH = LOCAL_MORPH_PATH
else:
    MORPH_PATH = DEPLOY_MORPH_PATH

IMG_DIR = "assets/Objekt_Images"

# Column names used in the exploration script
ID_COL = "Objekt ID"
GUT_COL = 'Visible_Copper'
MAT_COL = "Materialtype"
FARBE_COL = "Colour "
ZUSTAND_COL = "Condition"
GEWICHT_COL = "Mass [g]"
GEWICHT_COL_ALT = "Mass"
ELEMENT_COL = "Cu"

THRESHOLDS = {
    0.40: "#d62728",
    0.20: "#ff7f0e",
    0.10: "#1f77b4",
    0.06: "#7f7f7f",
}

EAF_ELEMENTS_DEFAULT = ["Fe", "Co", "Cu", "Mo", "Ni", "Sn", "W"]

PLOT_TEMPLATE = "plotly_white"

# Limit only the visible raw data points in distribution plots.
# Box/violin summaries and statistics still use the complete dataset.
MAX_VISIBLE_POINTS_PER_ELEMENT = 250

# Internal helper column used to match chemistry and morphology rows robustly.
# This avoids mismatches such as 1234 vs 1234.0 vs "1234".
ID_KEY_COL = "__object_id_key__"


def normalize_object_id(value):
    """Return a stable string key for object IDs across Excel sheets."""
    if pd.isna(value):
        return ""

    text = str(value).strip()
    if text == "":
        return ""

    # Excel often turns integer IDs into floats, e.g. 1234 -> 1234.0
    try:
        number = float(text)
        if np.isfinite(number) and number.is_integer():
            return str(int(number))
    except Exception:
        pass

    return text


# =============================================================================
# Data preprocessing, copied from the exploration workflow
# =============================================================================

# Translation dictionary for Zustand
zustand_translation = {
    "Spule": "Coil",
    "Knäuel": "Tangle",
    "Geflecht": "Mesh",
    "Draht": "Wire",
    "Elektronik Komponente": "Electronic Component",
    "Einzelteil": "Single Part",
    "Schaumstoff": "Foam",
    "Kunststoffteil mit Schraube": "Fastening",
    "Cast": "Cast",
    "Feder": "Spring",
    "Massivteil leicht verformt": "Ductile",
    "Massivteil verformt": "Ductile",
    "Massivteil": "Ductile",
    "Gepresst": "Ductile",
    "Steinartig": "Cast",
    "Schraube": "Nuts & Bolts",
    "Beilagscheibe": "Nuts & Bolts",
    "Mutter": "Nuts & Bolts",
    "Plättchen": "Sheet",
    "Nuts & Bolts": "Fastening"
}


def load_and_preprocess_excel(path: str) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Load and clean the XRF workbook.

    Mirrors the exploration script:
    - remove rows without object IDs
    - require numeric weight and Cu values
    - translate/consolidate Zustand labels
    - apply manual relabeling rules
    - convert chemical element columns to numeric, treating '< LOD' as zero
    """
    df = pd.read_excel(path, header=0).copy()
    df = df.dropna(axis=1, how="all")

    # Stable weight alias: keep the exploration-script name available.
    if GEWICHT_COL not in df.columns and GEWICHT_COL_ALT in df.columns:
        df[GEWICHT_COL] = df[GEWICHT_COL_ALT]

    required_cols = [ID_COL, GEWICHT_COL, ELEMENT_COL]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {missing}. Available columns: {list(df.columns)}")

    df = df.loc[
        ~df[ID_COL].isna() & (df[ID_COL].astype(str).str.strip() != "")
    ].copy()
    df[ID_KEY_COL] = df[ID_COL].apply(normalize_object_id)

    df[GEWICHT_COL] = pd.to_numeric(df[GEWICHT_COL], errors="coerce")
    df[ELEMENT_COL] = pd.to_numeric(df[ELEMENT_COL], errors="coerce")
    df = df.dropna(subset=[GEWICHT_COL, ELEMENT_COL]).copy()

    if ZUSTAND_COL in df.columns:
        df[ZUSTAND_COL] = df[ZUSTAND_COL].replace(zustand_translation)

    if GUT_COL in df.columns and ZUSTAND_COL in df.columns:
        df.loc[(df[GUT_COL] == "Gutteil") & (df[ZUSTAND_COL] == "Coil"), GUT_COL] = "Schlechtteil"
        df.loc[(df[GUT_COL] == "Schlechtteil") & (df[ZUSTAND_COL] == "Spring"), GUT_COL] = "Gutteil"
        df.loc[(df[GUT_COL] == "Schlechtteil") & (df[ZUSTAND_COL] == "Nuts & Bolts"), GUT_COL] = "Gutteil"
        df.loc[(df[GUT_COL] == "Gutteil") & (df[ZUSTAND_COL] == "Single Part"), ZUSTAND_COL] = "Ductile"
        df.loc[(df[GUT_COL] == "Gutteil") & (df[ZUSTAND_COL] == "Plastic Part with Screw"), ZUSTAND_COL] = "Fastening"
        df.loc[(df[GUT_COL] == "Gutteil") & (df[ID_COL] == 3150), ZUSTAND_COL] = "Cast"
        df[ZUSTAND_COL] = df[ZUSTAND_COL].replace(zustand_translation)

    # Chemical columns in the exploration script start at column 7.
    chem_elements = [
        c for c in list(df.columns[7:])
        if isinstance(c, str)
        and c.strip()
        and not c.startswith("Unnamed")
        and c not in {GEWICHT_COL, GEWICHT_COL_ALT}
        and c != "__object_id_key__"
    ]

    for element in chem_elements:
        s = df[element].astype("string").str.strip()
        s = s.replace({"< LOD": pd.NA, "": pd.NA, "nan": pd.NA, "None": pd.NA})
        df[element] = pd.to_numeric(s, errors="coerce").fillna(0)

    chem_elements = sorted([c for c in chem_elements if c in df.columns], key=str)

    # Dashboard grouping columns: only keep ones that exist.
    group_cols = [c for c in [GUT_COL, MAT_COL, FARBE_COL, ZUSTAND_COL] if c in df.columns]

    return df, chem_elements, group_cols



def load_morphology_excel(path: str) -> tuple[pd.DataFrame, list[str]]:
    """Load optional morphology measurements for the morphology dashboard tab.

    The old dashboard used ``objektgroessen_von_fotos.xlsx`` and selected all
    columns after ``Objekt ID`` as morphology features. This loader is tolerant:
    if the workbook is missing, the rest of the dashboard still runs and the
    morphology tab shows a helpful message.
    """
    if not Path(path).exists():
        return pd.DataFrame(), []

    df_morph = pd.read_excel(path, engine="openpyxl", header=0).copy()
    df_morph = df_morph.dropna(axis=1, how="all")

    if ID_COL not in df_morph.columns:
        return pd.DataFrame(), []

    df_morph = df_morph.loc[
        ~df_morph[ID_COL].isna() & (df_morph[ID_COL].astype(str).str.strip() != "")
    ].copy()
    df_morph[ID_KEY_COL] = df_morph[ID_COL].apply(normalize_object_id)

    # Use numeric columns as morphology features; skip object IDs and empty columns.
    feature_cols = []
    for col in df_morph.columns:
        if col in {ID_COL, ID_KEY_COL} or not isinstance(col, str) or col.startswith("Unnamed") or col in {"Objekt ID","__object_id_key__"}:
            continue
        numeric = pd.to_numeric(df_morph[col], errors="coerce")
        if numeric.notna().any():
            df_morph[col] = numeric
            feature_cols.append(col)

    return df_morph, feature_cols


def weighted_mean(series, weights=None):
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return np.nan
    if weights is None:
        return clean.mean()
    w = pd.to_numeric(pd.Series(weights), errors="coerce").reindex(clean.index)
    valid = w.notna() & np.isfinite(w) & (w > 0)
    if not valid.any():
        return clean.mean()
    return np.average(clean.loc[valid], weights=w.loc[valid])


def weighted_median(series, weights=None):
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return np.nan
    if weights is None:
        return clean.median()

    w = pd.to_numeric(pd.Series(weights), errors="coerce").reindex(clean.index)
    valid = w.notna() & np.isfinite(w) & (w > 0)
    clean = clean.loc[valid]
    w = w.loc[valid]

    if clean.empty or w.empty or w.sum() <= 0:
        return np.nan

    sorter = np.argsort(clean.to_numpy())
    x = clean.to_numpy()[sorter]
    w = w.to_numpy()[sorter]
    cutoff = 0.5 * w.sum()
    return x[np.searchsorted(np.cumsum(w), cutoff, side="left")]


def compact_summary(df: pd.DataFrame, value_cols: list[str], group_col: str | None = None) -> pd.DataFrame:
    """Return compact statistics for display in the dashboard."""
    rows = []

    if group_col is None:
        iterator = [("All", df)]
    else:
        iterator = list(df.dropna(subset=[group_col]).groupby(group_col))

    for group_name, g in iterator:
        for col in value_cols:
            if col not in g.columns:
                continue
            values = pd.to_numeric(g[col], errors="coerce").dropna()
            weights = g.loc[values.index, GEWICHT_COL] if GEWICHT_COL in g.columns else None

            rows.append({
                "Group": group_name,
                "Element": col,
                "n": int(values.count()),
                "Min": round(values.min(), 3) if not values.empty else np.nan,
                "Mean": round(values.mean(), 3) if not values.empty else np.nan,
                "Weighted mean": round(weighted_mean(values, weights), 3) if not values.empty else np.nan,
                "Median": round(values.median(), 3) if not values.empty else np.nan,
                "Weighted median": round(weighted_median(values, weights), 3) if not values.empty else np.nan,
                "Q1": round(values.quantile(0.25), 3) if not values.empty else np.nan,
                "Q3": round(values.quantile(0.75), 3) if not values.empty else np.nan,
                "Max": round(values.max(), 3) if not values.empty else np.nan,
            })

    return pd.DataFrame(rows)


DF_FULL, CHEM_ELEMENTS, GROUP_COLS = load_and_preprocess_excel(XLSX_PATH)
EAF_ELEMENTS = [e for e in EAF_ELEMENTS_DEFAULT if e in CHEM_ELEMENTS]
DF_MORPH, MORPH_FEATURES = load_morphology_excel(MORPH_PATH)


def infer_good_particle_value(df: pd.DataFrame):
    """Return the value that represents the publication subset previously named Gutteil.

    The dashboard originally used German labels (Gutteil/Schlechtteil). After
    column renaming, some workbooks may use English/boolean labels instead.
    This helper keeps the analysis tabs functional without hard-coding only
    one spelling.
    """
    if GUT_COL not in df.columns:
        return None

    values = list(df[GUT_COL].dropna().unique())
    if not values:
        return None

    candidates = [
        "Gutteil", "Good", "good", "Yes", "yes", "True", "true",
        True, 1, "1", "Visible", "visible"
    ]
    value_map = {str(v).strip().lower(): v for v in values}

    for candidate in candidates:
        key = str(candidate).strip().lower()
        if key in value_map:
            return value_map[key]

    # Fallback: keep the app running and use the first available category.
    return values[0]


GOOD_PARTICLE_VALUE = infer_good_particle_value(DF_FULL)


# =============================================================================
# Figure builders
# =============================================================================

def filter_particle_class(df: pd.DataFrame, particle_class: str) -> pd.DataFrame:
    if particle_class == "All particles" or GUT_COL not in df.columns or particle_class is None:
        return df.copy()
    return df[df[GUT_COL].astype(str) == str(particle_class)].copy()


def clean_good_condition_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if ZUSTAND_COL in out.columns:
        out = out[out[ZUSTAND_COL] != "Single Part"]
        out = out[out[ZUSTAND_COL] != "Plastic Part with Screw"]
    return out


def make_element_distribution_figure(df, elements, plot_type="Box", log_scale=True, title="Chemical element distribution"):
    if not elements:
        return go.Figure().update_layout(title="Select at least one element")

    elements = [e for e in elements if e in df.columns]
    if not elements:
        return go.Figure().update_layout(title="Selected elements are not available")

    data = df[[ID_COL] + elements].copy()
    long = data.melt(
        id_vars=[ID_COL],
        value_vars=elements,
        var_name="Element",
        value_name="Concentration"
    )
    long["Concentration"] = pd.to_numeric(long["Concentration"], errors="coerce")
    long = long.dropna(subset=["Concentration"])

    # Draw the statistical layer from the complete dataset, but draw only a
    # capped sample of visible raw points. This keeps the app responsive while
    # preserving the correct box/violin summaries.
    if MAX_VISIBLE_POINTS_PER_ELEMENT is None:
        points = long.copy()
    else:
        points = (
            long.groupby("Element", group_keys=False)
            .apply(lambda g: g.sample(
                n=min(len(g), MAX_VISIBLE_POINTS_PER_ELEMENT),
                random_state=42
            ))
            .reset_index(drop=True)
        )

    fig = go.Figure()

    for i, element in enumerate(elements):
        full_values = long.loc[long["Element"] == element, "Concentration"]
        sampled = points.loc[points["Element"] == element]

        if plot_type == "Violin / raincloud":
            fig.add_trace(
                go.Violin(
                    x=[element] * len(full_values),
                    y=full_values,
                    name=element,
                    box_visible=True,
                    meanline_visible=False,
                    points=False,
                    opacity=0.55,
                    showlegend=False,
                )
            )
        else:
            fig.add_trace(
                go.Box(
                    x=[element] * len(full_values),
                    y=full_values,
                    name=element,
                    boxpoints=False,
                    showlegend=False,
                )
            )

        if not sampled.empty:
            fig.add_trace(
                go.Scatter(
                    x=sampled["Element"],
                    y=sampled["Concentration"],
                    mode="markers",
                    marker=dict(size=4, opacity=0.45),
                    customdata=sampled[[ID_COL]].to_numpy(),
                    hovertemplate=(
                        "<b>Object ID:</b> %{customdata[0]}<br>"
                        "<b>Element:</b> %{x}<br>"
                        "<b>Concentration:</b> %{y:.3f} wt.%<extra></extra>"
                    ),
                    name=f"{element} points",
                    showlegend=False,
                )
            )

    fig.update_layout(
        template=PLOT_TEMPLATE,
        title=title,
        height=650,
        showlegend=False,
    )

    if log_scale:
        fig.update_yaxes(type="log", title="Concentration [wt.%] (log scale)")
    else:
        fig.update_yaxes(title="Concentration [wt.%]")

    fig.update_xaxes(categoryorder="array", categoryarray=elements)
    return fig

def add_threshold_lines(fig):
    for threshold, color in THRESHOLDS.items():
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                line=dict(color=color, dash="dot", width=2),
                name=f"{threshold:.2f}% threshold",
                showlegend=True,
            )
        )

        fig.add_hline(
            y=threshold,
            line_dash="dot",
            line_color=color,
            line_width=2,
            opacity=0.9,
        )

    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.8)",
        )
    )

    return fig


def make_eaf_condition_figure(df, element="Cu", group_col=ZUSTAND_COL, particle_class="All particles", log_scale=True):
    """Interactive FIG13 equivalent: selected EAF element by condition/group."""
    if element not in df.columns:
        return go.Figure().update_layout(title=f"Missing element column: {element}")

    d = clean_good_condition_df(filter_particle_class(df, particle_class))
    if group_col not in d.columns:
        return go.Figure().update_layout(title=f"Missing group column: {group_col}")

    d = d.dropna(subset=[group_col, element]).copy()
    d[element] = pd.to_numeric(d[element], errors="coerce")
    d = d.dropna(subset=[element])

    if d.empty:
        return go.Figure().update_layout(title=f"No data available for {element} by {group_col}")

    order = sorted(d[group_col].astype(str).unique())

    fig = px.violin(
        d,
        x=group_col,
        y=element,
        color=group_col,
        box=True,
        points="all",
        category_orders={group_col: order},
        hover_data=[ID_COL, GEWICHT_COL],
        template=PLOT_TEMPLATE,
        title=f"FIG13 equivalent — {element} distribution in {particle_class} by {group_col}",
    )
    fig.update_traces(jitter=0.25, marker_size=5, opacity=0.75)

    # Only Cu has the publication threshold lines from the exploration script.
    if element == "Cu" and not python_anywhere:
        add_threshold_lines(fig)

    median_value = d[element].median()
    fig.add_annotation(
        xref="paper", yref="paper", x=0.02, y=0.98,
        text=f"Median {element} overall: {median_value:.3f} wt.%",
        showarrow=False,
        bgcolor="white",
        bordercolor="lightgrey",
    )

    fig.update_yaxes(
        type="log" if log_scale else "linear",
        title=f"{element} concentration [wt.%]" + (" (log scale)" if log_scale else ""),
    )
    fig.update_layout(showlegend=False, height=650)
    return fig


def make_mass_vs_eaf_element_comparison(df, element="Cu", group_a="Cast", group_b="Ductile", particle_class="All particles", log_scale=True):
    """Interactive FIG14 equivalent: mass vs selected EAF element for two conditions."""
    if element not in df.columns:
        return go.Figure().update_layout(title=f"Missing element column: {element}")

    # Use the selected particle subset instead of hard-coding the former good-particle subset.
    d = filter_particle_class(df, particle_class)
    d = d.dropna(subset=[ZUSTAND_COL, GEWICHT_COL, element]).copy()
    d[GEWICHT_COL] = pd.to_numeric(d[GEWICHT_COL], errors="coerce")
    d[element] = pd.to_numeric(d[element], errors="coerce")
    d = d.dropna(subset=[GEWICHT_COL, element])

    groups = [group_a, group_b]
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=groups,
        shared_xaxes=True,
        shared_yaxes=True,
    )

    for idx, group in enumerate(groups, start=1):
        g = d[d[ZUSTAND_COL] == group].copy()

        if element == "Cu" and not python_anywhere:
            colors = []
            for value in g[element]:
                color = "#1f77b4"
                for threshold, threshold_color in THRESHOLDS.items():
                    if value > threshold:
                        color = threshold_color
                        break
                colors.append(color)
        else:
            colors = "#1f77b4"

        fig.add_trace(
            go.Scatter(
                x=g[GEWICHT_COL],
                y=g[element],
                mode="markers",
                marker=dict(color=colors, size=8, line=dict(color="black", width=0.5), opacity=0.7),
                customdata=np.stack([g[ID_COL], g[ZUSTAND_COL]], axis=-1) if not g.empty else None,
                hovertemplate=(
                    "<b>Object ID:</b> %{customdata[0]}<br>"
                    "<b>Condition:</b> %{customdata[1]}<br>"
                    "<b>Weight:</b> %{x:.2f} g<br>"
                    f"<b>{element}:</b> " + "%{y:.3f} wt.%<extra></extra>"
                ),
                name=group,
            ),
            row=1,
            col=idx,
        )

        if element == "Cu" and not python_anywhere:
            counts_text = f"Total particles: {len(g)}<br>"
            for threshold in THRESHOLDS:
                count = int((g[element] > threshold).sum())
                percentage = 100 * count / len(g) if len(g) else 0
                counts_text += f"&gt; {threshold:.2f}%: {count} ({percentage:.1f}%)<br>"
        else:
            counts_text = (
                f"Total particles: {len(g)}<br>"
                f"Median {element}: {g[element].median():.3f} wt.%<br>" if len(g) else "Total particles: 0<br>"
            )

        fig.add_annotation(
            text=counts_text,
            xref=f"x{idx if idx > 1 else ''} domain",
            yref=f"y{idx if idx > 1 else ''} domain",
            x=0.98,
            y=0.98,
            showarrow=False,
            align="right",
            bgcolor="white",
            bordercolor="lightgrey",
        )


    if element == "Cu" and not python_anywhere:
        for c in [1, 2]:
            for threshold, color in THRESHOLDS.items():
                fig.add_hline(
                    y=threshold,
                    line_dash="dot",
                    line_color=color,
                    opacity=0.9,
                )


    fig.update_xaxes(title="Weight [g]")
    fig.update_yaxes(title=f"{element} concentration [wt.%]" + (" (log scale)" if log_scale else ""))
    if log_scale:
        fig.update_yaxes(type="log")

    fig.update_layout(
        title=f"FIG14 equivalent — {group_a} vs. {group_b}: individual {element} content ({particle_class})",
        template=PLOT_TEMPLATE,
        height=650,
        showlegend=False,
    )
    return fig

def aggregate_composition(df, elements, mode="weighted_median", particle_class=GOOD_PARTICLE_VALUE):
    d = filter_particle_class(df, particle_class)
    d = d.dropna(subset=[ZUSTAND_COL]).copy()
    elements = [e for e in elements if e in d.columns]

    def aggregate_group(g):
        out = {}
        for element in elements:
            values = pd.to_numeric(g[element], errors="coerce").fillna(0)
            weights = g[GEWICHT_COL] if GEWICHT_COL in g.columns else None

            if mode == "mean":
                out[element] = values.mean()
            elif mode == "weighted_mean":
                out[element] = weighted_mean(values, weights)
            elif mode == "median":
                out[element] = values.median()
            elif mode == "weighted_median":
                out[element] = weighted_median(values, weights)
            else:
                out[element] = weighted_median(values, weights)
        return pd.Series(out)

    if d.empty or not elements:
        return pd.DataFrame(columns=elements).rename_axis(ZUSTAND_COL)

    composition = d.groupby(ZUSTAND_COL, as_index=True).apply(aggregate_group)

    # Depending on pandas version and empty-group edge cases, groupby.apply can
    # return remnants of the input frame. Keep only the requested element columns
    # so reset_index() cannot collide with an existing Condition column.
    composition = composition.loc[:, [e for e in elements if e in composition.columns]]

    if "Cu" in composition.columns:
        composition = composition.sort_values("Cu", ascending=False)

    composition.index.name = ZUSTAND_COL
    return composition.round(3)


def make_composition_heatmap(df, elements, mode="weighted_median", particle_class=GOOD_PARTICLE_VALUE):
    composition = aggregate_composition(df, elements, mode=mode, particle_class=particle_class)
    if composition.empty:
        return go.Figure().update_layout(title="No composition data available")

    fig = px.imshow(
        composition,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="YlOrBr",
        template=PLOT_TEMPLATE,
        title=f"FIG12 — {mode.replace('_', ' ').title()} element concentration ({particle_class})",
        labels=dict(x="Element", y="Condition", color="wt.%"),
    )
    fig.update_layout(height=max(500, 55 * len(composition.index)))
    return fig


def make_stats_table(df, elements, group_col=None):
    stats = compact_summary(df, elements, group_col=group_col)
    return stats.to_dict("records"), [{"name": c, "id": c} for c in stats.columns]


def get_filtered_morphology_df(particle_class="All particles", condition="All"):
    """Return morphology rows for the selected dashboard filters.

    The morphology workbook is already a valid standalone dataset. Therefore,
    the default view should show the complete morphology table and should not
    depend on a successful chemistry-table join. Chemistry filters are only
    applied when the user explicitly selects a particle subset or condition.
    """
    if DF_MORPH.empty or not MORPH_FEATURES:
        return pd.DataFrame()

    # Default morphology view: show all morphology measurements directly.
    # This prevents an empty plot when the public/normalized chemistry file does
    # not contain exactly the same object-id universe as the morphology file.
    if (particle_class in [None, "All particles"]) and (condition in [None, "All"]):
        return DF_MORPH.copy()

    chem_subset = filter_particle_class(DF_FULL, particle_class)

    if condition != "All" and ZUSTAND_COL in chem_subset.columns:
        chem_subset = chem_subset[chem_subset[ZUSTAND_COL].astype(str) == str(condition)]

    if ID_KEY_COL not in chem_subset.columns or ID_KEY_COL not in DF_MORPH.columns:
        return pd.DataFrame()

    valid_ids = set(chem_subset[ID_KEY_COL].dropna().astype(str))
    out = DF_MORPH[DF_MORPH[ID_KEY_COL].astype(str).isin(valid_ids)].copy()
    return out


def make_morphology_distribution_figure(particle_class, condition, features, histnorm=""):
    """Interactive morphology histogram grid, adapted from the old dashboard."""
    if DF_MORPH.empty or not MORPH_FEATURES:
        return go.Figure().update_layout(
            title=f"Morphology file not found or invalid: {MORPH_PATH}"
        )

    features = [f for f in (features or []) if f in MORPH_FEATURES]
    if not features:
        return go.Figure().update_layout(title="Select at least one morphology feature")

    d = get_filtered_morphology_df(particle_class=particle_class, condition=condition)
    if d.empty:
        chem_subset = filter_particle_class(DF_FULL, particle_class)
        if condition != "All" and ZUSTAND_COL in chem_subset.columns:
            chem_subset = chem_subset[chem_subset[ZUSTAND_COL].astype(str) == str(condition)]
        return go.Figure().update_layout(
            title=(
                "No morphology data available for this filtered selection. "
                "Try Particle subset = All particles and Condition = All. "
                f"(chemistry rows after filtering: {len(chem_subset)}, "
                f"morphology rows loaded: {len(DF_MORPH)})"
            )
        )

    cols = 3
    rows = math.ceil(len(features) / cols)
    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=features,
        shared_xaxes=False,
        shared_yaxes=False,
    )

    for i, feature in enumerate(features):
        row = (i // cols) + 1
        col = (i % cols) + 1
        values = pd.to_numeric(d[feature], errors="coerce").dropna()
        fig.add_trace(
            go.Histogram(
                x=values,
                name=feature,
                histnorm=histnorm,
                marker_line_width=0.5,
                opacity=0.85,
            ),
            row=row,
            col=col,
        )

    fig.update_layout(
        title=f"Morphological distributions — {particle_class}" + (f" / {condition}" if condition != "All" else ""),
        template=PLOT_TEMPLATE,
        height=max(520, 320 * rows),
        showlegend=False,
        margin=dict(t=70, b=50, l=50, r=40),
    )
    return fig


def make_morphology_stats_table(particle_class, condition, features):
    if DF_MORPH.empty or not MORPH_FEATURES:
        return [], []
    features = [f for f in (features or []) if f in MORPH_FEATURES]
    d = get_filtered_morphology_df(particle_class=particle_class, condition=condition)
    rows = []
    for feature in features:
        values = pd.to_numeric(d[feature], errors="coerce").dropna()
        rows.append({
            "Feature": feature,
            "n": int(values.count()),
            "Min": round(values.min(), 3) if not values.empty else np.nan,
            "Mean": round(values.mean(), 3) if not values.empty else np.nan,
            "Median": round(values.median(), 3) if not values.empty else np.nan,
            "Q1": round(values.quantile(0.25), 3) if not values.empty else np.nan,
            "Q3": round(values.quantile(0.75), 3) if not values.empty else np.nan,
            "Max": round(values.max(), 3) if not values.empty else np.nan,
        })
    stats = pd.DataFrame(rows)
    return stats.to_dict("records"), [{"name": c, "id": c} for c in stats.columns]


# =============================================================================
# Dash app
# =============================================================================

app = dash.Dash(__name__)
server = app.server
python_anywhere = Path("/home/XRFScrap2026").exists()

if python_anywhere:
    app.title = "XRF Scrap Dashboard"
else:
    app.title = "LOCAL XRF Scrap Dashboard"

particle_options = ["All particles"]
if GUT_COL in DF_FULL.columns:
    particle_options += [str(x) for x in sorted(DF_FULL[GUT_COL].dropna().astype(str).unique())]

group_options = [c for c in [ZUSTAND_COL, MAT_COL, FARBE_COL, GUT_COL] if c in DF_FULL.columns]
condition_options = ["All"]
if ZUSTAND_COL in DF_FULL.columns:
    condition_options += [str(x) for x in sorted(DF_FULL[ZUSTAND_COL].dropna().astype(str).unique())]

default_morph_features = MORPH_FEATURES[:9] if MORPH_FEATURES else []

app.layout = html.Div(
    style={
        "fontFamily": "Arial, sans-serif",
        "backgroundColor": "#f4f4f9",
        "padding": "24px",
    },
    children=[
        html.Div(
    style={
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "space-between",
        "padding": "10px 20px",
        "backgroundColor": "#ffffff",
        "borderBottom": "2px solid #d9d9d9",
        "marginBottom": "25px",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.08)"
    },
    children=[

                # Left logo
                html.Img(
                    src="https://www.k1-met.com/fileadmin/_processed_/8/4/csm_KIRAMET_Logo_hoch_bunt_mit_Claim_c9189b1700.png",
                    style={
                        "height": "90px",
                        "objectFit": "contain"
                    }
                ),

                # Center title
                html.Div(
                    [
                        html.H1(
                            "KIRAMET Waste Characterisation Dashboard",
                            style={
                                "margin": "0",
                                "fontSize": "34px",
                                "fontWeight": "700",
                                "color": "#333333",
                                "textAlign": "center"
                            }
                        ),

                        html.P(
                            "Interactive visualization of morphology and chemical composition data",
                            style={
                                "margin": "4px 0 0 0",
                                "color": "#666666",
                                "fontSize": "16px",
                                "textAlign": "center"
                            }
                        )
                    ],
                    style={
                        "flexGrow": "1",
                        "paddingLeft": "20px",
                        "paddingRight": "20px"
                    }
                ),

                # Right logo
                html.Img(
                    src="https://www.unileoben.ac.at/_assets/2d2b68a2b5380aad6da53f45d7d45c66/Images/Logo.svg",
                    style={
                        "height": "90px",
                        "objectFit": "contain"
                    }
                )
            ]
        ),

        html.Div(
            style={
                "backgroundColor": "#fff7e6",
                "border": "1px solid #ffd591",
                "padding": "10px 14px",
                "marginBottom": "18px",
                "borderRadius": "6px",
                "color": "#5c3b00",
                "fontSize": "14px",
            },
            children=[
                html.B("Data note: "),
                "Chemical values shown in this public dashboard are normalized relative signals. ",
                "The original chemistry values were divided by the global maximum value in the source workbook. ",
                "Axes and tables therefore show dimensionless normalized signals rather than wt.% concentrations."
            ],
        ),

        dcc.Tabs([
            dcc.Tab(label="Element distributions", children=[
                html.Div(className="tab-content", style={"padding": "20px", "backgroundColor": "white"}, children=[
                    html.H2("FIG6 / FIG8 / FIG10 — Chemical element distributions"),
                    html.Div([
                        html.Div([
                            html.Label("Particle subset"),
                            dcc.Dropdown(
                                id="dist-particle-class",
                                options=[{"label": x, "value": x} for x in particle_options],
                                value="All particles",
                                clearable=False,
                            ),
                        ], style={"width": "23%", "display": "inline-block", "marginRight": "1%"}),

                        html.Div([
                            html.Label("Plot type"),
                            dcc.Dropdown(
                                id="dist-plot-type",
                                options=[{"label": x, "value": x} for x in ["Box", "Violin / raincloud"]],
                                value="Box",
                                clearable=False,
                            ),
                        ], style={"width": "23%", "display": "inline-block", "marginRight": "1%"}),

                        html.Div([
                            html.Label("Scale"),
                            dcc.RadioItems(
                                id="dist-log-scale",
                                options=[{"label": "Log", "value": "log"}, {"label": "Linear", "value": "linear"}],
                                value="log",
                                inline=True,
                            ),
                        ], style={"width": "18%", "display": "inline-block", "verticalAlign": "top"}),

                        html.Div([
                            html.Label("Elements"),
                            dcc.Dropdown(
                                id="dist-elements",
                                options=[{"label": e, "value": e} for e in CHEM_ELEMENTS],
                                value=CHEM_ELEMENTS,
                                multi=True,
                            ),
                        ], style={"width": "100%", "display": "block", "marginTop": "10px"}),
                    ]),
                    dcc.Graph(id="element-distribution-graph"),
                    html.H3("Compact statistics"),
                    dash_table.DataTable(
                        id="element-distribution-stats",
                        page_size=12,
                        sort_action="native",
                        filter_action="native",
                        style_table={"overflowX": "auto"},
                        style_cell={"fontSize": "12px", "padding": "6px"},
                    ),
                ]),
            ]),

            dcc.Tab(label="EAF elements", children=[
                html.Div(style={"padding": "20px", "backgroundColor": "white"}, children=[
                    html.H2("FIG7 / FIG9 / FIG11 — EAF-relevant element distributions"),
                    html.Div([
                        html.Label("Particle subset"),
                        dcc.Dropdown(
                            id="eaf-particle-class",
                            options=[{"label": x, "value": x} for x in particle_options],
                            value="All particles",
                            clearable=False,
                        ),
                    ], style={"width": "30%"}),
                    dcc.Graph(id="eaf-distribution-graph"),
                ]),
            ]),



            dcc.Tab(label="EAF element by condition", children=[
                html.Div(style={"padding": "20px", "backgroundColor": "white"}, children=[
                    html.H2("FIG13 equivalent — EAF element distribution by condition"),
                    html.Div([
                        html.Div([
                            html.Label("Particle subset"),
                            dcc.Dropdown(
                                id="condition-particle-class",
                                options=[{"label": x, "value": x} for x in particle_options],
                                value=GOOD_PARTICLE_VALUE if GOOD_PARTICLE_VALUE in particle_options else "All particles",
                                clearable=False,
                            ),
                        ], style={"width": "30%", "display": "inline-block", "marginRight": "2%"}),
                        html.Div([
                            html.Label("EAF element"),
                            dcc.Dropdown(
                                id="condition-element",
                                options=[{"label": e, "value": e} for e in EAF_ELEMENTS],
                                value="Cu" if "Cu" in EAF_ELEMENTS else (EAF_ELEMENTS[0] if EAF_ELEMENTS else None),
                                clearable=False,
                            ),
                        ], style={"width": "30%", "display": "inline-block", "marginRight": "2%"}),
                        html.Div([
                            html.Label("Grouping"),
                            dcc.Dropdown(
                                id="condition-group-col",
                                options=[{"label": x, "value": x} for x in group_options],
                                value=ZUSTAND_COL if ZUSTAND_COL in group_options else group_options[0],
                                clearable=False,
                            ),
                        ], style={"width": "30%", "display": "inline-block"}),
                    ]),
                    dcc.Graph(id="eaf-condition-graph"),
                    html.H3("Element statistics by group"),
                    dash_table.DataTable(
                        id="eaf-condition-stats",
                        page_size=12,
                        sort_action="native",
                        filter_action="native",
                        style_table={"overflowX": "auto"},
                        style_cell={"fontSize": "12px", "padding": "6px"},
                    ),
                ]),
            ]),

            dcc.Tab(label="Mass vs EAF element", children=[
                html.Div(style={"padding": "20px", "backgroundColor": "white"}, children=[
                    html.H2("FIG14 equivalent — Mass vs selected EAF element"),
                    html.Div([
                        html.Div([
                            html.Label("Particle subset"),
                            dcc.Dropdown(
                                id="scatter-particle-class",
                                options=[{"label": x, "value": x} for x in particle_options],
                                value="All particles",
                                clearable=False,
                            ),
                        ], style={"width": "23%", "display": "inline-block", "marginRight": "1%"}),
                        html.Div([
                            html.Label("EAF element"),
                            dcc.Dropdown(
                                id="scatter-element",
                                options=[{"label": e, "value": e} for e in EAF_ELEMENTS],
                                value="Cu" if "Cu" in EAF_ELEMENTS else (EAF_ELEMENTS[0] if EAF_ELEMENTS else None),
                                clearable=False,
                            ),
                        ], style={"width": "23%", "display": "inline-block", "marginRight": "1%"}),
                        html.Div([
                            html.Label("Group A"),
                            dcc.Dropdown(
                                id="scatter-group-a",
                                options=[{"label": x, "value": x} for x in sorted(DF_FULL[ZUSTAND_COL].dropna().unique())],
                                value="Cast" if "Cast" in set(DF_FULL[ZUSTAND_COL].dropna()) else sorted(DF_FULL[ZUSTAND_COL].dropna().unique())[0],
                                clearable=False,
                            ),
                        ], style={"width": "25%", "display": "inline-block", "marginRight": "1%"}),
                        html.Div([
                            html.Label("Group B"),
                            dcc.Dropdown(
                                id="scatter-group-b",
                                options=[{"label": x, "value": x} for x in sorted(DF_FULL[ZUSTAND_COL].dropna().unique())],
                                value="Ductile" if "Ductile" in set(DF_FULL[ZUSTAND_COL].dropna()) else sorted(DF_FULL[ZUSTAND_COL].dropna().unique())[-1],
                                clearable=False,
                            ),
                        ], style={"width": "25%", "display": "inline-block"}),
                    ]),
                    dcc.Graph(id="mass-vs-eaf-element-graph"),
                ]),
            ]),

            dcc.Tab(label="Composition heatmap", children=[
                html.Div(style={"padding": "20px", "backgroundColor": "white"}, children=[
                    html.H2("FIG12 — Element composition heatmap"),
                    html.Div([
                        html.Div([
                            html.Label("Particle subset"),
                            dcc.Dropdown(
                                id="heatmap-particle-class",
                                options=[{"label": x, "value": x} for x in particle_options],
                                value="All particles",
                                clearable=False,
                            ),
                        ], style={"width": "25%", "display": "inline-block", "marginRight": "1%"}),
                        html.Div([
                            html.Label("Aggregation"),
                            dcc.Dropdown(
                                id="heatmap-mode",
                                options=[
                                    {"label": "Mean", "value": "mean"},
                                    {"label": "Weighted mean", "value": "weighted_mean"},
                                    {"label": "Median", "value": "median"},
                                    {"label": "Weighted median", "value": "weighted_median"},
                                ],
                                value="weighted_median",
                                clearable=False,
                            ),
                        ], style={"width": "25%", "display": "inline-block", "marginRight": "1%"}),
                        html.Div([
                            html.Label("Elements"),
                            dcc.Dropdown(
                                id="heatmap-elements",
                                options=[{"label": e, "value": e} for e in CHEM_ELEMENTS],
                                value=EAF_ELEMENTS if EAF_ELEMENTS else CHEM_ELEMENTS[:7],
                                multi=True,
                            ),
                        ], style={"width": "48%", "display": "inline-block"}),
                    ]),
                    dcc.Graph(id="composition-heatmap"),
                    html.H3("Heatmap values"),
                    dash_table.DataTable(
                        id="composition-table",
                        page_size=20,
                        sort_action="native",
                        filter_action="native",
                        style_table={"overflowX": "auto"},
                        style_cell={"fontSize": "12px", "padding": "6px"},
                    ),
                ]),
            ]),

            dcc.Tab(label="Morphology", children=[
                html.Div(style={"padding": "20px", "backgroundColor": "white"}, children=[
                    html.H2("Morphological distributions"),
                    html.P(
                        "Morphological measurements are loaded from objektgroessen_von_fotos.xlsx and filtered by Object ID to match the selected particle subset.",
                        style={"color": "#666666"},
                    ),
                    html.Div([
                        html.Div([
                            html.Label("Particle subset"),
                            dcc.Dropdown(
                                id="morph-particle-class",
                                options=[{"label": x, "value": x} for x in particle_options],
                                value="All particles",
                                clearable=False,
                            ),
                        ], style={"width": "23%", "display": "inline-block", "marginRight": "1%"}),
                        html.Div([
                            html.Label("Condition"),
                            dcc.Dropdown(
                                id="morph-condition",
                                options=[{"label": x, "value": x} for x in condition_options],
                                value="All",
                                clearable=False,
                            ),
                        ], style={"width": "23%", "display": "inline-block", "marginRight": "1%"}),
                        html.Div([
                            html.Label("Histogram normalisation"),
                            dcc.Dropdown(
                                id="morph-histnorm",
                                options=[
                                    {"label": "Absolute", "value": ""},
                                    {"label": "Percent", "value": "percent"},
                                    {"label": "Probability", "value": "probability"},
                                    {"label": "Density", "value": "density"},
                                    {"label": "Probability density", "value": "probability density"},
                                ],
                                value="",
                                clearable=False,
                            ),
                        ], style={"width": "23%", "display": "inline-block", "marginRight": "1%"}),
                        html.Div([
                            html.Label("Morphology features"),
                            dcc.Dropdown(
                                id="morph-features",
                                options=[{"label": f, "value": f} for f in MORPH_FEATURES],
                                value=default_morph_features,
                                multi=True,
                            ),
                        ], style={"width": "100%", "display": "block", "marginTop": "10px"}),
                    ]),
                    dcc.Graph(id="morphology-distribution-graph"),
                    html.H3("Morphology statistics"),
                    dash_table.DataTable(
                        id="morphology-stats",
                        page_size=12,
                        sort_action="native",
                        filter_action="native",
                        style_table={"overflowX": "auto"},
                        style_cell={"fontSize": "12px", "padding": "6px"},
                    ),
                ]),
            ]),
        ]),
    ],
)


# =============================================================================
# Callbacks
# =============================================================================

@app.callback(
    Output("element-distribution-graph", "figure"),
    Output("element-distribution-stats", "data"),
    Output("element-distribution-stats", "columns"),
    Input("dist-particle-class", "value"),
    Input("dist-elements", "value"),
    Input("dist-plot-type", "value"),
    Input("dist-log-scale", "value"),
)
def update_element_distribution(particle_class, elements, plot_type, scale):
    d = filter_particle_class(DF_FULL, particle_class)
    fig = make_element_distribution_figure(
        d,
        elements or [],
        plot_type=plot_type,
        log_scale=(scale == "log"),
        title=f"Chemical element distribution — {particle_class}",
    )
    table_data, table_cols = make_stats_table(d, elements or [])
    return fig, table_data, table_cols


@app.callback(
    Output("eaf-distribution-graph", "figure"),
    Input("eaf-particle-class", "value"),
)
def update_eaf_distribution(particle_class):
    d = filter_particle_class(DF_FULL, particle_class)
    return make_element_distribution_figure(
        d,
        EAF_ELEMENTS,
        plot_type="Violin / raincloud",
        log_scale=True,
        title=f"EAF-relevant element distribution — {particle_class}",
    )


@app.callback(
    Output("eaf-condition-graph", "figure"),
    Output("eaf-condition-stats", "data"),
    Output("eaf-condition-stats", "columns"),
    Input("condition-particle-class", "value"),
    Input("condition-element", "value"),
    Input("condition-group-col", "value"),
)
def update_eaf_condition(particle_class, element, group_col):
    d = clean_good_condition_df(filter_particle_class(DF_FULL, particle_class))
    fig = make_eaf_condition_figure(
        DF_FULL,
        element=element,
        group_col=group_col,
        particle_class=particle_class,
        log_scale=True,
    )
    table_data, table_cols = make_stats_table(d, [element] if element else [], group_col=group_col)
    return fig, table_data, table_cols


@app.callback(
    Output("mass-vs-eaf-element-graph", "figure"),
    Input("scatter-particle-class", "value"),
    Input("scatter-element", "value"),
    Input("scatter-group-a", "value"),
    Input("scatter-group-b", "value"),
)
def update_mass_vs_eaf_element(particle_class, element, group_a, group_b):
    return make_mass_vs_eaf_element_comparison(
        DF_FULL,
        element=element,
        group_a=group_a,
        group_b=group_b,
        particle_class=particle_class,
        log_scale=True,
    )


@app.callback(
    Output("morphology-distribution-graph", "figure"),
    Output("morphology-stats", "data"),
    Output("morphology-stats", "columns"),
    Input("morph-particle-class", "value"),
    Input("morph-condition", "value"),
    Input("morph-features", "value"),
    Input("morph-histnorm", "value"),
)
def update_morphology_distribution(particle_class, condition, features, histnorm):
    fig = make_morphology_distribution_figure(
        particle_class=particle_class,
        condition=condition,
        features=features or [],
        histnorm=histnorm or "",
    )
    table_data, table_cols = make_morphology_stats_table(
        particle_class=particle_class,
        condition=condition,
        features=features or [],
    )
    return fig, table_data, table_cols


@app.callback(
    Output("composition-heatmap", "figure"),
    Output("composition-table", "data"),
    Output("composition-table", "columns"),
    Input("heatmap-particle-class", "value"),
    Input("heatmap-elements", "value"),
    Input("heatmap-mode", "value"),
)
def update_heatmap(particle_class, elements, mode):
    elements = elements or []
    fig = make_composition_heatmap(DF_FULL, elements, mode=mode, particle_class=particle_class)
    comp = aggregate_composition(DF_FULL, elements, mode=mode, particle_class=particle_class)

    index_name = comp.index.name or ZUSTAND_COL
    if index_name in comp.columns:
        comp = comp.drop(columns=[index_name])
    comp = comp.reset_index()
    table_data = comp.to_dict("records")
    table_cols = [{"name": c, "id": c} for c in comp.columns]
    return fig, table_data, table_cols


if __name__ == "__main__":
    app.run()

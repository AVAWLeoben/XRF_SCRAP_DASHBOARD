"""Shared, validated XRF processing and Plotly figures for Dash and Panel."""

def add_bdl_note(fig, df, elements):
    items = [f"{e}: {int(df[e].eq(0).sum())}" for e in elements]
    counts = '<br>'.join('; '.join(items[i:i+7]) for i in range(0, len(items), 7))
    fig.add_annotation(x=0, y=-0.20, xref="paper", yref="paper", showarrow=False,
                       xanchor="left", text="BDL zeros (not visible on log axes): " + counts,
                       font=dict(size=10))
    fig.update_layout(margin=dict(b=max(150, 80 + 16 * ((len(items)+6)//7))))
    return fig

from pathlib import Path
import os
import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
BASE_DIR = Path(__file__).resolve().parent
XLSX_PATH = BASE_DIR / 'data/Dashboard_Daten_20.05.26_NORMALIZED.xlsx'
MORPH_PATH = BASE_DIR / 'data/objektgroessen_von_fotos.xlsx'
SIGNAL_LABEL = 'Normalized XRF signal [a.u.]'
DATA_NOTE = 'XRF values have been divided by one undisclosed common positive constant. They are normalized signals, not absolute concentrations. Zeros denote below detection limit (BDL) and are retained as zero in statistics. Log axes cannot display zeros; statistical summaries still include them. Morphology is retained for reference; its values have not been validated.'
ID_COL = 'Objekt ID'
GUT_COL = 'Visible_Copper'
MAT_COL = 'Materialtype'
FARBE_COL = 'Colour'
ZUSTAND_COL = 'Condition'
GEWICHT_COL = 'Mass [g]'
GEWICHT_COL_ALT = 'Mass'
ELEMENT_COL = 'Cu'
EAF_ELEMENTS_DEFAULT = ['Fe', 'Co', 'Cu', 'Mo', 'Ni', 'Sn', 'W']
PLOT_TEMPLATE = 'plotly_white'
MAX_VISIBLE_POINTS_PER_ELEMENT = 250
ID_KEY_COL = '__object_id_key__'

def normalize_object_id(value):
    """Return a stable string key for object IDs across Excel sheets."""
    if pd.isna(value):
        return ''
    text = str(value).strip()
    if text == '':
        return ''
    try:
        number = float(text)
        if np.isfinite(number) and number.is_integer():
            return str(int(number))
    except Exception:
        pass
    return text
zustand_translation = {'Spule': 'Coil', 'Knäuel': 'Tangle', 'Geflecht': 'Mesh', 'Draht': 'Wire', 'Elektronik Komponente': 'Electronic Component', 'Einzelteil': 'Single Part', 'Schaumstoff': 'Foam', 'Kunststoffteil mit Schraube': 'Fastening', 'Cast': 'Cast', 'Feder': 'Spring', 'Massivteil leicht verformt': 'Ductile', 'Massivteil verformt': 'Ductile', 'Massivteil': 'Ductile', 'Gepresst': 'Ductile', 'Steinartig': 'Cast', 'Schraube': 'Nuts & Bolts', 'Beilagscheibe': 'Nuts & Bolts', 'Mutter': 'Nuts & Bolts', 'Plättchen': 'Sheet', 'Nuts & Bolts': 'Fastening'}
ELEMENT_SYMBOLS = set('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'.split())

def preprocess_chemistry(raw):
    """Validate without dropping observations, then apply ordered legacy rules.

    Existing zero signals are BDL. Missing/invalid data are rejected, never
    silently imputed. Source workbooks and numerical measurements stay intact.
    """
    df = raw.copy()
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    if df.columns.duplicated().any():
        raise ValueError('Duplicate column names after whitespace normalization')
    if GEWICHT_COL not in df and GEWICHT_COL_ALT in df:
        df[GEWICHT_COL] = df[GEWICHT_COL_ALT]
    required = [ID_COL, GEWICHT_COL, ELEMENT_COL, GUT_COL, ZUSTAND_COL]
    missing = [c for c in required if c not in df]
    if missing:
        raise ValueError(f'Missing columns: {missing}')
    df[ID_KEY_COL] = df[ID_COL].apply(normalize_object_id)
    if df[ID_KEY_COL].eq('').any() or df[ID_KEY_COL].duplicated().any():
        raise ValueError('Missing or duplicate object IDs')
    elements = sorted((c for c in df.columns if c in ELEMENT_SYMBOLS))
    for col in [GEWICHT_COL] + elements:
        values = pd.to_numeric(df[col], errors='coerce')
        invalid = ~np.isfinite(values) | (values < 0)
        if col == GEWICHT_COL:
            invalid |= values <= 0
        if invalid.any():
            ids = df.loc[invalid, ID_COL].tolist()[:10]
            raise ValueError(f'Invalid/missing {col} for objects {ids}; no automatic zero imputation')
        df[col] = values
    for col in [GUT_COL, ZUSTAND_COL]:
        if df[col].isna().any():
            raise ValueError(f'Missing {col}')
        df[col] = df[col].astype(str).str.strip()
    df[GUT_COL] = df[GUT_COL].replace({'Gutteil': 'Iron Particle', 'Schlechtteil': 'Copper Bearing Particle'})
    unknown = set(df[GUT_COL]) - {'Iron Particle', 'Copper Bearing Particle'}
    if unknown:
        raise ValueError(f'Unknown particle categories: {sorted(unknown)}')
    first_pass = {k: v for k, v in zustand_translation.items() if k != 'Nuts & Bolts'}
    df[ZUSTAND_COL] = df[ZUSTAND_COL].replace(first_pass)
    changes = []

    def apply_rule(name, mask, column, new):
        for index in df.index[mask & df[column].ne(new)]:
            changes.append({'Object ID': df.at[index, ID_COL], 'Rule': name, 'Column': column, 'Before': df.at[index, column], 'After': new})
        df.loc[mask, column] = new
    apply_rule('Iron coils to copper-bearing', (df[GUT_COL] == 'Iron Particle') & (df[ZUSTAND_COL] == 'Coil'), GUT_COL, 'Copper Bearing Particle')
    apply_rule('Copper-bearing springs to iron', (df[GUT_COL] == 'Copper Bearing Particle') & (df[ZUSTAND_COL] == 'Spring'), GUT_COL, 'Iron Particle')
    apply_rule('Copper-bearing nuts/bolts to iron', (df[GUT_COL] == 'Copper Bearing Particle') & (df[ZUSTAND_COL] == 'Nuts & Bolts'), GUT_COL, 'Iron Particle')
    apply_rule('Iron single parts to ductile', (df[GUT_COL] == 'Iron Particle') & (df[ZUSTAND_COL] == 'Single Part'), ZUSTAND_COL, 'Ductile')
    apply_rule('Iron plastic parts with screw to fastening', (df[GUT_COL] == 'Iron Particle') & (df[ZUSTAND_COL] == 'Plastic Part with Screw'), ZUSTAND_COL, 'Fastening')
    apply_rule('Iron object 3150 to cast', (df[GUT_COL] == 'Iron Particle') & (df[ID_KEY_COL] == '3150'), ZUSTAND_COL, 'Cast')
    apply_rule('Consolidate nuts/bolts to fastening', df[ZUSTAND_COL] == 'Nuts & Bolts', ZUSTAND_COL, 'Fastening')
    df.attrs['classification_changes'] = changes
    groups = [c for c in [GUT_COL, MAT_COL, FARBE_COL, ZUSTAND_COL] if c in df]
    return (df, elements, groups)

def load_and_preprocess_excel(path):
    return preprocess_chemistry(pd.read_excel(path))

def load_morphology_excel(path: str) -> tuple[pd.DataFrame, list[str]]:
    """Load optional morphology measurements for the morphology dashboard tab.

    The old dashboard used ``objektgroessen_von_fotos.xlsx`` and selected all
    columns after ``Objekt ID`` as morphology features. This loader is tolerant:
    if the workbook is missing, the rest of the dashboard still runs and the
    morphology tab shows a helpful message.
    """
    if not Path(path).exists():
        return (pd.DataFrame(), [])
    df_morph = pd.read_excel(path, engine='openpyxl', header=0).copy()
    df_morph = df_morph.dropna(axis=1, how='all')
    if ID_COL not in df_morph.columns:
        return (pd.DataFrame(), [])
    df_morph = df_morph.loc[~df_morph[ID_COL].isna() & (df_morph[ID_COL].astype(str).str.strip() != '')].copy()
    df_morph[ID_KEY_COL] = df_morph[ID_COL].apply(normalize_object_id)
    feature_cols = []
    for col in df_morph.columns:
        if col in {ID_COL, ID_KEY_COL} or not isinstance(col, str) or col.startswith('Unnamed') or (col in {'Objekt ID', '__object_id_key__'}):
            continue
        numeric = pd.to_numeric(df_morph[col], errors='coerce')
        if numeric.notna().any():
            df_morph[col] = numeric
            feature_cols.append(col)
    return (df_morph, feature_cols)

def weighted_mean(series, weights=None):
    clean = pd.to_numeric(series, errors='coerce').dropna()
    if clean.empty:
        return np.nan
    if weights is None:
        return clean.mean()
    w = pd.to_numeric(pd.Series(weights), errors='coerce').reindex(clean.index)
    valid = w.notna() & np.isfinite(w) & (w > 0)
    if not valid.any():
        return np.nan
    return np.average(clean.loc[valid], weights=w.loc[valid])

def weighted_median(series, weights=None):
    clean = pd.to_numeric(series, errors='coerce').dropna()
    if clean.empty:
        return np.nan
    if weights is None:
        return clean.median()
    w = pd.to_numeric(pd.Series(weights), errors='coerce').reindex(clean.index)
    valid = w.notna() & np.isfinite(w) & (w > 0)
    clean = clean.loc[valid]
    w = w.loc[valid]
    if clean.empty or w.empty or w.sum() <= 0:
        return np.nan
    sorter = np.argsort(clean.to_numpy())
    x = clean.to_numpy()[sorter]
    w = w.to_numpy()[sorter]
    cutoff = 0.5 * w.sum()
    return x[np.searchsorted(np.cumsum(w), cutoff, side='left')]

def compact_summary(df: pd.DataFrame, value_cols: list[str], group_col: str | None=None) -> pd.DataFrame:
    """Return compact statistics for display in the dashboard."""
    rows = []
    if group_col is None:
        iterator = [('All', df)]
    else:
        iterator = list(df.dropna(subset=[group_col]).groupby(group_col))
    for group_name, g in iterator:
        for col in value_cols:
            if col not in g.columns:
                continue
            values = pd.to_numeric(g[col], errors='coerce').dropna()
            weights = g.loc[values.index, GEWICHT_COL] if GEWICHT_COL in g.columns else None
            rows.append({'Group': group_name, 'Element': col, 'n': int(values.count()), 'BDL (zero)': int(values.eq(0).sum()), 'Min': values.min() if not values.empty else np.nan, 'Mean': values.mean() if not values.empty else np.nan, 'Weighted mean': weighted_mean(values, weights) if not values.empty else np.nan, 'Median': values.median() if not values.empty else np.nan, 'Weighted median': weighted_median(values, weights) if not values.empty else np.nan, 'Q1': values.quantile(0.25) if not values.empty else np.nan, 'Q3': values.quantile(0.75) if not values.empty else np.nan, 'Max': values.max() if not values.empty else np.nan})
    return pd.DataFrame(rows)
DF_FULL, CHEM_ELEMENTS, GROUP_COLS = load_and_preprocess_excel(XLSX_PATH)
EAF_ELEMENTS = [e for e in EAF_ELEMENTS_DEFAULT if e in CHEM_ELEMENTS]
DF_MORPH, MORPH_FEATURES = load_morphology_excel(MORPH_PATH)

def infer_good_particle_value(df):
    return 'Iron Particle' if 'Iron Particle' in set(df[GUT_COL]) else 'All particles'
GOOD_PARTICLE_VALUE = infer_good_particle_value(DF_FULL)

def filter_particle_class(df: pd.DataFrame, particle_class: str) -> pd.DataFrame:
    if particle_class == 'All particles' or GUT_COL not in df.columns or particle_class is None:
        return df.copy()
    return df[df[GUT_COL].astype(str) == str(particle_class)].copy()

def clean_good_condition_df(df):
    """Retain all conditions after explicit preprocessing; no hidden exclusions."""
    return df.copy()

def make_element_distribution_figure(df, elements, plot_type='Box', log_scale=True, title='Chemical element distribution'):
    if not elements:
        return go.Figure().update_layout(title='Select at least one element')
    elements = [e for e in elements if e in df.columns]
    if not elements:
        return go.Figure().update_layout(title='Selected elements are not available')
    data = df[[ID_COL] + elements].copy()
    long = data.melt(id_vars=[ID_COL], value_vars=elements, var_name='Element', value_name='Concentration')
    long['Concentration'] = pd.to_numeric(long['Concentration'], errors='coerce')
    long = long.dropna(subset=['Concentration'])
    if MAX_VISIBLE_POINTS_PER_ELEMENT is None:
        points = long.copy()
    else:
        points = pd.concat([g.sample(n=min(len(g), MAX_VISIBLE_POINTS_PER_ELEMENT), random_state=42) for _, g in long.groupby('Element', sort=False)], ignore_index=True) if not long.empty else long.copy()
    fig = go.Figure()
    for i, element in enumerate(elements):
        full_values = long.loc[long['Element'] == element, 'Concentration']
        sampled = points.loc[points['Element'] == element]
        if plot_type == 'Violin / raincloud':
            fig.add_trace(go.Violin(x=[element] * len(full_values), y=full_values, name=element, box_visible=True, meanline_visible=False, points=False, opacity=0.55, showlegend=False))
        else:
            fig.add_trace(go.Box(x=[element] * len(full_values), y=full_values, name=element, boxpoints=False, showlegend=False))
        if not sampled.empty:
            fig.add_trace(go.Scatter(x=sampled['Element'], y=sampled['Concentration'], mode='markers', marker=dict(size=4, opacity=0.45), customdata=sampled[[ID_COL]].to_numpy(), hovertemplate='<b>Object ID:</b> %{customdata[0]}<br><b>Element:</b> %{x}<br><b>Normalized signal:</b> %{y:.4g} a.u.<extra></extra>', name=f'{element} points', showlegend=False))
    fig.update_layout(template=PLOT_TEMPLATE, title=title, height=650, showlegend=False)
    if log_scale:
        fig.update_yaxes(type='log', title='Normalized XRF signal [a.u.] (log scale)')
    else:
        fig.update_yaxes(title='Normalized XRF signal [a.u.]')
    fig.update_xaxes(categoryorder='array', categoryarray=elements)
    if log_scale:
        add_bdl_note(fig, df, elements)
    return fig

def make_eaf_condition_figure(df, element='Cu', group_col=ZUSTAND_COL, particle_class='All particles', log_scale=True):
    """Interactive FIG13 equivalent: selected EAF element by condition/group."""
    if element not in df.columns:
        return go.Figure().update_layout(title=f'Missing element column: {element}')
    d = clean_good_condition_df(filter_particle_class(df, particle_class))
    if group_col not in d.columns:
        return go.Figure().update_layout(title=f'Missing group column: {group_col}')
    d = d.dropna(subset=[group_col, element]).copy()
    d[element] = pd.to_numeric(d[element], errors='coerce')
    d = d.dropna(subset=[element])
    if d.empty:
        return go.Figure().update_layout(title=f'No data available for {element} by {group_col}')
    order = sorted(d[group_col].astype(str).unique())
    fig = px.violin(d, x=group_col, y=element, color=group_col, box=True, points='all', category_orders={group_col: order}, hover_data=[ID_COL, GEWICHT_COL], template=PLOT_TEMPLATE, title=f'FIG13 equivalent — {element} distribution in {particle_class} by {group_col}')
    fig.update_traces(jitter=0.25, marker_size=5, opacity=0.75)
    median_value = d[element].median()
    fig.add_annotation(xref='paper', yref='paper', x=0.02, y=0.98, text=f'Median {element} overall: {median_value:.4g} a.u.', showarrow=False, bgcolor='white', bordercolor='lightgrey')
    fig.update_yaxes(type='log' if log_scale else 'linear', title=f'{element} normalized XRF signal [a.u.]' + (' (log scale)' if log_scale else ''))
    fig.update_layout(showlegend=False, height=650)
    if log_scale:
        add_bdl_note(fig, d, [element])
    return fig

def make_mass_vs_eaf_element_comparison(df, element='Cu', group_a='Cast', group_b='Ductile', particle_class='All particles', log_scale=True):
    """Interactive FIG14 equivalent: mass vs selected EAF element for two conditions."""
    if element not in df.columns:
        return go.Figure().update_layout(title=f'Missing element column: {element}')
    d = filter_particle_class(df, particle_class)
    d = d.dropna(subset=[ZUSTAND_COL, GEWICHT_COL, element]).copy()
    d[GEWICHT_COL] = pd.to_numeric(d[GEWICHT_COL], errors='coerce')
    d[element] = pd.to_numeric(d[element], errors='coerce')
    d = d.dropna(subset=[GEWICHT_COL, element])
    groups = [group_a, group_b]
    fig = make_subplots(rows=1, cols=2, subplot_titles=groups, shared_xaxes=True, shared_yaxes=True)
    for idx, group in enumerate(groups, start=1):
        g = d[d[ZUSTAND_COL] == group].copy()
        colors = '#1f77b4'
        fig.add_trace(go.Scatter(x=g[GEWICHT_COL], y=g[element], mode='markers', marker=dict(color=colors, size=8, line=dict(color='black', width=0.5), opacity=0.7), customdata=np.stack([g[ID_COL], g[ZUSTAND_COL]], axis=-1) if not g.empty else None, hovertemplate=f'<b>Object ID:</b> %{{customdata[0]}}<br><b>Condition:</b> %{{customdata[1]}}<br><b>Weight:</b> %{{x:.2f}} g<br><b>{element}:</b> ' + '%{y:.4g} a.u.<extra></extra>', name=group), row=1, col=idx)
        counts_text = f'Total particles: {len(g)}<br>Median {element}: {g[element].median():.4g} a.u.<br>' if len(g) else 'Total particles: 0<br>'
        fig.add_annotation(text=counts_text, xref=f"x{(idx if idx > 1 else '')} domain", yref=f"y{(idx if idx > 1 else '')} domain", x=0.98, y=0.98, showarrow=False, align='right', bgcolor='white', bordercolor='lightgrey')
    fig.update_xaxes(title='Weight [g]')
    fig.update_yaxes(title=f'{element} normalized XRF signal [a.u.]' + (' (log scale)' if log_scale else ''))
    if log_scale:
        fig.update_yaxes(type='log')
    fig.update_layout(title=f'FIG14 equivalent — {group_a} vs. {group_b}: individual {element} content ({particle_class})', template=PLOT_TEMPLATE, height=650, showlegend=False)
    if log_scale:
        add_bdl_note(fig, d[d[ZUSTAND_COL].isin(groups)], [element])
    return fig

def aggregate_composition(df, elements, mode='weighted_median', particle_class=GOOD_PARTICLE_VALUE):
    d = filter_particle_class(df, particle_class)
    d = d.dropna(subset=[ZUSTAND_COL]).copy()
    elements = [e for e in elements if e in d.columns]

    def aggregate_group(g):
        out = {}
        for element in elements:
            values = pd.to_numeric(g[element], errors='coerce').fillna(0)
            weights = g[GEWICHT_COL] if GEWICHT_COL in g.columns else None
            if mode == 'mean':
                out[element] = values.mean()
            elif mode == 'weighted_mean':
                out[element] = weighted_mean(values, weights)
            elif mode == 'median':
                out[element] = values.median()
            elif mode == 'weighted_median':
                out[element] = weighted_median(values, weights)
            else:
                out[element] = weighted_median(values, weights)
        return pd.Series(out)
    if d.empty or not elements:
        return pd.DataFrame(columns=elements).rename_axis(ZUSTAND_COL)
    composition = pd.DataFrame({name: aggregate_group(g) for name, g in d.groupby(ZUSTAND_COL)}).T
    composition = composition.loc[:, [e for e in elements if e in composition.columns]]
    if 'Cu' in composition.columns:
        composition = composition.sort_values('Cu', ascending=False)
    composition.index.name = ZUSTAND_COL
    return composition

def make_composition_heatmap(df, elements, mode='weighted_median', particle_class=GOOD_PARTICLE_VALUE):
    composition = aggregate_composition(df, elements, mode=mode, particle_class=particle_class)
    if composition.empty:
        return go.Figure().update_layout(title='No composition data available')
    fig = px.imshow(composition, text_auto='.4g', aspect='auto', color_continuous_scale='YlOrBr', template=PLOT_TEMPLATE, title=f"FIG12 — {mode.replace('_', ' ').title()} normalized XRF signal ({particle_class})", labels=dict(x='Element', y='Condition', color='a.u.'))
    fig.update_layout(height=max(500, 55 * len(composition.index)))
    return fig

def make_stats_table(df, elements, group_col=None):
    stats = compact_summary(df, elements, group_col=group_col)
    return (stats.to_dict('records'), [{'name': c, 'id': c} for c in stats.columns])

def get_filtered_morphology_df(particle_class='All particles', condition='All'):
    """Return morphology rows for the selected dashboard filters.

    The morphology workbook is already a valid standalone dataset. Therefore,
    the default view should show the complete morphology table and should not
    depend on a successful chemistry-table join. Chemistry filters are only
    applied when the user explicitly selects a particle subset or condition.
    """
    if DF_MORPH.empty or not MORPH_FEATURES:
        return pd.DataFrame()
    if particle_class in [None, 'All particles'] and condition in [None, 'All']:
        return DF_MORPH.copy()
    chem_subset = filter_particle_class(DF_FULL, particle_class)
    if condition != 'All' and ZUSTAND_COL in chem_subset.columns:
        chem_subset = chem_subset[chem_subset[ZUSTAND_COL].astype(str) == str(condition)]
    if ID_KEY_COL not in chem_subset.columns or ID_KEY_COL not in DF_MORPH.columns:
        return pd.DataFrame()
    valid_ids = set(chem_subset[ID_KEY_COL].dropna().astype(str))
    out = DF_MORPH[DF_MORPH[ID_KEY_COL].astype(str).isin(valid_ids)].copy()
    return out

def make_morphology_distribution_figure(particle_class, condition, features, histnorm=''):
    """Interactive morphology histogram grid, adapted from the old dashboard."""
    if DF_MORPH.empty or not MORPH_FEATURES:
        return go.Figure().update_layout(title=f'Morphology file not found or invalid: {MORPH_PATH}')
    features = [f for f in features or [] if f in MORPH_FEATURES]
    if not features:
        return go.Figure().update_layout(title='Select at least one morphology feature')
    d = get_filtered_morphology_df(particle_class=particle_class, condition=condition)
    if d.empty:
        chem_subset = filter_particle_class(DF_FULL, particle_class)
        if condition != 'All' and ZUSTAND_COL in chem_subset.columns:
            chem_subset = chem_subset[chem_subset[ZUSTAND_COL].astype(str) == str(condition)]
        return go.Figure().update_layout(title=f'No morphology data available for this filtered selection. Try Particle subset = All particles and Condition = All. (chemistry rows after filtering: {len(chem_subset)}, morphology rows loaded: {len(DF_MORPH)})')
    cols = 3
    rows = math.ceil(len(features) / cols)
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=features, shared_xaxes=False, shared_yaxes=False)
    for i, feature in enumerate(features):
        row = i // cols + 1
        col = i % cols + 1
        values = pd.to_numeric(d[feature], errors='coerce').dropna()
        fig.add_trace(go.Histogram(x=values, name=feature, histnorm=histnorm, marker_line_width=0.5, opacity=0.85), row=row, col=col)
    fig.update_layout(title=f'Morphological distributions — {particle_class}' + (f' / {condition}' if condition != 'All' else ''), template=PLOT_TEMPLATE, height=max(520, 320 * rows), showlegend=False, margin=dict(t=70, b=50, l=50, r=40))
    return fig

def make_morphology_stats_table(particle_class, condition, features):
    if DF_MORPH.empty or not MORPH_FEATURES:
        return ([], [])
    features = [f for f in features or [] if f in MORPH_FEATURES]
    d = get_filtered_morphology_df(particle_class=particle_class, condition=condition)
    rows = []
    for feature in features:
        values = pd.to_numeric(d[feature], errors='coerce').dropna()
        rows.append({'Feature': feature, 'n': int(values.count()), 'Min': values.min() if not values.empty else np.nan, 'Mean': values.mean() if not values.empty else np.nan, 'Median': values.median() if not values.empty else np.nan, 'Q1': values.quantile(0.25) if not values.empty else np.nan, 'Q3': values.quantile(0.75) if not values.empty else np.nan, 'Max': values.max() if not values.empty else np.nan})
    stats = pd.DataFrame(rows)
    return (stats.to_dict('records'), [{'name': c, 'id': c} for c in stats.columns])

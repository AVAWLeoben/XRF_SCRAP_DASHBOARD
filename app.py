"""Python-authored dashboard for local Panel and GitHub Pages/Pyodide."""
import panel as pn
import pandas as pd
import xrf_core as x

pn.extension('plotly', 'tabulator', sizing_mode='stretch_width')
particles = ['All particles'] + sorted(x.DF_FULL[x.GUT_COL].unique())
conditions = sorted(x.DF_FULL[x.ZUSTAND_COL].unique())

def select(name, options, value=None):
    return pn.widgets.Select(name=name, options=options, value=value or options[0], width=240)

def table(df):
    return pn.widgets.Tabulator(df, disabled=True, pagination='local', page_size=15,
                                show_index=False, header_filters=True, height=360)

def result(fig, df=None):
    children = [pn.pane.Plotly(fig, config={'responsive': True}, sizing_mode='stretch_width')]
    if df is not None:
        children += [pn.pane.Markdown('#### Statistics (normalized XRF signals; BDL counted as zero)'), table(df)]
    return pn.Column(*children)

def chemistry_view(particle, elements, kind, scale):
    d = x.filter_particle_class(x.DF_FULL, particle)
    fig = x.make_element_distribution_figure(d, elements, kind, scale == 'Log', f'Element distributions — {particle}')
    return result(fig, x.compact_summary(d, elements))

dist_particle = select('Particle subset', particles)
dist_elements = pn.widgets.MultiChoice(name='Elements', options=x.CHEM_ELEMENTS, value=x.EAF_ELEMENTS)
dist_kind = select('Plot type', ['Box', 'Violin / raincloud'])
dist_scale = select('Scale', ['Log', 'Linear'])
distribution = pn.Column(pn.Row(dist_particle, dist_kind, dist_scale), dist_elements,
    pn.bind(chemistry_view, dist_particle, dist_elements, dist_kind, dist_scale))

eaf_particle = select('Particle subset', particles)
eaf = pn.Column(eaf_particle, pn.bind(chemistry_view, eaf_particle, x.EAF_ELEMENTS, 'Violin / raincloud', 'Log'))

def condition_view(particle, element, group, scale):
    d = x.filter_particle_class(x.DF_FULL, particle)
    return result(x.make_eaf_condition_figure(x.DF_FULL, element, group, particle, scale == 'Log'),
                  x.compact_summary(d, [element], group))

cond_particle = select('Particle subset', particles, x.GOOD_PARTICLE_VALUE)
cond_element = select('EAF element', x.EAF_ELEMENTS, 'Cu')
cond_group = select('Group by', x.GROUP_COLS, x.ZUSTAND_COL)
cond_scale = select('Scale', ['Log', 'Linear'])
by_condition = pn.Column(pn.Row(cond_particle, cond_element, cond_group, cond_scale),
    pn.bind(condition_view, cond_particle, cond_element, cond_group, cond_scale))

mass_particle = select('Particle subset', particles)
mass_element = select('EAF element', x.EAF_ELEMENTS, 'Cu')
mass_a = select('Condition A', conditions, 'Cast')
mass_b = select('Condition B', conditions, 'Ductile')
mass_scale = select('Scale', ['Log', 'Linear'])
def mass_view(particle, element, a, b, scale):
    return result(x.make_mass_vs_eaf_element_comparison(x.DF_FULL, element, a, b, particle, scale == 'Log'))
mass = pn.Column(pn.Row(mass_particle, mass_element, mass_scale), pn.Row(mass_a, mass_b),
    pn.bind(mass_view, mass_particle, mass_element, mass_a, mass_b, mass_scale))

heat_particle = select('Particle subset', particles)
heat_mode = select('Aggregation', ['weighted_median', 'weighted_mean', 'median', 'mean'])
heat_elements = pn.widgets.MultiChoice(name='Elements', options=x.CHEM_ELEMENTS, value=x.EAF_ELEMENTS)
def heat_view(particle, elements, mode):
    comp = x.aggregate_composition(x.DF_FULL, elements, mode, particle).reset_index()
    return result(x.make_composition_heatmap(x.DF_FULL, elements, mode, particle), comp)
heatmap = pn.Column(pn.Row(heat_particle, heat_mode), heat_elements,
    pn.pane.Markdown('Weighted mean estimates a mass-weighted signal. Weighted median is a distribution statistic, not bulk composition.'),
    pn.bind(heat_view, heat_particle, heat_elements, heat_mode))

morph_particle = select('Particle subset', particles)
morph_condition = select('Condition', ['All'] + conditions)
morph_features = pn.widgets.MultiChoice(name='Features', options=x.MORPH_FEATURES, value=x.MORPH_FEATURES[:9])
morph_norm = pn.widgets.Select(name='Histogram normalization', options={
    'Absolute': '', 'Percent': 'percent', 'Probability': 'probability',
    'Density': 'density', 'Probability density': 'probability density'}, value='')
def morph_view(particle, condition, features, norm):
    d = x.get_filtered_morphology_df(particle, condition)
    records, _ = x.make_morphology_stats_table(particle, condition, features)
    return pn.Column(f'Morphology rows in selection: **{len(d):,}**',
        result(x.make_morphology_distribution_figure(particle, condition, features, norm)), table(pd.DataFrame(records)))
morphology = pn.Column(
    'Morphology values are retained unchanged and have not been validated. The default shows all morphology objects; chemistry filters use matching object IDs.',
    pn.Row(morph_particle, morph_condition, morph_norm), morph_features,
    pn.bind(morph_view, morph_particle, morph_condition, morph_features, morph_norm))

tabs = pn.Tabs(('Element distributions', distribution), ('EAF elements', eaf),
              ('EAF element by condition', by_condition), ('Mass vs EAF element', mass),
              ('Composition heatmap', heatmap), ('Morphology', morphology), dynamic=True)
dashboard = pn.Column(
    pn.pane.Markdown('# KIRAMET Waste Characterisation Dashboard\nInteractive XRF and morphology explorer'),
    pn.pane.Alert(x.DATA_NOTE, alert_type='info'),
    f'**{len(x.DF_FULL):,} XRF objects · {len(x.CHEM_ELEMENTS)} elements**. Classification rules applied; no conditions excluded.',
    tabs,
    max_width=1600, margin=20,
).servable(title='KIRAMET XRF Dashboard')

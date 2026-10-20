"""Python-authored dashboard for local Panel and GitHub Pages/Pyodide."""
import panel as pn
import pandas as pd
import xrf_core as x
import theme as t

pn.extension('plotly', 'tabulator', design='native', theme='dark',
             global_css=[t.GLOBAL_CSS], sizing_mode='stretch_width')
particles = ['All particles'] + sorted(x.DF_FULL[x.GUT_COL].unique())
conditions = sorted(x.DF_FULL[x.ZUSTAND_COL].unique())

def select(name, options, value=None):
    return pn.widgets.Select(name=name, options=options, value=value or options[0], width=220, height=70, sizing_mode='fixed',
                             stylesheets=[t.COMPONENT_CSS])

def table(df):
    return pn.widgets.Tabulator(df, disabled=True, pagination='local', page_size=15,
                                show_index=False, header_filters=True, height=360, theme='midnight',
                                stylesheets=[t.COMPONENT_CSS])

# Keep each chart pane alive across filter updates. Replacing entire panes can
# leave queued Plotly resize callbacks targeting a purged graph.
_result_views = {}

def result(fig, df=None, *, key, heading='Statistics (normalized XRF signals; BDL counted as zero)'):
    fig = t.style_figure(fig, x.CHEM_ELEMENTS + conditions + x.MORPH_FEATURES)
    if key not in _result_views:
        plot = pn.pane.Plotly(fig, config={'responsive': False}, sizing_mode='stretch_width')
        stats = table(df) if df is not None else None
        children = [plot]
        if stats is not None:
            children += [pn.pane.Markdown('#### ' + heading), stats]
        view = pn.Column(*children, styles=t.CARD, margin=(16, 0))
        _result_views[key] = (view, plot, stats)
    else:
        view, plot, stats = _result_views[key]
        plot.object = fig
        if stats is not None and df is not None:
            stats.value = df
    return _result_views[key][0]

def chemistry_view(particle, elements, kind, scale, key="distribution"):
    d = x.filter_particle_class(x.DF_FULL, particle)
    fig = x.make_element_distribution_figure(d, elements, kind, scale == 'Log', f'Element distributions — {particle}')
    return result(fig, x.compact_summary(d, elements), key=key)

dist_particle = select('Particle subset', particles)
dist_elements = pn.widgets.MultiChoice(name='Elements', options=x.CHEM_ELEMENTS, value=x.EAF_ELEMENTS, stylesheets=[t.COMPONENT_CSS])
dist_kind = select('Plot type', ['Box', 'Violin / raincloud'])
dist_scale = select('Scale', ['Log', 'Linear'])
distribution = pn.Column(pn.FlexBox(dist_particle, dist_kind, dist_scale), dist_elements,
    pn.bind(chemistry_view, dist_particle, dist_elements, dist_kind, dist_scale))

eaf_particle = select('Particle subset', particles)
eaf = pn.Column(eaf_particle, pn.bind(chemistry_view, eaf_particle, x.EAF_ELEMENTS, 'Violin / raincloud', 'Log', key='eaf'))

def condition_view(particle, element, group, scale):
    d = x.filter_particle_class(x.DF_FULL, particle)
    return result(x.make_eaf_condition_figure(x.DF_FULL, element, group, particle, scale == 'Log'),
                  x.compact_summary(d, [element], group), key="condition")

cond_particle = select('Particle subset', particles, x.GOOD_PARTICLE_VALUE)
cond_element = select('EAF element', x.EAF_ELEMENTS, 'Cu')
cond_group = select('Group by', x.GROUP_COLS, x.ZUSTAND_COL)
cond_scale = select('Scale', ['Log', 'Linear'])
by_condition = pn.Column(pn.FlexBox(cond_particle, cond_element, cond_group, cond_scale),
    pn.bind(condition_view, cond_particle, cond_element, cond_group, cond_scale))

mass_particle = select('Particle subset', particles)
mass_element = select('EAF element', x.EAF_ELEMENTS, 'Cu')
mass_a = select('Condition A', conditions, 'Cast')
mass_b = select('Condition B', conditions, 'Ductile')
mass_scale = select('Scale', ['Log', 'Linear'])
def mass_view(particle, element, a, b, scale):
    return result(x.make_mass_vs_eaf_element_comparison(x.DF_FULL, element, a, b, particle, scale == 'Log'), key='mass')
mass = pn.Column(pn.FlexBox(mass_particle, mass_element, mass_scale), pn.FlexBox(mass_a, mass_b),
    pn.bind(mass_view, mass_particle, mass_element, mass_a, mass_b, mass_scale))

heat_particle = select('Particle subset', particles)
heat_mode = select('Aggregation', ['weighted_median', 'weighted_mean', 'median', 'mean'])
heat_elements = pn.widgets.MultiChoice(name='Elements', options=x.CHEM_ELEMENTS, value=x.EAF_ELEMENTS, stylesheets=[t.COMPONENT_CSS])
def heat_view(particle, elements, mode):
    comp = x.aggregate_composition(x.DF_FULL, elements, mode, particle).reset_index()
    return result(x.make_composition_heatmap(x.DF_FULL, elements, mode, particle), comp, key="heatmap")
heatmap = pn.Column(pn.FlexBox(heat_particle, heat_mode), heat_elements,
    pn.pane.Markdown('Weighted mean estimates a mass-weighted signal. Weighted median is a distribution statistic, not bulk composition.'),
    pn.bind(heat_view, heat_particle, heat_elements, heat_mode))

morph_particle = select('Particle subset', particles)
morph_condition = select('Condition', ['All'] + conditions)
morph_features = pn.widgets.MultiChoice(name='Features', options=x.MORPH_FEATURES, value=x.MORPH_FEATURES[:9], stylesheets=[t.COMPONENT_CSS])
morph_norm = pn.widgets.Select(name='Histogram normalization', options={
    'Absolute': '', 'Percent': 'percent', 'Probability': 'probability',
    'Density': 'density', 'Probability density': 'probability density'}, value='', stylesheets=[t.COMPONENT_CSS])
def morph_view(particle, condition, features, norm):
    d = x.get_filtered_morphology_df(particle, condition)
    records, _ = x.make_morphology_stats_table(particle, condition, features)
    return result(x.make_morphology_distribution_figure(particle, condition, features, norm),
                  pd.DataFrame(records), key='morphology', heading='Morphology statistics')

morphology = pn.Column(
    'Morphology values are retained unchanged and have not been validated. The default shows all morphology objects; chemistry filters use matching object IDs.',
    pn.FlexBox(morph_particle, morph_condition, morph_norm), morph_features,
    pn.bind(morph_view, morph_particle, morph_condition, morph_features, morph_norm))

tabs = pn.Tabs(('Element distributions', distribution), ('EAF elements', eaf),
              ('EAF element by condition', by_condition), ('Mass vs EAF element', mass),
              ('Composition heatmap', heatmap), ('Morphology', morphology), dynamic=False,
              stylesheets=[t.COMPONENT_CSS])
header = pn.pane.HTML(f"""
<header class="header">
 <a class="brand" href="https://koinig.site/" aria-label="koinig.site home"><span class="mark">K</span>koinig.site</a>
 <a class="back" href="https://koinig.site/">← Back to koinig.site</a>
</header>
<section class="hero">
 <div class="eyebrow">KIRAMET · Material characterisation</div>
 <h1>XRF Scrap Analysis</h1>
 <p>Explore elemental signals, particle classes and material characteristics.</p>
 <div class="meta"><span><b>{len(x.DF_FULL):,}</b> XRF objects</span>
 <span><b>{len(x.CHEM_ELEMENTS)}</b> elements</span><span>Normalized signals</span></div>
</section>
""", stylesheets=[t.HEADER_CSS], margin=0)
data_note = pn.pane.Markdown('**About the data**  \n' + x.DATA_NOTE,
    styles={'background': '#111722', 'border': '1px solid #253247',
            'border-radius': '13px', 'padding': '14px 18px', 'color': '#93a4b8'},
    stylesheets=[t.COMPONENT_CSS], margin=(0, 0, 24, 0))
dashboard = pn.Column(
    header, data_note, tabs,
    pn.pane.HTML('<footer style="border-top:1px solid #253247;padding:24px 0;color:#93a4b8;font-size:12px">koinig.site · Independent browser tools and projects</footer>',
                 stylesheets=[t.COMPONENT_CSS]),
    max_width=1440, margin=(0, 16), align='center',
).servable(title='XRF Scrap Analysis · koinig.site')

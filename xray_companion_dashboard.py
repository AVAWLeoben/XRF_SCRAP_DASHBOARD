"""Corrected Dash entry point. Run: python xray_companion_dashboard.py"""
import dash
from dash import dcc, html, Input, Output, dash_table
from xrf_core import *

app = dash.Dash(__name__)
server = app.server
app.title = "XRF Scrap Dashboard"

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
                DATA_NOTE
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

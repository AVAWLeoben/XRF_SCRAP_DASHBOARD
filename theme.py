"""Presentation-only theme matching koinig.site. No scientific transformations."""
import plotly.graph_objects as go

BG = '#0a0d12'
PANEL = '#111722'
SURFACE = '#161e2b'
TEXT = '#f1f5f9'
MUTED = '#93a4b8'
BORDER = '#253247'
ACCENT = '#38bdf8'
FONT = 'Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif'
# Distinct categorical colours, separate from the site's brand accents.
PALETTE = ['#56b4e9', '#e69f00', '#009e73', '#cc79a7', '#f0e442',
           '#d55e00', '#9ac2ff', '#ffb5a7', '#b8de8c', '#c4a7e7',
           '#80cdc1', '#dfc27d', '#f781bf']

GLOBAL_CSS = '''
:root {color-scheme:dark; --design-primary-color:#38bdf8;}
html, body {margin:0; min-height:100%; background:#0a0d12; color:#f1f5f9;
 font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;}
body {background:radial-gradient(circle at 12% -5%,rgba(56,189,248,.16),transparent 33rem),
 radial-gradient(circle at 92% 8%,rgba(139,92,246,.12),transparent 28rem),#0a0d12;}
body.pn-loading {background-color:#0a0d12; color:#f1f5f9;}
.pn-loading-msg {color:#93a4b8;}
'''

COMPONENT_CSS = '''
:host {color:#f1f5f9; --design-primary-color:#38bdf8;
 font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;}
a {color:#38bdf8; text-decoration:none;}
a:focus-visible, button:focus-visible, select:focus-visible, input:focus-visible {
 outline:2px solid #38bdf8; outline-offset:3px;}
label, .bk-input-group label {color:#93a4b8; font-weight:600; font-size:12px;}
input, select, .bk-input, .choices__inner {background:#0d1420!important;
 color:#f1f5f9!important; border:1px solid #253247!important; border-radius:9px!important;}
.choices__list--dropdown, .choices__list[aria-expanded] {background:#161e2b!important; color:#f1f5f9!important;}
.choices__item--selectable.is-highlighted {background:#253247!important;}
.choices__list--multiple .choices__item {background:#253247!important; border-color:#3a506f!important; color:#f1f5f9!important;}
.bk-tabs-header {border-color:#253247; overflow-x:auto;}
.bk-tab {color:#93a4b8; padding:12px 16px; border-radius:9px 9px 0 0;}
.bk-tab.bk-active {background:#161e2b; color:#38bdf8; border-color:#253247;}
.bk-tab:hover {color:#f1f5f9; background:#161e2b;}
.tabulator {background:#111722!important; border-color:#253247!important; color:#f1f5f9; font-size:13px;}
.tabulator-header, .tabulator-col, .tabulator-footer {background:#161e2b!important; color:#93a4b8!important; border-color:#253247!important;}
.tabulator-row {background:#111722!important; color:#f1f5f9!important;}
.tabulator-row.tabulator-row-even {background:#141c29!important;}
.tabulator-row:hover {background:#1e2a3d!important;}
.tabulator-cell {border-color:#253247!important;}
.tabulator-page {background:#111722!important; color:#f1f5f9!important; border-color:#253247!important;}
.tabulator-page.active {color:#38bdf8!important;}
'''

HEADER_CSS = COMPONENT_CSS + '''
.header {display:flex;align-items:center;justify-content:space-between;gap:16px;
 padding:18px 0 26px;border-bottom:1px solid #253247;flex-wrap:wrap;}
.brand {display:flex;align-items:center;gap:11px;color:#f1f5f9;font-weight:800;letter-spacing:-.02em;}
.mark {width:34px;height:34px;border-radius:10px;display:grid;place-items:center;
 background:linear-gradient(135deg,#38bdf8,#8b5cf6);color:#06111b;font-weight:950;}
.back {color:#93a4b8;font-size:14px;padding:9px 12px;border-radius:9px;}
.back:hover {color:#f1f5f9;background:rgba(255,255,255,.055);}
.hero {padding:36px 0 24px;}
.eyebrow {color:#38bdf8;font-size:12px;font-weight:800;letter-spacing:.11em;text-transform:uppercase;}
h1 {font-size:clamp(28px,4vw,46px);letter-spacing:-.04em;line-height:1.1;margin:12px 0;}
p {color:#93a4b8;line-height:1.6;margin:0;}
.meta {display:flex;gap:10px;flex-wrap:wrap;margin-top:20px;}
.meta span {border:1px solid #253247;border-radius:999px;padding:7px 12px;font-size:12px;color:#93a4b8;}
.meta b {color:#f1f5f9;}
'''

CARD = {'background': 'linear-gradient(145deg,rgba(22,30,43,.92),rgba(13,18,27,.84))',
        'border': '1px solid #253247', 'border-radius': '20px',
        'padding': '16px', 'box-shadow': '0 10px 35px rgba(0,0,0,.16)'}

def style_figure(figure, categories):
    """Return a styled copy; coordinates, samples and statistics are untouched."""
    fig = go.Figure(figure)
    colors = {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(categories)}
    fig.update_layout(template='plotly_dark', paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font=dict(family=FONT, color=TEXT, size=12),
        colorway=PALETTE, title=dict(font=dict(size=17, color=TEXT)),
        hoverlabel=dict(bgcolor=SURFACE, font_color=TEXT, bordercolor=BORDER),
        legend=dict(bgcolor=PANEL, font_color=TEXT), autosize=True)
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER)
    for trace in fig.data:
        if trace.type == 'heatmap':
            # Perceptually ordered scale; branding does not encode magnitude.
            trace.colorscale = 'Viridis'
            continue
        name = (trace.name or '').removesuffix(' points')
        color = colors.get(name, PALETTE[0])
        if trace.type in ('box', 'violin'):
            trace.update(line_color=color, fillcolor=color, marker_color=color)
        elif trace.type in ('scatter', 'histogram'):
            trace.update(marker_color=color)
    if fig.layout.coloraxis:
        fig.update_coloraxes(colorscale='Viridis')
    for annotation in fig.layout.annotations or []:
        annotation.font.color = TEXT
        if annotation.bgcolor:
            annotation.bgcolor = SURFACE
            annotation.bordercolor = BORDER
    return fig

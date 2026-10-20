# KIRAMET XRF dashboard: Python to GitHub Pages

This package contains a corrected Dash version and a Panel/Pyodide port sharing
one scientific implementation in `xrf_core.py`. All six tabs are retained.
The original workbooks are included unchanged in `data/`.

## What changed

- Explicit mappings: Gutteil = Iron Particle; Schlechtteil = Copper Bearing Particle.
- Ordered legacy rules restored. No classifications change in the supplied workbook.
- All 62 formerly excluded objects are copper-bearing (59 Plastic Part with Screw,
  3 Single Part). The Iron Particle rules do not apply to them. They are now
  retained under their existing conditions in the condition view.
- Existing `Fastening` labels are not guessed to mean Nuts & Bolts. Only explicit
  Nuts & Bolts (or German screw/nut/washer labels) trigger that legacy class rule.
  The original code's early Nuts & Bolts consolidation is delayed until after
  that rule, so the rule can actually run for future source data.
- All 44 elements are selected by element symbol, including Be. Colour grouping
  accepts the actual column name after trimming whitespace.
- Normalized XRF units replace concentration labels. All Cu absolute thresholds
  and host-dependent threshold behavior are removed.
- Zeros are BDL and remain zero in statistics. Per-element BDL counts are shown
  in chemistry statistics and log-plot notes. Missing/invalid future entries fail
  validation instead of being silently mapped to zero or dropping the object.
- No rounding in scientific calculations. Weighted median uses the lower
  observation at an exact cumulative 50% boundary. Weighted means with no valid
  weights return NaN instead of silently becoming unweighted means.
- Sampling no longer depends on grouping columns surviving `groupby.apply`.
- No XRF measurement or mass value is changed. Morphology numerical data are
  unchanged and not scientifically validated. Its subset filters use the
  explicit chemistry categories; its default continues to show all morphology.

## Local use

Use Python 3.12 in a virtual environment:

```bash
python -m venv .venv
# Activate .venv using your operating system's normal command.
python -m pip install -r requirements.txt
python -m pytest -q
python audit.py
panel serve app.py --show
```

For the corrected Dash version:

```bash
python -m pip install -r requirements-dash.txt
python xray_companion_dashboard.py
```

For the browser build:

```bash
python build_site.py
python -m http.server 8000
```

Open `http://localhost:8000/dist/`. Do not open the HTML via `file://`.
The first visit downloads Pyodide and Python dependencies from CDNs. This is
not an offline bundle. No running Python server is needed after publication.

To run the live-browser smoke test:

```bash
python -m pip install playwright==1.55.0
python -m playwright install chromium
python browser_check.py
```

## GitHub Pages

1. Put this directory's **contents at the repository root**, including the hidden
   `.github/workflows/pages.yml` directory. Do not nest it inside another folder.
2. In repository Settings > Pages, choose **GitHub Actions** as the source.
3. Push to `main` (or change both `main` references in `pages.yml` to your branch).
4. The workflow validates the data, exports the audit, builds Panel, runs the
   live-browser check, uploads the static site, and deploys it to Pages.
5. The deployment URL appears in the Actions deployment output. Project paths
   work because resources use relative URLs.

Pull requests run build/validation but do not deploy. Each subsequent push to
main rebuilds the website. GitHub Pages must already be enabled for deployment.
The source XLSX files and packaged browser data are public on the deployed site;
only the supplied scaled chemistry is included, without a scaling factor.

## Editing

- `theme.py`: koinig.site colours, header, component styles and scientific chart palette.
  The Panel dashboard uses dark navy panels and a return link to koinig.site.
  Plotly categorical colours stay distinct from brand accents; heatmaps use Viridis.
  The legacy Dash interface retains its previous appearance.
- `app.py`: Panel layout, widgets and interactions.
  Chart panes persist across updates and tab changes to avoid queued resize
  callbacks targeting removed Plotly graphs. Panel owns responsive sizing.
- `xrf_core.py`: authoritative processing, statistics and figures for both apps.
- `data/*.xlsx`: replace with new source data, maintaining the documented schema.
- `xray_companion_dashboard.py`: legacy Dash interface.
- `audit.py`: detailed before/after report, including per-object changes.
- `tests/test_science.py`: population, numerical, rule and plot regression tests.

Changing a dataset intentionally may require updating snapshot counts in the
tests and browser check. Review the audit before updating those expectations.
The workflow fails on unexpected data changes rather than publishing silently.

Desktop dependency versions are pinned. Browser NumPy/pandas are provided by
the Pyodide distribution emitted by pinned Panel (currently Pyodide 0.29.3).
Other browser requirements are in `requirements-browser.txt`; the live test
records the actual pandas version and checks the reference Cu weighted mean.
The package is not a fully vendored dependency archive.

## Object photographs (lazy hover previews)

Keep the existing photos in `data/Object_Images/` in the repository. Filenames
must follow `BOX_OBJECTID.jpg`, e.g. `282_5422.jpg` is object 5422. JPG/JPEG,
PNG and WebP extensions are supported case-insensitively. Do not rename the folder.

Each build creates `dist/image-index.json` and copies photos into
`dist/data/Object_Images/`. Photos are not included in the Python resource ZIP
and are not downloaded at page startup. The small filename index is fetched
on the first sustained hover over a measurement; the corresponding image is
requested only for that hover. A 120 ms dwell avoids fetching during quick
pointer sweeps. Repeat visits use normal browser HTTP caching.

Preview cards appear next to the pointer for individual points in element
distributions, EAF distributions, the condition view, and mass scatter plots.
Box summaries, heatmap cells and morphology histogram bins do not identify one
object and therefore do not show a photo. Missing images show a fallback.
Decimal measurement IDs use their integer part for photo lookup only (1034.1
uses the 1034 photo); measurement IDs and XRF values remain unchanged.

Duplicate photo IDs stop the build with an explicit error. Unrecognized
filenames are listed in the generated index. An absent folder is supported,
but results in no available photos. Add or update photos and push to rebuild.

This preview is injected into the generated Pages HTML by `build_site.py`.
Use the static build/local HTTP preview to test it; the legacy Dash app and
`panel serve` do not include this browser script. Image files are published
alongside the site even though visitors only download them on demand.

## Audit results for supplied workbooks

- 4,731 XRF objects; 44 elements.
- 3,894 Iron Particle; 837 Copper Bearing Particle, unchanged after rules.
- Zero classification changes; no objects excluded from condition analysis.
- Overall and category mean/median/weighted mean unchanged; condition plots
  now also include the two previously excluded copper-bearing conditions.
- 5,412 morphology objects; 4,728 matching chemistry IDs.
- Chemistry-only IDs: 1034.1, 1148, 1152.1. Decimal IDs remain distinct.

Detailed output is in `artifacts/audit.json`, `classification_changes.csv`
(header only because no rules change these data), and
`statistics_before_after.csv`. Numerical values use the supplied arbitrary units.

See `VALIDATION.md` for checks performed and outstanding deployment checks.

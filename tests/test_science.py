"""Scientific invariants, edge cases and actual-workbook regression checks."""
import numpy as np
import pandas as pd
import pytest
import xrf_core as x

def test_measurements_and_population_are_preserved():
    raw = pd.read_excel(x.XLSX_PATH)
    assert len(x.DF_FULL) == len(raw) == 4731
    assert len(x.CHEM_ELEMENTS) == 44
    assert 'Be' in x.CHEM_ELEMENTS and 'Colour' in x.GROUP_COLS
    for col in x.CHEM_ELEMENTS + [x.GEWICHT_COL, x.ID_COL]:
        np.testing.assert_array_equal(x.DF_FULL[col], raw[col])
    assert len(x.clean_good_condition_df(x.DF_FULL)) == len(raw)

def test_ordered_classification_and_no_fastening_guess():
    raw = pd.DataFrame({x.ID_COL: [1, 2, 3, 4, 5, 3150, 7],
        x.GUT_COL: ['Gutteil', 'Schlechtteil', 'Schlechtteil', 'Gutteil', 'Gutteil', 'Gutteil', 'Schlechtteil'],
        x.ZUSTAND_COL: ['Coil', 'Spring', 'Nuts & Bolts', 'Single Part', 'Plastic Part with Screw', 'Ductile', 'Fastening'],
        x.GEWICHT_COL: [1.] * 7, 'Cu': [0.] * 7})
    d, _, _ = x.preprocess_chemistry(raw)
    assert d[x.GUT_COL].tolist() == ['Copper Bearing Particle', 'Iron Particle', 'Iron Particle',
        'Iron Particle', 'Iron Particle', 'Iron Particle', 'Copper Bearing Particle']
    assert d[x.ZUSTAND_COL].tolist() == ['Coil', 'Spring', 'Fastening', 'Ductile', 'Fastening', 'Cast', 'Fastening']
    assert x.infer_good_particle_value(d.iloc[::-1]) == 'Iron Particle'

def test_missing_not_silently_mapped_to_bdl():
    raw = pd.read_excel(x.XLSX_PATH).head(2)
    raw.loc[0, 'Cu'] = np.nan
    with pytest.raises(ValueError, match='Invalid/missing Cu'):
        x.preprocess_chemistry(raw)

def test_index_alignment_and_weighted_median_definition():
    values = pd.Series([1., 5., 9.], index=[10, 30, 20])
    weights = pd.Series([2., 1., 1.], index=[20, 10, 30])
    assert x.weighted_mean(values, weights) == 6
    # Lower weighted quantile at an exact cumulative half, documented convention.
    assert x.weighted_median(values, weights) == 5
    assert np.isnan(x.weighted_mean(values, weights * 0))

def test_all_group_statistics_against_independent_formulas():
    for particle in ['All particles', 'Iron Particle', 'Copper Bearing Particle']:
        d = x.filter_particle_class(x.DF_FULL, particle)
        comp = x.aggregate_composition(x.DF_FULL, x.CHEM_ELEMENTS, 'weighted_mean', particle)
        for name, g in d.groupby(x.ZUSTAND_COL):
            expected = (g[x.CHEM_ELEMENTS].to_numpy() * g[x.GEWICHT_COL].to_numpy()[:, None]).sum(axis=0) / g[x.GEWICHT_COL].sum()
            np.testing.assert_allclose(comp.loc[name], expected, rtol=1e-12, atol=1e-14)
    assert x.compact_summary(x.DF_FULL, ['Sn']).iloc[0]['BDL (zero)'] == 3923

def test_plots_keep_all_observations_in_statistical_layer():
    fig = x.make_element_distribution_figure(x.DF_FULL, ['Cu', 'Be'])
    assert len(fig.data[0].y) == 4731
    assert len(fig.data[1].y) == 250
    assert len(fig.data[2].y) == 4731
    assert all(v == 0 for v in fig.data[2].y)
    assert not fig.layout.shapes

def test_all_plot_builders_and_empty_selection():
    x.make_eaf_condition_figure(x.DF_FULL)
    x.make_mass_vs_eaf_element_comparison(x.DF_FULL)
    for mode in ['mean', 'median', 'weighted_mean', 'weighted_median']:
        x.make_composition_heatmap(x.DF_FULL, x.EAF_ELEMENTS, mode, 'All particles')
    x.make_element_distribution_figure(x.DF_FULL.iloc[:0], ['Cu'])
    assert x.aggregate_composition(x.DF_FULL, []).empty
    x.make_morphology_distribution_figure('All particles', 'All', x.MORPH_FEATURES[:2])

def test_morphology_measurements_unchanged():
    original = pd.read_excel(x.MORPH_PATH)
    pd.testing.assert_frame_equal(original, x.DF_MORPH[original.columns])

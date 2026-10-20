"""Produce auditable classification changes and before/after XRF statistics."""
from pathlib import Path
from collections import Counter
import json
import hashlib
import numpy as np
import pandas as pd
import xrf_core as x

def main():
    out = Path('artifacts')
    out.mkdir(exist_ok=True)
    raw = pd.read_excel(x.XLSX_PATH)
    clean = x.DF_FULL
    changes = pd.DataFrame(clean.attrs['classification_changes'],
        columns=['Object ID', 'Rule', 'Column', 'Before', 'After'])
    changes.to_csv(out / 'classification_changes.csv', index=False)
    rows = []
    for population in ['All particles', 'Iron Particle', 'Copper Bearing Particle']:
        before = x.filter_particle_class(raw, population)
        after = x.filter_particle_class(clean, population)
        for element in x.CHEM_ELEMENTS:
            for metric, fn in [('Mean', lambda d: d[element].mean()),
                               ('Median', lambda d: d[element].median()),
                               ('Weighted mean', lambda d: np.average(d[element], weights=d[x.GEWICHT_COL]))]:
                rows.append({'Population': population, 'Element': element, 'Metric': metric,
                             'Before n': len(before), 'After n': len(after),
                             'Before': float(fn(before)), 'After': float(fn(after))})
    pd.DataFrame(rows).to_csv(out / 'statistics_before_after.csv', index=False)
    c, m = set(clean[x.ID_KEY_COL]), set(x.DF_MORPH[x.ID_KEY_COL])
    report = {
        'chemistry_objects': len(clean), 'elements': len(x.CHEM_ELEMENTS),
        'particle_counts_before': raw[x.GUT_COL].value_counts().to_dict(),
        'particle_counts_after': clean[x.GUT_COL].value_counts().to_dict(),
        'rule_changes': dict(Counter(changes['Rule'])),
        'objects_changed': int(changes['Object ID'].nunique()),
        'old_condition_exclusions': int(raw[x.ZUSTAND_COL].isin(['Single Part', 'Plastic Part with Screw']).sum()),
        'new_condition_exclusions': 0,
        'original_exclusions_by_class': raw.loc[raw[x.ZUSTAND_COL].isin(['Single Part', 'Plastic Part with Screw'])].groupby([x.GUT_COL, x.ZUSTAND_COL]).size().to_string(),
        'measurements_bitwise_equal': all(np.array_equal(raw[col], clean[col]) for col in x.CHEM_ELEMENTS + [x.GEWICHT_COL]),
        'morphology_rows': len(x.DF_MORPH), 'matched_ids': len(c & m),
        'chemistry_only_ids': sorted(c-m), 'morphology_only_count': len(m-c),
        'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [x.XLSX_PATH, x.MORPH_PATH]},
        'pandas': pd.__version__, 'numpy': np.__version__,
    }
    (out / 'audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()

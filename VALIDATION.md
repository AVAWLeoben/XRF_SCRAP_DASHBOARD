# Current validation

The supplied normalized workbook is used unchanged. All source IDs, classes, conditions, chemical signals and masses are preserved. Audit CSVs compare source values to processed values; they do not claim the new source equals the previous workbook.

Verification covers weighted means against independent formulas, raw-space box quartiles before axis transformation, preserved raw hover values and object IDs, zero display, classifications, malformed input rejection, morphology preservation and image lookup behavior.

Local runtime: Python 3.12, pandas 3.1.0, NumPy 2.5.4, Plotly 6.3.0, Panel 1.9.4. Deployment dependencies retain the repository's existing pins. Local Python tests, JavaScript lazy-loading checks, audit and Panel static conversion were run. A live browser rendering check was not run locally; the existing GitHub workflow still requires it before deployment. Browser checks now compute their expected Cu mean from the supplied workbook instead of the old hardcoded mean.

Latest source: 5,097 objects (4,207 Iron Particle, 890 Copper Bearing Particle), 44 elements, 366 Cu zeros. Total count now matches the publication script. The particle-class counts differ by one from that script; current workbook labels are preserved. The supplied workbook is used byte-for-byte, without re-normalization or legacy reclassification.

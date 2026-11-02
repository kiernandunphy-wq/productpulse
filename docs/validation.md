# Verification record

Seven-day verification on November 2, 2026: **34 tests passed**, Ruff passed, BigQuery context and DuckDB session/daily reconciliation passed against 245,209 January 1?7 events. January 1 raw rows match the original baseline. See [seven-day findings](../reports/real_data_20210101_07.md).

Current live verification: the [November 2, 2026 run](../reports/real_data_20210101.md) passed BigQuery schema checks, extraction and real-data SQL/Python reconciliation; 27 tests and Ruff passed. The baseline below is historical.

This records the earlier project baseline. For current checkout-inclusive tests, authentication status and blockers, see [foundation_status.md](foundation_status.md).

Verified locally on Windows using an isolated uv-managed Python 3.12.16 environment. Exact installed dependency versions are in requirements-lock.txt (install that file, then `pip install --no-deps -e .` to reproduce the tested environment). The lock is a version snapshot, not a cross-platform hash lock.

- `python -m pytest -q`: final run **11 passed in 3.49 seconds**, including missing/malformed fields, missing identity, composite session keys, ordering/ties, empty denominators, zero/future retention cells, duplicate reporting, experiment reproducibility and end-to-end exports.
- Fixture CLI completed and wrote 8 analytical CSVs, provenance manifest, chart and calculated findings.
- Fixture: 16 event rows; 2 excluded from session metrics; 4 eligible sessions; ordered counts 4,4,2,2. Three sessions contain any purchase.
- Seed-42 experiment completed with 20,000 synthetic assignments and calculated statistical results.
- Both Jupyter notebooks executed successfully through nbclient with outputs saved.
- Databricks source notebook's embedded core ran locally and passed its fixture assertion. This does not verify Databricks import or serverless execution.
- Jupyter emitted Windows event-loop/kernel transport warnings; execution completed successfully.

Not verified: BigQuery SQL execution/schema audit, authentic GA4 export reconciliation, SQL/Python real-data parity, Databricks platform execution, Power BI Desktop import/DAX/rendering, GitHub Actions remote execution, GitHub publication, or portfolio deployment. No credentials were assumed and no cloud findings were fabricated.

Re-run commands are in README.md. Execute notebooks with `python scripts/verify_notebooks.py`. Regenerate notebook sources after changing core functions with `python scripts/build_notebooks.py`, then execute again. The generated Databricks source embeds the core at generation time.

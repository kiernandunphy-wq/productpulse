# ProductPulse

A portfolio project translating ecommerce business questions into validated SQL extracts, Python analytical tables, and decision support. It emphasizes analytical definitions, data quality, and statistical reasoning rather than a frontend.

**Current status:** January 1?7 real GA4 extraction and SQL/Python reconciliation passed: 245,209 window events, 22,847 distinct users, and an observed-entry ordered session funnel of 3,942 ? 743 ? 190 ? 91 (2.31%). Adjacent-date context prevents splitting midnight sessions. The January 1 baseline is preserved. See the [seven-day findings](reports/real_data_20210101_07.md), [multi-day workflow and Power BI data contract](docs/multiday.md), and [single-day report](reports/real_data_20210101.md). Dashboard and experiment work remains deferred.

## Windows + VS Code setup

Install Python 3.12 and VS Code with Python and Jupyter extensions. In the VS Code PowerShell terminal:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[bigquery,dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts databricks
.\.venv\Scripts\python.exe -m productpulse.foundation --input data/fixtures/foundation_events.csv --label fixture --output data/processed/foundation_demo
```

If using uv: `uv venv --python 3.12` then `uv pip install -e ".[bigquery,dev]"`. Select `.venv\Scripts\python.exe` as VS Code interpreter and notebook kernel. No activation or execution-policy change is required. Use a new output directory for every foundation run; existing results are protected. Base dependencies are in requirements.txt, optional cloud/test tools in pyproject.toml, and the tested environment snapshot in requirements-lock.txt.

For real GA4 input, follow the [single-day authenticated extraction workflow](docs/foundation.md), then:

```powershell
.\.venv\Scripts\python.exe -m productpulse.foundation --input data/raw/ga4/20210101/events.csv --label ga4 --output data/processed/ga4/20210101
.\.venv\Scripts\python.exe -m productpulse.validate_run --raw-dir data/raw/ga4/20210101 --analysis-dir data/processed/ga4/20210101
```

Do not label the fixture as GA4. The CLI label is a user-supplied declaration, not independent provenance verification.

## Review the analytical work

- [Business requirements and acceptance criteria](docs/analytics_requirements.md)
- [Data dictionary and metric contracts](docs/data_dictionary.md)
- [Architecture](docs/architecture.md)
- [Executive report and limitations](reports/executive_findings.md)
- [Power BI build guidance](powerbi/README.md)
- [Databricks import instructions](databricks/README.md)
- [Portfolio presentation](docs/portfolio.md)

SQL files are numbered by purpose. Notebooks provide local exploration and separate experimentation. Generated CSVs, manifest, chart, and calculated report live under `data/processed/fixture`; the independent simulated experiment is under `data/processed/experiment`. A schema failure stops processing. Missing user/session rows remain in event counts and user activity but are excluded from session metrics. Duplicates are counted and retained because identical projected rows are not proof of duplicate source events.

## Source and scope

Primary intended source: Google's [public GA4 ecommerce sample](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset), covering 2020-11-01 through 2021-01-31. It is obfuscated and includes placeholders and limited internal consistency. It cannot be reconciled against the GA demo account. [Export schema reference](https://support.google.com/analytics/answer/7029846).

The local CSV contract avoids cloud credentials and nested serialization dependencies. Product/item analysis stays in a separate SQL query to prevent item arrays inflating event counts. No revenue, AOV, profit, identity resolution, or causal traffic-source attribution is inferred from this minimal contract.

## Public release

Review `.gitignore`, keep credentials and raw exports private, and inspect generated files before committing. Source code is MIT licensed; Google's dataset remains subject to its provider terms. This repository does not redistribute a GA4 extract. Publish to GitHub yourself after reviewing the project; no remote repository or portfolio deployment has been created.


## Power BI dashboard preparation

The verified seven-day real-data analysis now has a validated local import package, field-level data dictionary, typed Power Query expressions, DAX definitions, and a three-page report design. **No .pbix has been created or verified.** Follow [Power BI Desktop setup](powerbi/desktop_setup.md), review the [report design](powerbi/report_design.md), and use the [portfolio summary](reports/portfolio_dashboard_summary.md). See the [exact deliverables](powerbi/deliverables.md).

```powershell
.\.venv\Scripts\python.exe -m productpulse.dashboard_export
.\.venv\Scripts\python.exe scripts/build_powerbi_contract.py
```

The current package is `powerbi/data/ga4_20210101_07/`; existing package directories are protected. For a repeat export, pass a fresh `--output` path and point the contract generator at it with `--package`. Real local source files are required; fixtures are rejected. No additional BigQuery queries are needed. Original analytical outputs remain unchanged.

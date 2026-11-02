# ProductPulse Power BI preparation

Use the **verified seven-day real GA4 package**. The repository's earlier four-stage examples use different fields and are not the current dashboard contract. The established checkout-inclusive funnel begins at product view, not page_view.

No `.pbix` was created or verified. This directory provides CSV preparation, implementation instructions and a report design. DAX, Power Query and visual interactions still require Power BI Desktop acceptance.

```powershell
.\.venv\Scripts\python.exe -m productpulse.dashboard_export
.\.venv\Scripts\python.exe scripts/build_powerbi_contract.py
```

The existing generated package is `data/ga4_20210101_07/` relative to this directory. Repeated export requires a new `--output` path. The exporter uses existing local real data, verifies raw provenance and source hashes, writes no cloud settings, and submits no BigQuery queries. The package remains Git-ignored; original single-day and seven-day outputs remain unchanged.

- [Desktop setup, imports, relationships, measures and acceptance](desktop_setup.md)
- [Field dictionary, actual types, table grains and aggregation rules](data_dictionary.md)
- [Source CSV schema audit](source_schema_audit.csv)
- [Three-page report and accessibility specification](report_design.md)
- [Separate DAX measure definitions](measures.dax)
- [Typed Power Query expressions](import_queries.pq)
- [Optional base theme](theme.json)
- [Exact deliverables and validation record](deliverables.md)
- [Portfolio summary and interview talking points](../reports/portfolio_dashboard_summary.md)

The full-window acceptance result is **245,209 events**, **22,847 unique users**, **26,331 active eligible sessions**, **26,328 entry-cohort sessions**, and ordered funnel **3,942 → 743 → 190 → 91 (2.31%)**. The package distinguishes calendar activity from observed-entry session outcomes. Static aggregates remain disconnected; interactive charts use the cohort fact and distinct-presence tables.

The original single-day and seven-day reports remain the analytical evidence. Proposed visuals do not imply the report has been opened or executed in Power BI Desktop.

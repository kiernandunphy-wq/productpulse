# Architecture

```mermaid
flowchart LR
    A[Public GA4 BigQuery shards] --> B[Schema audit + bounded SQL]
    B --> C[User-exported event CSV]
    C --> D[Python validation and quality manifest]
    F[Labeled synthetic fixture] --> D
    D --> E[Session model and ordered funnel]
    D --> R[Observed monthly cohorts]
    E --> T[BI CSVs + chart + calculated report]
    R --> T
    T --> P[Power BI manual build]
    X[Seeded independent experiment] --> S[Tests + CI + power + logistic model]
```

Local package separates cleaning, analytical models, experiment analysis and CLI orchestration. Notebooks reuse the package. Databricks source notebook embeds the fixture and pandas logic so cloud credentials and repository filesystem paths are unnecessary. It demonstrates the same workflow but is not a verified deployed integration. SQL handles nested source structure before local ingestion; item queries remain separate. Large extracts should be aggregated in the warehouse rather than loaded unbounded into pandas.

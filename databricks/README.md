# Databricks Free Edition

Import `productpulse_free_edition.py` through Workspace → Import as a Python source notebook, attach serverless notebook compute, and Run All. It embeds the same labeled synthetic fixture and core cleaning/funnel functions used locally, so no external credentials or sample catalog permissions are required. Outputs are temporary notebook dataframes and displays; no workspace tables or files are created automatically.

For authentic sample data, first run the BigQuery extraction process. Upload the resulting bounded CSV to a Unity Catalog volume available to your account. Replace the StringIO fixture cell with `raw = pd.read_csv('/Volumes/<catalog>/<schema>/<volume>/ga4_events.csv', dtype='string')` using your actual permitted path. Keep the export small enough for driver memory. Clearly change the displayed data label. Do not assume a shared sample catalog or legacy DBFS mount exists.

Free Edition uses serverless resources and has quotas; availability and environment libraries should be checked in your workspace. pandas is the only dependency in this demonstration. This notebook was generated and its functions were tested locally; Databricks import/run has not been verified.

Official references: [Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition), [limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).

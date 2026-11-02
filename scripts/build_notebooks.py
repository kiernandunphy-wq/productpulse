"""Generate reviewable notebooks and a self-contained Databricks source notebook."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]


def notebook(name, title, cells):
    nb = nbf.v4.new_notebook()
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.cells = [nbf.v4.new_markdown_cell(title)] + [nbf.v4.new_code_cell(c) for c in cells]
    path = ROOT / 'notebooks' / name
    path.parent.mkdir(exist_ok=True)
    nbf.write(nb, path)


notebook('01_ingestion_funnel.ipynb', '# ProductPulse: fixture workflow\nSynthetic fixture only. Change input and label together after a verified GA4 export.', [
    "from pathlib import Path\nimport pandas as pd\nfrom productpulse.pipeline import run\nroot = Path.cwd()\nif not (root / 'data').exists():\n    root = root.parent\noutput = root / 'data/processed/fixture'\nrun(root / 'data/fixtures/events.csv', output, 'fixture')",
    "pd.read_csv(output / 'funnel.csv')",
    "pd.read_csv(output / 'descriptive.csv')",
    "pd.read_csv(output / 'retention.csv')",
    "from IPython.display import Image, display\ndisplay(Image(filename=str(output / 'funnel.png')))"
])
notebook('02_simulated_experiment.ipynb', '# Independent simulated A/B experiment\nNo GA4 results. Seed 42; one assignment and binary outcome per synthetic user. Two-sided alpha .05; no peeking or multiple primary outcomes.', [
    "from productpulse.experiment import simulate, analyze\nexperiment = simulate(seed=42)\nexperiment.groupby('treatment').converted.agg(['count', 'sum', 'mean'])",
    "analyze(experiment)",
    "experiment.groupby(['treatment', 'mobile']).converted.mean().unstack().plot.bar(title='SIMULATED conversion by assignment/device')"
])

# Inline the tested core functions; no package installation or repo paths required in Databricks.
blocks = ["# Databricks notebook source\n# MAGIC %md\n# MAGIC # ProductPulse — SYNTHETIC fixture demonstration\n# MAGIC Import as a Python notebook and use serverless compute. No Google credentials required.\n# MAGIC Platform execution is not yet verified. Use a bounded authentic CSV to analyze GA4.\n",
          "import pandas as pd\nfrom io import StringIO\n"]
for module in ['cleaning.py', 'analytics.py']:
    blocks.append((ROOT / 'src/productpulse' / module).read_text(encoding='utf-8'))
fixture = (ROOT / 'data/fixtures/events.csv').read_text(encoding='utf-8')
blocks.append(f"raw = pd.read_csv(StringIO({fixture!r}), dtype='string')\nevents, quality = clean_events(raw)\nsessions = session_table(events)\nprint(quality)\ndisplay(funnel_table(sessions))\ndisplay(retention_table(events))\nassert funnel_table(sessions).sessions.tolist() == [4, 4, 2, 2]\n")
(ROOT / 'databricks/productpulse_free_edition.py').write_text('\n# COMMAND ----------\n'.join(blocks), encoding='utf-8')

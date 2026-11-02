"""Execute local notebooks and embedded Databricks core without claiming cloud validation."""
from pathlib import Path
import nbformat
from nbclient import NotebookClient

root = Path(__file__).resolve().parents[1]
for path in sorted((root / 'notebooks').glob('*.ipynb')):
    nb = nbformat.read(path, as_version=4)
    NotebookClient(nb, timeout=120, kernel_name='python3', resources={'metadata': {'path': str(root)}}).execute()
    nbformat.write(nb, path)
    print(f'Executed {path.name}')

source = root / 'databricks/productpulse_free_edition.py'
namespace = {'display': lambda value: None}
exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), namespace)
print('Databricks source fixture assertion passed locally (cloud not verified)')

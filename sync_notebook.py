import nbformat
import re
import sys

py_path = 'src/02_llm_integration.py'
nb_path = 'notebooks/02_llm_integration.ipynb'

try:
    with open(py_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split content by # Cell X
    cells = re.split(r'\n# Cell \d+:[^\n]*\n', content)

    nb = nbformat.v4.new_notebook()

    for i, cell_content in enumerate(cells):
        if not cell_content.strip():
            continue
        # Remove # In[X]: markers if any
        cell_content = re.sub(r'# In\[\d+\]:\n+', '', cell_content)
        # The first split might be the header before Cell 1
        if i == 0 and not cell_content.strip().startswith('import') and not 'get_ipython' in cell_content:
            # maybe skip or add as code cell
            continue
            
        nb.cells.append(nbformat.v4.new_code_cell(cell_content.strip()))

    with open(nb_path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)
    print('Notebook regenerated successfully at', nb_path)
except Exception as e:
    print('Error:', e)

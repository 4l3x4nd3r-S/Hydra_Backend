import json
import sys
import os

notebooks = [
    r"C:\Users\ALEXANDER_SUNI\Documents\ALEXANDERSUNI\DATA\datathon\cuadernos\m_1_prepare_data.ipynb",
    r"C:\Users\ALEXANDER_SUNI\Documents\ALEXANDERSUNI\DATA\datathon\cuadernos\m_2_build_panel_data.ipynb",
    r"C:\Users\ALEXANDER_SUNI\Documents\ALEXANDERSUNI\DATA\datathon\cuadernos\m_3_train_eval.ipynb"
]

for nb_path in notebooks:
    if not os.path.exists(nb_path):
        print(f"File not found: {nb_path}")
        continue
    
    print(f"\n{'='*80}\nNotebook: {os.path.basename(nb_path)}\n{'='*80}")
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
        for i, cell in enumerate(nb.get('cells', [])):
            if cell.get('cell_type') == 'code':
                source = "".join(cell.get('source', []))
                print(f"\n--- In [{cell.get('execution_count', ' ')}] ---")
                print(source)

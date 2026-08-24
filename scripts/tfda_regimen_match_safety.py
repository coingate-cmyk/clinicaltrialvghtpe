#!/usr/bin/env python3
"""Prevent a single-component TFDA licence from being presented as a whole combination regimen.

Curated NHI records sometimes put a true regimen in `drug` (e.g. "S-1 + gemcitabine").
Until component-wise label rendering is implemented, those records must not inherit the label
of only one component. Fixed-dose combination products can be explicitly allow-listed later.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / 'tools/nhi/assets'
TFDA_JS = ASSET_DIR / 'tfda-labels.js'

# True single-product combinations may be added here when verified by licence ingredient data.
FIXED_COMBINATION_IDS = set()


def load_tfda():
    src = TFDA_JS.read_text(encoding='utf-8')
    m = re.match(r'\s*window\.TFDA_LABELS\s*=\s*(\{[\s\S]*\});\s*$', src)
    if not m:
        raise SystemExit('Cannot parse TFDA_LABELS')
    return json.loads(m.group(1))


def curated_drugs():
    out = {}
    for path in sorted(ASSET_DIR.glob('data-*.js')):
        if path.name == 'data-core.js':
            continue
        src = path.read_text(encoding='utf-8')
        m = re.search(r'push\(\.\.\.(\[[\s\S]*\])\s*\);', src)
        if not m:
            continue
        try:
            rows = json.loads(m.group(1))
        except Exception:
            continue
        for row in rows:
            if isinstance(row, dict) and row.get('id'):
                out[str(row['id'])] = str(row.get('drug', ''))
    return out


def is_multi_product_regimen(drug: str) -> bool:
    # '+' is used in curated data for separately supplied regimen components.
    # Slash is NOT used here because several slash names are fixed combination products
    # (trifluridine/tipiracil, tegafur/gimeracil/oteracil).
    return '+' in str(drug or '')


def main():
    data = load_tfda()
    drugs = curated_drugs()
    changed = 0
    for item_id, entry in (data.get('byIndicationId') or {}).items():
        drug = drugs.get(item_id, entry.get('drug', '') if isinstance(entry, dict) else '')
        if item_id in FIXED_COMBINATION_IDS or not is_multi_product_regimen(drug):
            continue
        if not isinstance(entry, dict):
            continue
        entry.clear()
        entry.update({
            'status': 'regimen-components-required',
            'drug': drug,
            'note': 'Combination regimen requires component-wise TFDA label mapping; a single component licence is intentionally not shown as the whole regimen.'
        })
        changed += 1
    meta = data.setdefault('meta', {})
    meta['combination_regimen_withheld_count'] = changed
    TFDA_JS.write_text('window.TFDA_LABELS = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    print(json.dumps({'combination_regimen_withheld': changed}, ensure_ascii=False))


if __name__ == '__main__':
    main()

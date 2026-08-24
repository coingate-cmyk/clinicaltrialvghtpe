#!/usr/bin/env python3
"""Safety normalization for TFDA label mappings.

- Prevent a single-component licence from being presented as a whole '+' combination regimen.
- Normalize TFDA dataset-39 fields that concatenate multiple official PDF URLs with ';': keep
  all links in `label_urls`, while `label_url` is the first valid URL used by the UI.
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


def split_official_urls(value: str) -> list[str]:
    value = str(value or '').strip()
    if not value:
        return []
    parts = re.split(r';(?=https?://)', value)
    out = []
    for part in parts:
        part = part.strip()
        if part.startswith('https://mcp.fda.gov.tw/') or part.startswith('http://mcp.fda.gov.tw/'):
            if part not in out:
                out.append(part)
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
    normalized_links = 0
    for item_id, entry in (data.get('byIndicationId') or {}).items():
        if not isinstance(entry, dict):
            continue

        urls = split_official_urls(entry.get('label_url', ''))
        if urls:
            entry['label_urls'] = urls
            if entry.get('label_url') != urls[0]:
                entry['label_url'] = urls[0]
                normalized_links += 1

        drug = drugs.get(item_id, entry.get('drug', ''))
        if item_id in FIXED_COMBINATION_IDS or not is_multi_product_regimen(drug):
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
    meta['multi_insert_link_normalized_count'] = normalized_links
    TFDA_JS.write_text('window.TFDA_LABELS = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    print(json.dumps({'combination_regimen_withheld': changed, 'multi_insert_links_normalized': normalized_links}, ensure_ascii=False))


if __name__ == '__main__':
    main()

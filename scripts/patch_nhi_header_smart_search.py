#!/usr/bin/env python3
from pathlib import Path

js_path = Path('tools/nhi/assets/clinical-map.js')
html_path = Path('tools/nhi/index.html')
js = js_path.read_text(encoding='utf-8')
html = html_path.read_text(encoding='utf-8')

if 'function isDrugLikeQuery(q)' not in js:
    anchor = "  function directDrugHay(x) {\n    return norm([x.drug,x.regimen].join(' '));\n  }\n"
    insert = """  function isDrugLikeQuery(q) {
    const n = norm(q);
    if (!n || n.length < 3) return false;
    if (Object.keys(brandAliases).some(brand => brand === n || brand.startsWith(n) || n.startsWith(brand))) return true;
    if (officialBrandMatches(n).length) return true;
    return data.indications.some(x => {
      const d = norm(x.drug || '');
      return d && (d === n || d.includes(n) || n.includes(d));
    });
  }
  function routeHeaderSearchToDrug(q) {
    const value = String(q || '').trim();
    if (!isDrugLikeQuery(value)) return false;
    drugInput.value = value;
    if (document.body.dataset.lookupMode !== 'drug') setLookupMode('drug');
    else renderDrugLookup();
    return true;
  }
"""
    if anchor not in js:
        raise SystemExit('directDrugHay anchor not found')
    js = js.replace(anchor, insert + anchor, 1)

listener_anchor = "  drugInput.addEventListener('input', renderDrugLookup);\n"
listener = """  globalSearch?.addEventListener('input', e => {
    const q = e.target.value;
    if (routeHeaderSearchToDrug(q)) return;
  });
"""
if listener not in js:
    if listener_anchor not in js:
        raise SystemExit('drugInput listener anchor not found')
    js = js.replace(listener_anchor, listener_anchor + listener, 1)

html = html.replace('placeholder="搜尋 drug / regimen / biomarker…"', 'placeholder="搜尋藥名 / 商品名 / 癌種 / biomarker…"')

js_path.write_text(js, encoding='utf-8')
html_path.write_text(html, encoding='utf-8')
print('Smart header drug search patch applied')

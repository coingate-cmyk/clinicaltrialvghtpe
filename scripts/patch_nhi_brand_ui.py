#!/usr/bin/env python3
from pathlib import Path


def patch_once(path: Path, old: str, new: str, label: str):
    s = path.read_text(encoding='utf-8')
    if new in s:
        return False
    if old not in s:
        raise SystemExit(f'{label} anchor missing in {path}')
    path.write_text(s.replace(old, new, 1), encoding='utf-8')
    return True


# Load official brand index before the UI logic.
p = Path('tools/nhi/index.html')
patch_once(
    p,
    '  <script src="assets/candidates-ui.js"></script>\n  <script src="assets/clinical-map.js"></script>',
    '  <script src="assets/candidates-ui.js"></script>\n  <script src="assets/nhi-brand-aliases.js"></script>\n  <script src="assets/clinical-map.js"></script>',
    'brand script tag'
)

p = Path('tools/nhi/assets/clinical-map.js')
s = p.read_text(encoding='utf-8')

old = "  // -------- Drug-centric reimbursement lookup --------\n  const brandAliases = {"
new = """  // -------- Drug-centric reimbursement lookup --------
  const officialBrandIndex = window.NHI_BRAND_INDEX || {meta:{}, products:[]};
  const officialBrandProducts = Array.isArray(officialBrandIndex.products) ? officialBrandIndex.products : [];
  const brandAliases = {"""
if new not in s:
    if old not in s:
        raise SystemExit('brand index insertion anchor missing')
    s = s.replace(old, new, 1)

old_start = s.index('  function aliasExpansion(q) {')
old_end = s.index('\n  function directDrugHay(x) {', old_start)
replacement = r'''  const ingredientStopwords = new Set(['sodium','hydrochloride','hydrochloridehydrate','hydrate','monohydrate','dihydrate','anhydrous','maleate','dimaleate','mesylate','mesilate','acetate','citrate','phosphate','sulfate','succinate','tartrate','potassium','calcium','trihydrate']);
  function ingredientTerms(value='') {
    const n = norm(value);
    const tokens = n.match(/[a-z0-9][a-z0-9-]{3,}/g) || [];
    return unique([n, ...tokens.filter(t => !ingredientStopwords.has(t))]);
  }
  function productName(p) {
    return [p.brand_en, p.brand_zh].filter(Boolean).join(' / ');
  }
  function officialBrandMatches(q) {
    const n = norm(q);
    if (!n || n.length < 2) return [];
    return officialBrandProducts.filter(p => norm([p.brand_en,p.brand_zh].join(' ')).includes(n)).slice(0,120);
  }
  function aliasExpansion(q) {
    const n = norm(q);
    if (!n) return {terms:[], alias:null, products:[]};
    const terms = [n];
    const notices = [];
    for (const [brand,generic] of Object.entries(brandAliases)) {
      if (brand.includes(n) || n.includes(brand)) {
        terms.push(norm(generic));
        notices.push(`${brand} → ${generic}`);
      }
    }
    const products = officialBrandMatches(n);
    products.forEach(p => terms.push(...ingredientTerms(p.ingredient)));
    if (products.length) {
      const ingredients = unique(products.map(p=>p.ingredient)).slice(0,5);
      notices.push(`健保商品名 → ${ingredients.join(' / ')}`);
    }
    return {terms:unique(terms), alias:notices.length ? notices.join('；') : null, products};
  }
  function brandsForRecord(x) {
    if (!officialBrandProducts.length) return [];
    const hay = directDrugHay(x);
    const rows = officialBrandProducts.filter(p => ingredientTerms(p.ingredient).some(t => t.length >= 4 && hay.includes(t)));
    const seen = new Set();
    return rows.filter(p => {
      const name = productName(p);
      const k = norm(name);
      if (!name || seen.has(k)) return false;
      seen.add(k);
      return true;
    }).sort((a,b)=>productName(a).localeCompare(productName(b),'zh-Hant',{sensitivity:'base'}));
  }
  function brandListHtml(x) {
    const rows = brandsForRecord(x);
    if (!rows.length) return '';
    return `<details class="nhi-brand-list"><summary>健保收載商品名（含原廠 / 學名藥） <b>${rows.length}</b></summary><div class="nhi-brand-grid">${rows.map(p => `<div class="nhi-brand-item"><strong>${esc(productName(p))}</strong><span>${esc(p.company || p.manufacturer || '')}${p.code ? ` · ${esc(p.code)}` : ''}</span></div>`).join('')}</div></details>`;
  }'''
s = s[:old_start] + replacement + s[old_end:]

# Alias notice: make official NHI product matches visible, not just hand-curated originator aliases.
s = s.replace(
    "    if (alias) aliasNotice.textContent = `商品名別名：${alias}`;",
    "    if (alias) aliasNotice.textContent = `商品名 / 成分解析：${alias}`;"
)

# Add brand list underneath every reimbursement record in drug-centric results.
old = "<div class=\"badges\">${x.status && x.status !== '給付' ? `<span class=\"badge\">${esc(x.status)}</span>` : ''}${x.prior_auth ? '<span class=\"badge auth\">事前審查</span>' : ''}${bio}<span class=\"badge\">§ ${esc(x.section)}</span></div></div><div class=\"drug-hit-actions\">"
new = "<div class=\"badges\">${x.status && x.status !== '給付' ? `<span class=\"badge\">${esc(x.status)}</span>` : ''}${x.prior_auth ? '<span class=\"badge auth\">事前審查</span>' : ''}${bio}<span class=\"badge\">§ ${esc(x.section)}</span></div>${brandListHtml(x)}</div><div class=\"drug-hit-actions\">"
if new not in s:
    if old not in s:
        raise SystemExit('drug hit brand list anchor missing')
    s = s.replace(old, new, 1)

# The aliasExpansion destructuring already tolerates the extra products field; update explanatory text.
s = s.replace(
    '搜尋結果先列「此藥本身的給付」，再列「給付條件 / 摘要中提及此藥」；每個癌種與治療線別分開顯示。',
    '可輸入學名、原廠商品名或健保收載學名藥商品名。搜尋結果先列「此藥本身的給付」，再列「給付條件 / 摘要中提及此藥」；每個癌種與治療線別分開顯示。'
)
s = s.replace(
    '例如：nivolumab、bevacizumab、Keytruda、Tagrisso…',
    '例如：nivolumab、Keytruda、中文商品名、學名藥商品名…'
)

p.write_text(s, encoding='utf-8')

p = Path('tools/nhi/assets/clinical-map.css')
css = p.read_text(encoding='utf-8')
extra = r'''
/* NHI-listed brand-name index */
.nhi-brand-list{margin-top:9px;border-top:1px dashed var(--line);padding-top:8px}
.nhi-brand-list summary{cursor:pointer;color:var(--accent-2);font-size:11px;font-weight:750;list-style:none}
.nhi-brand-list summary::-webkit-details-marker{display:none}
.nhi-brand-list summary::before{content:'＋';display:inline-block;width:15px;color:var(--muted)}
.nhi-brand-list[open] summary::before{content:'－'}
.nhi-brand-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:6px;margin-top:8px}
.nhi-brand-item{padding:8px 9px;border:1px solid var(--line);border-radius:9px;background:#fbfcfc}
.nhi-brand-item strong{display:block;font-size:10px;line-height:1.35;color:var(--ink)}
.nhi-brand-item span{display:block;margin-top:3px;font-size:9px;line-height:1.3;color:var(--muted)}
'''
if '/* NHI-listed brand-name index */' not in css:
    css += extra
    p.write_text(css, encoding='utf-8')

print('NHI brand UI patch complete')

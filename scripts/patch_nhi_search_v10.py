from pathlib import Path
import re

# ---- clinical-map.js ----
p = Path('tools/nhi/assets/clinical-map.js')
s = p.read_text(encoding='utf-8')
s = s.replace('ALL CANCERS · V0.9 CLINICAL NAVIGATOR', 'ALL CANCERS · V1.0 REVIEW NAVIGATOR')
s = s.replace(
    '兩種查法並存：Cancer → setting → line → biomarker → reimbursed regimen；或直接用藥名反查所有健保適應症。所有癌種皆可使用臨床路徑視圖，完整條文仍隨時可切回。',
    '兩種查法並存：先依癌種看臨床路徑；或在癌種列表下方直接用藥名反查。藥物搜尋會把「此藥本身的給付」和「給付條件中提及此藥」分開呈現。'
)

old = "  changePanel.insertAdjacentElement('afterend', lookupBar);"
new = "  cancerBrowseSection.insertAdjacentElement('afterend', lookupBar);"
if old not in s:
    raise SystemExit('lookupBar insertion anchor missing')
s = s.replace(old, new, 1)

old = "  cancerBrowseSection.insertAdjacentElement('afterend', drugSection);"
new = "  lookupBar.insertAdjacentElement('afterend', drugSection);"
if old not in s:
    raise SystemExit('drugSection insertion anchor missing')
s = s.replace(old, new, 1)

s = s.replace(
    '<div class="section-heading drug-heading"><div><p class="eyebrow">SEARCH BY DRUG</p><h2>用藥名反查健保適應症</h2><p class="muted">可輸入 generic name；常用商品名亦支援別名轉換。結果會跨癌種列出 setting、line、biomarker、事審與 §9.x。</p></div><div id="drugLookupCount" class="result-count"></div></div>',
    '<div class="section-heading drug-heading"><div><p class="eyebrow">SEARCH BY DRUG</p><h2>用藥名反查健保適應症</h2><p class="muted">搜尋結果先列「此藥本身的給付」，再列「給付條件 / 摘要中提及此藥」；每個癌種與治療線別分開顯示。</p></div><div id="drugLookupCount" class="result-count"></div></div>'
)

old_dom = '''    <div id="drugAliasNotice" class="drug-alias-notice" hidden></div>
    <div id="drugDirectory" class="drug-directory"></div>
    <div id="drugLookupResults" class="drug-lookup-results"></div>`;'''
new_dom = '''    <div id="drugAliasNotice" class="drug-alias-notice" hidden></div>
    <div id="drugLookupResults" class="drug-lookup-results"></div>
    <div id="drugDirectory" class="drug-directory"></div>`;'''
if old_dom not in s:
    raise SystemExit('drug DOM order anchor missing')
s = s.replace(old_dom, new_dom, 1)

start = s.index('  function drugHay(x) {')
end = s.index('\n\n  function showDrugDetail', start)
replacement = r'''  function directDrugHay(x) {
    return norm([x.drug,x.regimen].join(' '));
  }
  function relatedDrugHay(x) {
    return norm([x.setting,x.line,lineGroup(x),x.biomarker,x.summary,x.review,x.duration,(x.tags||[]).join(' ')].join(' '));
  }
  function passesDrugFilters(x) {
    if (!includeDrugHints.checked && !isReimbursed(x)) return false;
    if (drugCancerFilter.value && x.cancer !== drugCancerFilter.value) return false;
    if (drugAuthFilter.value === 'yes' && !x.prior_auth) return false;
    if (drugAuthFilter.value === 'no' && x.prior_auth) return false;
    return true;
  }
  function drugMatchBuckets() {
    const {terms, alias} = aliasExpansion(drugInput.value);
    aliasNotice.hidden = !alias;
    if (alias) aliasNotice.textContent = `商品名別名：${alias}`;
    const eligible = data.indications.filter(passesDrugFilters);
    if (!terms.length) return {direct:eligible, related:[], terms, alias};
    const direct = eligible.filter(x => terms.some(t => directDrugHay(x).includes(t)));
    const directIds = new Set(direct.map(x => x.id));
    const related = eligible.filter(x => !directIds.has(x.id) && terms.some(t => relatedDrugHay(x).includes(t)));
    return {direct, related, terms, alias};
  }
  function groupByDrug(records) {
    const groups = new Map();
    records.forEach(x => {
      const key = x.drug || x.regimen || '未命名';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(x);
    });
    return [...groups.entries()].sort((a,b) => a[0].localeCompare(b[0],'en',{sensitivity:'base'}));
  }
  function groupByCancerAndLine(records) {
    const cancers = new Map();
    records.forEach(x => {
      const cancerName = cancerMap[x.cancer]?.name || x.cancer;
      if (!cancers.has(cancerName)) cancers.set(cancerName, new Map());
      const line = lineGroup(x) || x.line || '未指定線別';
      const lines = cancers.get(cancerName);
      if (!lines.has(line)) lines.set(line, []);
      lines.get(line).push(x);
    });
    return [...cancers.entries()]
      .sort((a,b)=>a[0].localeCompare(b[0],'zh-Hant'))
      .map(([cancer,lines]) => [cancer,[...lines.entries()].sort((a,b)=>a[0].localeCompare(b[0],'zh-Hant',{numeric:true}))]);
  }
  function drugHitHtml(x) {
    const bio = x.biomarker && x.biomarker !== '—' ? `<span class="badge bio">${esc(x.biomarker)}</span>` : '';
    return `<article class="drug-hit"><div class="drug-hit-main"><h4>${esc(x.drug)}</h4><div class="regimen">${esc(x.regimen)}</div><p>${esc(x.setting)}</p><div class="badges">${x.status && x.status !== '給付' ? `<span class="badge">${esc(x.status)}</span>` : ''}${x.prior_auth ? '<span class="badge auth">事前審查</span>' : ''}${bio}<span class="badge">§ ${esc(x.section)}</span></div></div><div class="drug-hit-actions"><button type="button" class="action-button primary" data-drug-detail="${esc(x.id)}">摘要</button><a class="action-button" href="${esc(pdfLink(x))}" target="_blank" rel="noopener">官方 PDF ↗</a></div></article>`;
  }
  function groupedDrugResultsHtml(records) {
    return groupByCancerAndLine(records).map(([cancer,lines]) => `<section class="drug-cancer-group"><div class="drug-cancer-head"><h3>${esc(cancer)}</h3><span>${lines.reduce((n,[,rows])=>n+rows.length,0)} 筆</span></div>${lines.map(([line,rows]) => `<div class="drug-line-group"><div class="drug-line-head"><strong>${esc(line)}</strong><span>${rows.length} 個給付情境</span></div><div class="drug-group-list">${rows.map(drugHitHtml).join('')}</div></div>`).join('')}</section>`).join('');
  }
  function renderDrugDirectory() {
    if (drugInput.value.trim()) { drugDirectory.hidden = true; return; }
    const active = data.indications.filter(isReimbursed);
    const groups = groupByDrug(active);
    drugDirectory.hidden = false;
    drugDirectory.innerHTML = `<div class="drug-directory-head"><strong>${groups.length} 個藥物 / 組合名稱</strong><span>常用藥物索引；點一下即可帶入上方搜尋</span></div><div class="drug-chip-grid">${groups.map(([name,rows]) => `<button type="button" data-drug-chip="${esc(name)}"><strong>${esc(name)}</strong><span>${rows.length} 筆</span></button>`).join('')}</div>`;
  }
  function renderDrugLookup() {
    const {direct, related} = drugMatchBuckets();
    const directActive = direct.filter(isReimbursed).length;
    drugCount.innerHTML = `<b>${directActive}</b><span> 直接給付情境</span>`;
    renderDrugDirectory();
    if (!drugInput.value.trim()) {
      drugResults.innerHTML = '<div class="drug-lookup-empty">輸入藥名。結果會緊接在搜尋框下方，並將「此藥本身」與「條件中提及此藥」分開。</div>';
      return;
    }
    const directHtml = direct.length
      ? `<section class="drug-match-section direct"><div class="drug-match-head"><div><p class="eyebrow">DIRECT INDICATIONS</p><h3>此藥本身的健保給付</h3></div><span>${direct.length} 筆</span></div>${groupedDrugResultsHtml(direct)}</section>`
      : '<section class="drug-match-section direct"><div class="drug-lookup-empty"><strong>沒有找到此藥本身的 curated 給付 record</strong><span>仍可查看下方是否有其他藥物的給付條件提到這個藥。</span></div></section>';
    const relatedHtml = related.length
      ? `<section class="drug-match-section related"><div class="drug-match-head"><div><p class="eyebrow">CLAUSE / CONDITION MENTIONS</p><h3>給付條件或摘要中提及此藥</h3><p>這些結果的「被申請藥」不是搜尋的藥；例如前線使用、治療失敗或互斥條件中提到它。</p></div><span>${related.length} 筆</span></div>${groupedDrugResultsHtml(related)}</section>`
      : '';
    drugResults.innerHTML = directHtml + relatedHtml;
  }'''
s = s[:start] + replacement + s[end:]

old = '''      cancerBrowseSection.hidden = true;
      resultsSection.hidden = true;
      drugSection.hidden = false;
      renderDrugLookup();
      setTimeout(() => drugInput.focus({preventScroll:true}), 0);'''
new = '''      cancerBrowseSection.hidden = false;
      resultsSection.hidden = true;
      drugSection.hidden = false;
      renderDrugLookup();
      setTimeout(() => { drugSection.scrollIntoView({behavior:'smooth',block:'start'}); drugInput.focus({preventScroll:true}); }, 0);'''
if old not in s:
    raise SystemExit('drug mode layout anchor missing')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# ---- split afatinib lung indications ----
p = Path('tools/nhi/assets/data-lung-support.js')
s = p.read_text(encoding='utf-8')
pat = re.compile(r'\{"id":"lc-afatinib".*?\},\n(?=\{"id":"lc-ts1")', re.S)
m = pat.search(s)
if not m:
    raise SystemExit('lc-afatinib combined record not found')
repl = '''{"id":"lc-afatinib-egfr-1l","cancer":"lung","drug":"Afatinib","regimen":"Afatinib monotherapy","setting":"EGFR-mutated 局部晚期 / 轉移性肺腺癌","line":"第一線","biomarker":"EGFR-TK mutation","prior_auth":false,"review":"每8–12週療效評估；與其他第一線 EGFR TKI / 指定組合依條文擇一","duration":"至惡化/不耐受","section":"9.45","pdf_page":30,"effective":"115/8/1","status":"給付","summary":"肺腺癌：EGFR-TK mutation 的局部晚期或轉移性肺腺癌，可使用 afatinib 第一線。第一線 EGFR 標靶的互斥與更換限制依第9.45節。","tags":["lung","NSCLC","adenocarcinoma","EGFR","afatinib","first-line"],"line_group":"1L"},
{"id":"lc-afatinib-sq-2l","cancer":"lung","drug":"Afatinib","regimen":"Afatinib monotherapy","setting":"含鉑化療後惡化之鱗狀 NSCLC","line":"第二線","biomarker":"—","prior_auth":false,"review":"需符合第9.45節含鉑治療後惡化之條件","duration":"至惡化/不耐受","section":"9.45","pdf_page":30,"effective":"115/8/1","status":"給付","summary":"肺癌：鱗狀非小細胞肺癌於含鉑化療治療後惡化，可使用 afatinib 第二線；此情境與 EGFR-mutated 肺腺癌第一線分開呈現。","tags":["lung","NSCLC","squamous","afatinib","second-line","post-platinum"],"line_group":"2L"},
'''
s = s[:m.start()] + repl + s[m.end():]
p.write_text(s, encoding='utf-8')

# ---- CSS ----
p = Path('tools/nhi/assets/clinical-map.css')
css = p.read_text(encoding='utf-8')
extra = '''
/* v1.0 review-oriented drug lookup */
.drug-directory[hidden],.drug-lookup-section[hidden],.clinical-view-toolbar[hidden],.clinical-map-panel[hidden]{display:none!important}
.lookup-mode-bar{scroll-margin-top:92px}
.drug-lookup-section{scroll-margin-top:92px}
.drug-match-section{margin:14px 0 22px}
.drug-match-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;padding:14px 16px;background:#f7faf9;border:1px solid var(--line);border-radius:14px;margin-bottom:10px}
.drug-match-head h3{margin:0;font-size:20px}.drug-match-head p{margin:4px 0 0;color:var(--muted);font-size:12px;max-width:760px}.drug-match-head>span{font-size:12px;color:var(--muted);white-space:nowrap}
.drug-match-section.related .drug-match-head{background:#fff8e8;border-color:#ead9a9}.drug-match-section.related .drug-match-head .eyebrow{color:#8a5a08}
.drug-cancer-group{border:1px solid var(--line);background:#fff;border-radius:15px;margin:10px 0;overflow:hidden}.drug-cancer-head{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:12px 15px;background:#f4f7f7;border-bottom:1px solid var(--line)}.drug-cancer-head h3{margin:0;font-size:17px}.drug-cancer-head span{font-size:11px;color:var(--muted)}
.drug-line-group{padding:13px 15px}.drug-line-group+.drug-line-group{border-top:1px solid var(--line)}.drug-line-head{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px}.drug-line-head strong{font-size:13px;color:var(--accent-2)}.drug-line-head span{font-size:10px;color:var(--muted)}
.drug-directory{margin-top:24px;padding-top:20px;border-top:1px dashed var(--line)}
@media(max-width:610px){.drug-match-head,.drug-line-head{align-items:flex-start;flex-direction:column}.drug-cancer-head{align-items:flex-start}}
'''
if 'v1.0 review-oriented drug lookup' not in css:
    p.write_text(css + extra, encoding='utf-8')

print('Patch complete')

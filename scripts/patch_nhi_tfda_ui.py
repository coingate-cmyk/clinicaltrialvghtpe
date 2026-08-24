#!/usr/bin/env python3
"""Idempotently add TFDA label/dose enrichment to the NHI Navigator UI."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'tools/nhi/assets/app.js'
INDEX = ROOT / 'tools/nhi/index.html'
CSS = ROOT / 'tools/nhi/assets/style.css'

app = APP.read_text(encoding='utf-8')

if 'const tfda = window.TFDA_LABELS' not in app:
    anchor = "  const changes = window.NHI_CHANGES || { status: 'not-run', changes: [] };\n"
    insert = anchor + "  const tfda = window.TFDA_LABELS || { meta: {}, byIndicationId: {} };\n  const tfdaFor = (item) => (tfda.byIndicationId || {})[item?.id] || null;\n  const tfdaVisible = (item) => { const t=tfdaFor(item); return t && (t.status === 'matched' || t.status === 'generic-label'); };\n  const tfdaSearchText = (item) => { const t=tfdaFor(item); return t ? [t.product_zh,t.product_en,t.permit,t.dosage,...(t.dose_mentions||[]),...(t.frequency_mentions||[])].filter(Boolean).join(' ') : ''; };\n"
    if anchor not in app:
        raise SystemExit('Cannot find app TFDA insertion anchor')
    app = app.replace(anchor, insert, 1)

old_hay = "        const hay = normalize([x.drug,x.regimen,x.setting,x.line,lineGroup(x),x.biomarker,x.summary,x.section,...(x.tags||[]),cancerMap[x.cancer]?.name].join(' '));"
new_hay = "        const hay = normalize([x.drug,x.regimen,x.setting,x.line,lineGroup(x),x.biomarker,x.summary,x.section,...(x.tags||[]),cancerMap[x.cancer]?.name,tfdaSearchText(x)].join(' '));"
if old_hay in app:
    app = app.replace(old_hay, new_hay, 1)
elif new_hay not in app:
    raise SystemExit('Cannot locate NHI search haystack')

card_re = re.compile(r"  function cardHtml\(x\) \{[\s\S]*?\n  \}\n\n  function renderFilterChips\(\)", re.M)
new_card = r'''  function cardHtml(x) {
    const bio = x.biomarker && x.biomarker !== '—';
    const t = tfdaFor(x);
    const showTfda = tfdaVisible(x);
    const doseChip = showTfda && (t.dose_mentions || []).length ? (t.dose_mentions || []).slice(0,3).join(' / ') : '';
    const freqChip = showTfda && (t.frequency_mentions || []).length ? (t.frequency_mentions || []).slice(0,3).join(' / ') : '';
    const tfdaMeta = showTfda ? `<div class="tfda-card-dose"><small>TFDA 核准仿單</small><span>${esc(doseChip || '用法用量詳見仿單')}${freqChip ? ` · ${esc(freqChip)}` : ''}</span></div>` : '';
    return `<article class="drug-card">
      <div>
        <h3>${esc(x.drug)}</h3>
        <div class="regimen">${esc(x.regimen)}</div>
        <div class="badges">
          <span class="badge">${esc(lineGroup(x))}</span>
          ${x.status && x.status !== '給付' ? `<span class="badge">${esc(x.status)}</span>` : ''}
          ${x.prior_auth ? '<span class="badge auth">事前審查</span>' : ''}
          ${bio ? `<span class="badge bio">${esc(x.biomarker)}</span>` : ''}
          ${showTfda ? '<span class="badge tfda">TFDA dose</span>' : ''}
          <span class="badge">§ ${esc(x.section)}</span>
        </div>
        ${tfdaMeta}
      </div>
      <div class="meta-grid">
        <div class="meta-item"><small>Setting</small><span>${esc(x.setting)}</span></div>
        <div class="meta-item"><small>Biomarker</small><span>${esc(x.biomarker)}</span></div>
        <div class="meta-item"><small>Review</small><span>${esc(x.review)}</span></div>
        <div class="meta-item"><small>Duration</small><span>${esc(x.duration)}</span></div>
      </div>
      <div class="card-actions">
        <button class="action-button primary" data-detail="${esc(x.id)}">摘要 / 劑量</button>
        <a class="action-button" href="${esc(pdfLink(x))}" target="_blank" rel="noopener">健保 PDF ↗</a>
        ${showTfda && t.label_url ? `<a class="action-button tfda-link" href="${esc(t.label_url)}" target="_blank" rel="noopener">TFDA 仿單 ↗</a>` : ''}
      </div>
    </article>`;
  }

  function renderFilterChips()'''
if not card_re.search(app):
    if 'class="tfda-card-dose"' not in app:
        raise SystemExit('Cannot locate cardHtml block')
else:
    app = card_re.sub(new_card, app, count=1)

show_re = re.compile(r"  function showDetail\(id\) \{[\s\S]*?\n  \}\n\n  function showChangesDialog\(\)", re.M)
new_show = r'''  function showDetail(id) {
    const x = data.indications.find(i => i.id === id);
    if (!x) return;
    const c = cancerMap[x.cancer];
    const t = tfdaFor(x);
    const showTfda = tfdaVisible(x);
    const tfdaDate = tfda.meta?.fetched_at ? String(tfda.meta.fetched_at).slice(0,10) : '';
    const tfdaPanel = showTfda ? `<section class="source-panel tfda-panel">
      <div class="source-panel-head"><div><small>TFDA 核准仿單</small><strong>${esc(t.product_zh || t.product_en || x.drug)}</strong></div><span>${esc(t.match_basis || '')}</span></div>
      <dl class="detail-table compact-table">
        <dt>許可證</dt><dd>${esc(t.permit || '')}</dd>
        <dt>核准適應症</dt><dd>${esc(t.indication || '—')}</dd>
        <dt>劑量</dt><dd>${esc((t.dose_mentions || []).join(' / ') || '仿單未能自動拆出單一劑量')}</dd>
        <dt>頻次</dt><dd>${esc((t.frequency_mentions || []).join(' / ') || '仿單未能自動拆出單一頻次')}</dd>
        <dt>官方用法用量</dt><dd class="dose-text">${esc(t.dosage || '詳如仿單')}</dd>
        <dt>TFDA 資料同步</dt><dd>${esc(tfdaDate || '—')}${t.license_modified ? `；藥證異動 ${esc(t.license_modified)}` : ''}</dd>
      </dl>
      <p class="source-note">健保「能不能用」與 TFDA「核准怎麼用」是不同來源；若兩者限制不同，申報與處方仍分別依最新官方規定。</p>
    </section>` : `<section class="source-panel tfda-panel pending"><div class="source-panel-head"><div><small>TFDA 核准仿單</small><strong>此情境尚未有可安全自動對應的劑量</strong></div></div><p class="source-note">可能是同成分多藥證、仿單只寫「詳如仿單」，或癌種對應仍在 review queue；系統不會自行猜測。</p></section>`;
    $('dialogContent').innerHTML = `<p class="eyebrow">${esc(c.name)} · § ${esc(x.section)}</p>
      <h3 class="dialog-title">${esc(x.drug)}</h3>
      <div class="regimen">${esc(x.regimen)}</div>
      <section class="source-panel nhi-panel">
        <div class="source-panel-head"><div><small>健保給付規定</small><strong>${esc(x.setting)}</strong></div><span>§ ${esc(x.section)}</span></div>
        <p class="dialog-summary">${esc(x.summary)}</p>
        <dl class="detail-table compact-table">
          <dt>給付狀態</dt><dd>${esc(x.status || '給付')}</dd>
          <dt>治療線別</dt><dd>${esc(lineGroup(x))}${x.line && x.line !== lineGroup(x) ? `（${esc(x.line)}）` : ``}</dd>
          <dt>Biomarker</dt><dd>${esc(x.biomarker)}</dd>
          <dt>事前審查</dt><dd>${x.prior_auth ? '需要' : '條目未標為需要'}</dd>
          <dt>審查 / 追蹤</dt><dd>${esc(x.review)}</dd>
          <dt>療程限制</dt><dd>${esc(x.duration)}</dd>
          <dt>條文生效</dt><dd>${esc(x.effective)}</dd>
        </dl>
      </section>
      ${tfdaPanel}
      <div class="dialog-actions"><a class="action-button primary" href="${esc(pdfLink(x))}" target="_blank" rel="noopener">健保署原始 PDF ↗</a>${showTfda && t.label_url ? `<a class="action-button tfda-link" href="${esc(t.label_url)}" target="_blank" rel="noopener">TFDA 官方仿單 ↗</a>` : ''}<button class="action-button" value="close">關閉</button></div>`;
    $('detailDialog').showModal();
  }

  function showChangesDialog()'''
if not show_re.search(app):
    if 'class="source-panel tfda-panel"' not in app:
        raise SystemExit('Cannot locate showDetail block')
else:
    app = show_re.sub(new_show, app, count=1)

APP.write_text(app, encoding='utf-8')

index = INDEX.read_text(encoding='utf-8')
if '<script src="assets/tfda-labels.js"></script>' not in index:
    anchor = '  <script src="assets/nhi-candidates.js"></script>\n  <script src="assets/app.js"></script>'
    repl = '  <script src="assets/nhi-candidates.js"></script>\n  <script src="assets/tfda-labels.js"></script>\n  <script src="assets/app.js"></script>'
    if anchor not in index:
        raise SystemExit('Cannot locate index script anchor')
    index = index.replace(anchor, repl, 1)
index = index.replace('搜尋藥名 / 商品名 / 癌種 / biomarker…', '搜尋藥名 / 癌種 / biomarker / dose / q3w…')
index = index.replace('Cancer → setting → line → biomarker → reimbursed regimen。', 'Cancer → setting → line → biomarker → reimbursed regimen → TFDA label dose。')
index = index.replace('此網站為臨床快速查詢 beta；申報、處方與治療決策請以健保署最新公告、藥品許可證與院內規範為準。', '此網站為臨床快速查詢 beta；健保給付與 TFDA 核准仿單分開標示來源。申報、處方與治療決策請以健保署最新公告、TFDA 最新藥品許可證／仿單與院內規範為準。')
INDEX.write_text(index, encoding='utf-8')

css = CSS.read_text(encoding='utf-8')
marker = '/* TFDA label-dose enrichment v1 */'
if marker not in css:
    css += r'''

/* TFDA label-dose enrichment v1 */
.badge.tfda { background:#eef8f1; color:#216a3d; border-color:#cfe8d6; }
.tfda-card-dose { margin-top:10px; padding:8px 10px; border-radius:10px; background:#f2f8f4; border:1px solid #dcebe0; }
.tfda-card-dose small { display:block; color:#4c7560; font-size:10px; font-weight:800; letter-spacing:.06em; text-transform:uppercase; }
.tfda-card-dose span { display:block; margin-top:2px; color:#234d34; font-size:12px; font-weight:650; }
.action-button.tfda-link { border-color:#b9dac2; color:#225f36; background:#f7fbf8; }
.source-panel { margin:17px 0; border:1px solid var(--line); border-radius:14px; padding:14px 15px; background:#fff; }
.source-panel.nhi-panel { border-color:#d8e4e8; }
.source-panel.tfda-panel { border-color:#cfe5d6; background:#fbfefc; }
.source-panel.tfda-panel.pending { border-style:dashed; background:#fafcfa; }
.source-panel-head { display:flex; justify-content:space-between; gap:14px; align-items:flex-start; margin-bottom:8px; }
.source-panel-head small { display:block; color:var(--muted); font-size:10px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
.source-panel-head strong { display:block; margin-top:2px; font-size:15px; }
.source-panel-head > span { color:var(--muted); font-size:11px; text-align:right; }
.compact-table { margin:8px 0 0; }
.dose-text { white-space:pre-wrap; max-height:210px; overflow:auto; line-height:1.65; }
.source-note { margin:10px 0 0; color:var(--muted); font-size:11px; }
@media (max-width:610px) {
  .source-panel { padding:12px; }
  .source-panel-head { display:block; }
  .source-panel-head > span { display:block; text-align:left; margin-top:3px; }
  .dose-text { max-height:260px; }
}
'''
CSS.write_text(css, encoding='utf-8')
print('TFDA dose/label UI patch applied.')

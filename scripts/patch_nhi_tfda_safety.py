#!/usr/bin/env python3
"""Safety pass for TFDA dose UI.

Keeps the TFDA permit/label link visible when mapped, but shows dose/frequency/searchable dose
text only when the extractor marked the indication-specific dose as high confidence.
Run after patch_nhi_tfda_ui.py so future weekly rebuilds preserve this behavior.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'tools/nhi/assets/app.js'
app = APP.read_text(encoding='utf-8')

old_search = "  const tfdaSearchText = (item) => { const t=tfdaFor(item); return t ? [t.product_zh,t.product_en,t.permit,t.dosage,...(t.dose_mentions||[]),...(t.frequency_mentions||[])].filter(Boolean).join(' ') : ''; };"
new_search = "  const tfdaSearchText = (item) => { const t=tfdaFor(item); if (!t) return ''; const safe=t.dose_confidence === 'high'; return [t.product_zh,t.product_en,t.permit,safe ? t.dosage_excerpt || t.dosage : '',...(safe ? (t.dose_mentions||[]) : []),...(safe ? (t.frequency_mentions||[]) : [])].filter(Boolean).join(' '); };"
if old_search in app:
    app = app.replace(old_search, new_search, 1)
elif new_search not in app:
    raise SystemExit('Cannot locate TFDA search helper')

card_re = re.compile(r"  function cardHtml\(x\) \{[\s\S]*?\n  \}\n\n  function renderFilterChips\(\)", re.M)
new_card = r'''  function cardHtml(x) {
    const bio = x.biomarker && x.biomarker !== '—';
    const t = tfdaFor(x);
    const showTfda = tfdaVisible(x);
    const safeDose = showTfda && t.dose_confidence === 'high';
    const doseChip = safeDose && (t.dose_mentions || []).length ? (t.dose_mentions || []).slice(0,3).join(' / ') : '';
    const freqChip = safeDose && (t.frequency_mentions || []).length ? (t.frequency_mentions || []).slice(0,3).join(' / ') : '';
    const tfdaMeta = showTfda ? `<div class="tfda-card-dose${safeDose ? '' : ' withheld'}"><small>TFDA 核准仿單</small><span>${safeDose ? `${esc(doseChip || '仿單劑量已核對')}${freqChip ? ` · ${esc(freqChip)}` : ''}` : '已對應官方仿單 · 此癌種劑量未安全自動拆出'}</span></div>` : '';
    return `<article class="drug-card">
      <div>
        <h3>${esc(x.drug)}</h3>
        <div class="regimen">${esc(x.regimen)}</div>
        <div class="badges">
          <span class="badge">${esc(lineGroup(x))}</span>
          ${x.status && x.status !== '給付' ? `<span class="badge">${esc(x.status)}</span>` : ''}
          ${x.prior_auth ? '<span class="badge auth">事前審查</span>' : ''}
          ${bio ? `<span class="badge bio">${esc(x.biomarker)}</span>` : ''}
          ${showTfda ? `<span class="badge tfda">${safeDose ? 'TFDA dose' : 'TFDA label'}</span>` : ''}
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
    raise SystemExit('Cannot locate cardHtml block for TFDA safety pass')
app = card_re.sub(new_card, app, count=1)

show_re = re.compile(r"  function showDetail\(id\) \{[\s\S]*?\n  \}\n\n  function showChangesDialog\(\)", re.M)
new_show = r'''  function showDetail(id) {
    const x = data.indications.find(i => i.id === id);
    if (!x) return;
    const c = cancerMap[x.cancer];
    const t = tfdaFor(x);
    const showTfda = tfdaVisible(x);
    const safeDose = showTfda && t.dose_confidence === 'high';
    const tfdaDate = tfda.meta?.fetched_at ? String(tfda.meta.fetched_at).slice(0,10) : '';
    const doseStatus = safeDose
      ? `<dt>劑量</dt><dd>${esc((t.dose_mentions || []).join(' / ') || '請見下方官方用法用量')}</dd>
         <dt>頻次</dt><dd>${esc((t.frequency_mentions || []).join(' / ') || '依仿單療程／週期')}</dd>
         <dt>對應依據</dt><dd>${esc(t.dose_match_basis || '適應症特異仿單段落')}</dd>
         <dt>官方用法用量</dt><dd class="dose-text">${esc(t.dosage_excerpt || t.dosage || '詳如仿單')}</dd>`
      : `<dt>劑量 / 頻次</dt><dd><strong>未自動顯示</strong> — 此藥證雖已對應，但無法確定目前癌種對應的單一劑量段落。</dd>
         <dt>原因</dt><dd>${esc(t.dose_withheld_reason || '多適應症仿單或仿單文字無法安全拆分')}</dd>`;
    const tfdaPanel = showTfda ? `<section class="source-panel tfda-panel${safeDose ? '' : ' pending'}">
      <div class="source-panel-head"><div><small>TFDA 核准仿單</small><strong>${esc(t.product_zh || t.product_en || x.drug)}</strong></div><span>${esc(t.match_basis || '')}</span></div>
      <dl class="detail-table compact-table">
        <dt>許可證</dt><dd>${esc(t.permit || '')}</dd>
        <dt>核准適應症</dt><dd>${esc(t.indication || '—')}</dd>
        ${doseStatus}
        <dt>TFDA 資料同步</dt><dd>${esc(tfdaDate || '—')}${t.license_modified ? `；藥證異動 ${esc(t.license_modified)}` : ''}</dd>
      </dl>
      <p class="source-note">健保「能不能用」與 TFDA「核准怎麼用」是不同來源。只有明確對到此癌種用法用量小節，或單一適應症藥證時，系統才自動顯示 dose / frequency；其他情況只提供官方仿單，不猜。</p>
    </section>` : `<section class="source-panel tfda-panel pending"><div class="source-panel-head"><div><small>TFDA 核准仿單</small><strong>此情境尚未有可安全自動對應的藥證</strong></div></div><p class="source-note">可能是同成分多藥證或癌種對應仍在 review queue；系統不會自行猜測。</p></section>`;
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
    raise SystemExit('Cannot locate showDetail block for TFDA safety pass')
app = show_re.sub(new_show, app, count=1)

APP.write_text(app, encoding='utf-8')
print('TFDA dose UI now requires high-confidence indication-specific mapping.')

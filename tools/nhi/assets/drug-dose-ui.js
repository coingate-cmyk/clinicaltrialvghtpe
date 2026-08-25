(() => {
  'use strict';
  const data = window.NHI_DATA;
  const tfda = window.TFDA_LABELS || { meta: {}, byIndicationId: {} };
  const dialog = document.getElementById('detailDialog');
  const dialogContent = document.getElementById('dialogContent');
  if (!data || !dialog || !dialogContent) return;

  const byId = Object.fromEntries((data.indications || []).map(x => [x.id, x]));
  const cancerMap = Object.fromEntries((data.cancers || []).map(x => [x.id, x]));
  const sourcePdf = window.NHI_CHANGES?.source_url || data.meta?.source_url || '';

  const esc = (s='') => String(s).replace(/[&<>'\"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','\"':'&quot;'}[m]));
  const lineGroup = x => x.line_group || x.line || '';
  const tfdaFor = x => (tfda.byIndicationId || {})[x?.id] || null;
  const tfdaVisible = t => t && (t.status === 'matched' || t.status === 'generic-label');
  const pdfLink = x => `${sourcePdf}#page=${Number(x.pdf_page || 1)}`;
  const firstLabelUrl = t => (Array.isArray(t?.label_urls) && t.label_urls[0]) || String(t?.label_url || '').split(';')[0] || '';

  function productName(x) {
    const t = tfdaFor(x);
    if (!tfdaVisible(t)) return '';
    return String(t.product_en || t.product_zh || '').trim();
  }

  function displayDrugName(x) {
    const brand = productName(x);
    return brand && !brand.toLowerCase().includes(String(x.drug || '').toLowerCase())
      ? `${x.drug}（${brand}）`
      : (x.drug || brand || '未命名藥物');
  }

  function compactDoseText(x) {
    const t = tfdaFor(x);
    if (!tfdaVisible(t) || t.dose_confidence !== 'high') return '';
    const doses = (t.dose_mentions || []).slice(0, 3).join(' / ');
    const freqs = (t.frequency_mentions || []).slice(0, 3).join(' / ');
    return [doses, freqs].filter(Boolean).join(' · ');
  }

  function tfdaPanelHtml(x) {
    const t = tfdaFor(x);
    if (!tfdaVisible(t)) {
      const note = t?.status === 'regimen-components-required'
        ? '此為合併療法，必須分別對應各成分的 TFDA 仿單；目前不以單一成分仿單冒充整個 regimen。'
        : '目前尚未有可安全自動對應的 TFDA 仿單／劑量。';
      return `<section class="source-panel tfda-panel pending"><div class="source-panel-head"><div><small>TFDA 核准仿單</small><strong>尚未安全對應</strong></div></div><p class="source-note">${esc(note)}</p></section>`;
    }

    const safeDose = t.dose_confidence === 'high';
    const syncDate = tfda.meta?.fetched_at ? String(tfda.meta.fetched_at).slice(0, 10) : '—';
    const doseRows = safeDose
      ? `<dt>劑量</dt><dd>${esc((t.dose_mentions || []).join(' / ') || '請見下方仿單段落')}</dd>
         <dt>頻次</dt><dd>${esc((t.frequency_mentions || []).join(' / ') || '依仿單療程／週期')}</dd>
         <dt>對應依據</dt><dd>${esc(t.dose_match_basis || '癌種特異用法用量段落')}</dd>
         <dt>官方用法用量</dt><dd class="dose-text">${esc(t.dosage_excerpt || t.dosage || '詳如仿單')}</dd>`
      : `<dt>劑量 / 頻次</dt><dd><strong>未自動顯示</strong> — 已找到官方仿單，但尚無法確定此癌種對應的單一劑量段落。</dd>
         <dt>原因</dt><dd>${esc(t.dose_withheld_reason || '多適應症仿單或仿單文字無法安全拆分')}</dd>`;

    return `<section class="source-panel tfda-panel${safeDose ? '' : ' pending'}">
      <div class="source-panel-head"><div><small>TFDA 核准仿單</small><strong>${esc(t.product_en || t.product_zh || x.drug)}</strong></div><span>${esc(t.match_basis || '')}</span></div>
      <dl class="detail-table compact-table">
        <dt>許可證</dt><dd>${esc(t.permit || '—')}</dd>
        <dt>核准適應症</dt><dd>${esc(t.indication || '—')}</dd>
        ${doseRows}
        <dt>TFDA 資料同步</dt><dd>${esc(syncDate)}${t.license_modified ? `；藥證異動 ${esc(t.license_modified)}` : ''}</dd>
      </dl>
      <p class="source-note">健保「能不能用」與 TFDA「核准怎麼用」分開標示。只有高信心對到此癌種用法用量時才直接顯示 dose / frequency。</p>
    </section>`;
  }

  function showUnifiedDetail(id) {
    const x = byId[id];
    if (!x) return;
    const c = cancerMap[x.cancer];
    const t = tfdaFor(x);
    const labelUrl = tfdaVisible(t) ? firstLabelUrl(t) : '';
    dialogContent.innerHTML = `<p class="eyebrow">${esc(c?.name || x.cancer)} · § ${esc(x.section)}</p>
      <h3 class="dialog-title">${esc(displayDrugName(x))}</h3>
      <div class="regimen">${esc(x.regimen)}</div>
      <section class="source-panel nhi-panel">
        <div class="source-panel-head"><div><small>健保給付規定</small><strong>${esc(x.setting)}</strong></div><span>§ ${esc(x.section)}</span></div>
        <p class="dialog-summary">${esc(x.summary)}</p>
        <dl class="detail-table compact-table">
          <dt>給付狀態</dt><dd>${esc(x.status || '給付')}</dd>
          <dt>治療線別</dt><dd>${esc(lineGroup(x))}${x.line && x.line !== lineGroup(x) ? `（${esc(x.line)}）` : ''}</dd>
          <dt>Biomarker</dt><dd>${esc(x.biomarker)}</dd>
          <dt>事前審查</dt><dd>${x.prior_auth ? '需要' : '條目未標為需要'}</dd>
          <dt>審查 / 追蹤</dt><dd>${esc(x.review)}</dd>
          <dt>療程限制</dt><dd>${esc(x.duration)}</dd>
          <dt>條文生效</dt><dd>${esc(x.effective)}</dd>
        </dl>
      </section>
      ${tfdaPanelHtml(x)}
      <div class="dialog-actions">
        <a class="action-button primary" href="${esc(pdfLink(x))}" target="_blank" rel="noopener">健保署原始 PDF ↗</a>
        ${labelUrl ? `<a class="action-button tfda-link" href="${esc(labelUrl)}" target="_blank" rel="noopener">TFDA 官方仿單 ↗</a>` : ''}
        <button class="action-button" value="close">關閉</button>
      </div>`;
    dialog.showModal();
  }

  function addDosePreview(container, x) {
    if (!container || container.querySelector('.tfda-card-dose.unified-dose-preview')) return;
    const text = compactDoseText(x);
    if (!text) return;
    const box = document.createElement('div');
    box.className = 'tfda-card-dose unified-dose-preview';
    box.innerHTML = `<small>TFDA 劑量 / 頻次</small><span>${esc(text)}</span>`;
    const regimen = container.querySelector('.regimen');
    (regimen || container.firstElementChild)?.insertAdjacentElement('afterend', box);
  }

  function decorateDrugNames(root=document) {
    root.querySelectorAll?.('[data-map-item]').forEach(btn => {
      const x = byId[btn.dataset.mapItem];
      const strong = btn.querySelector('strong');
      if (x && strong) strong.textContent = displayDrugName(x);
      if (x) {
        const text = compactDoseText(x);
        if (text && !btn.querySelector('.pathway-dose-preview')) {
          const small = document.createElement('small');
          small.className = 'pathway-dose-preview';
          small.textContent = `TFDA: ${text}`;
          btn.appendChild(small);
        }
      }
    });
    root.querySelectorAll?.('[data-drug-detail]').forEach(btn => {
      const x = byId[btn.dataset.drugDetail];
      const hit = btn.closest('.drug-hit');
      const title = hit?.querySelector('h4');
      if (x && title) title.textContent = displayDrugName(x);
      if (x && hit) addDosePreview(hit.querySelector('.drug-hit-main'), x);
      if (btn && btn.textContent.trim() === '摘要') btn.textContent = '健保 / 劑量';
    });
    root.querySelectorAll?.('[data-detail]').forEach(btn => {
      const x = byId[btn.dataset.detail];
      const card = btn.closest('.drug-card');
      const title = card?.querySelector('h3');
      if (x && title) title.textContent = displayDrugName(x);
      if (x && card) addDosePreview(card.firstElementChild, x);
      if (btn.textContent.includes('摘要')) btn.textContent = '健保 / 劑量';
    });
  }

  document.addEventListener('click', e => {
    const drugBtn = e.target.closest?.('[data-drug-detail]');
    if (drugBtn) {
      e.preventDefault();
      e.stopImmediatePropagation();
      showUnifiedDetail(drugBtn.dataset.drugDetail);
      return;
    }
    const detailBtn = e.target.closest?.('[data-detail]');
    if (detailBtn) {
      e.preventDefault();
      e.stopImmediatePropagation();
      showUnifiedDetail(detailBtn.dataset.detail);
      return;
    }
    const mapBtn = e.target.closest?.('[data-map-item]');
    if (mapBtn) {
      e.preventDefault();
      e.stopImmediatePropagation();
      showUnifiedDetail(mapBtn.dataset.mapItem);
    }
  }, true);

  decorateDrugNames(document);
  new MutationObserver(mutations => {
    for (const m of mutations) for (const n of m.addedNodes || []) if (n.nodeType === 1) decorateDrugNames(n);
  }).observe(document.body, { childList: true, subtree: true });
})();
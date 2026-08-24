(() => {
  'use strict';
  const data = window.NHI_DATA;
  const changes = window.NHI_CHANGES || { status: 'not-run', changes: [] };
  const tfda = window.TFDA_LABELS || { meta: {}, byIndicationId: {} };
  const tfdaFor = (item) => (tfda.byIndicationId || {})[item?.id] || null;
  const tfdaVisible = (item) => { const t=tfdaFor(item); return t && (t.status === 'matched' || t.status === 'generic-label'); };
  const tfdaSearchText = (item) => { const t=tfdaFor(item); return t ? [t.product_zh,t.product_en,t.permit,t.dosage,...(t.dose_mentions||[]),...(t.frequency_mentions||[])].filter(Boolean).join(' ') : ''; };
  if (!data) throw new Error('NHI_DATA not loaded');

  const $ = (id) => document.getElementById(id);
  const state = { cancer: null, query: '', line: '', biomarker: '', auth: '' };
  const cancerMap = Object.fromEntries(data.cancers.map(c => [c.id, c]));
  const sourcePdf = changes.source_url || data.meta.source_url;

  function esc(s='') {
    return String(s).replace(/[&<>'"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[m]));
  }
  function normalize(s='') { return String(s).toLowerCase().replace(/\s+/g,' ').trim(); }
  function uniq(arr) { return [...new Set(arr.filter(Boolean))].sort((a,b) => a.localeCompare(b,'zh-Hant')); }
  function lineGroup(x) { return x.line_group || x.line || ''; }
  function pdfLink(item) { return `${sourcePdf}#page=${Number(item.pdf_page || 1)}`; }

  function renderHeader() {
    const sourceUpdate = changes.source_update || data.meta.source_update;
    $('sourceBadge').textContent = `官方來源 ${sourceUpdate}`;
    $('footerMeta').textContent = `${data.meta.source_name}｜資料核對 ${data.meta.verified_on}｜${data.meta.scope}`;
    const curatedCancers = new Set(data.indications.map(x => x.cancer)).size;
    const authCount = data.indications.filter(x => x.prior_auth).length;
    const biomarkerCount = data.indications.filter(x => x.biomarker && x.biomarker !== '—').length;
    $('heroStats').innerHTML = [
      [data.cancers.length, '癌種 taxonomy'], [curatedCancers, '已有 curated data'], [data.indications.length, '給付情境'], [authCount, '需事前審查']
    ].map(([n,l]) => `<div class="stat-card"><b>${n}</b><span>${l}</span></div>`).join('');
  }

  function renderChanges() {
    const panel = $('changePanel');
    const n = Array.isArray(changes.changes) ? changes.changes.length : 0;
    const gaps = Number(changes.coverage?.missing_candidate_count || 0);
    const sections = Number(changes.section_count || 0);
    if (changes.status === 'ok') {
      const headline = n ? `本次偵測到 ${n} 個第 9 節條文章節變更` : '第 9 節自動擷取與比對成功';
      const detail = `${sections ? `已解析 ${sections} 個 9.x 章節；` : ''}漏項偵測目前有 ${gaps} 個「癌種 × 條文」候選待人工核對。curated 臨床摘要不會自動覆寫。`;
      panel.innerHTML = `<div><strong>${esc(headline)}</strong><span>${esc(detail)}</span></div>${n ? '<button class="ghost-button compact" id="showChanges">查看變更</button>' : ''}`;
      if (n) $('showChanges').addEventListener('click', () => showChangesDialog());
    } else {
      panel.innerHTML = `<div><strong>每週自動更新管線建置中</strong><span>正式流程：健保署第 9 節 → section diff → 癌種漏項偵測 → review queue；只有人工核對後才更新臨床摘要。</span></div>`;
    }
  }

  function renderCancerGrid() {
    $('cancerGrid').innerHTML = data.cancers.map(c => {
      const count = data.indications.filter(x => x.cancer === c.id).length;
      const status = count ? `${count} 個給付情境 →` : '已納入監測 · 待整理 →';
      return `<button class="cancer-card${count ? '' : ' pending'}" data-cancer="${esc(c.id)}">
        <span class="cancer-icon">${esc(c.icon)}</span>
        <h3>${esc(c.name)}</h3><p>${esc(c.description)}</p>
        <small class="muted">${esc(c.group || '')}</small>
        <span class="count">${esc(status)}</span>
      </button>`;
    }).join('');
    document.querySelectorAll('[data-cancer]').forEach(btn => btn.addEventListener('click', () => openCancer(btn.dataset.cancer)));
  }

  function setOptions(select, values, allLabel) {
    const current = select.value;
    select.innerHTML = `<option value="">${allLabel}</option>` + values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
    if (values.includes(current)) select.value = current;
  }

  function baseItems() {
    return data.indications.filter(x => !state.cancer || x.cancer === state.cancer);
  }
  function filteredItems() {
    const q = normalize(state.query);
    return baseItems().filter(x => {
      if (state.line && lineGroup(x) !== state.line) return false;
      if (state.biomarker && x.biomarker !== state.biomarker) return false;
      if (state.auth === 'yes' && !x.prior_auth) return false;
      if (state.auth === 'no' && x.prior_auth) return false;
      if (q) {
        const hay = normalize([x.drug,x.regimen,x.setting,x.line,lineGroup(x),x.biomarker,x.summary,x.section,...(x.tags||[]),cancerMap[x.cancer]?.name,tfdaSearchText(x)].join(' '));
        if (!hay.includes(q)) return false;
      }
      return true;
    }).sort((a,b) => lineGroup(a).localeCompare(lineGroup(b), 'en', {numeric:true}) || a.drug.localeCompare(b.drug));
  }

  function openCancer(id) {
    state.cancer = id || null;
    state.line = ''; state.biomarker = ''; state.auth = '';
    history.replaceState(null, '', id ? `#/${id}` : '#/all');
    renderResults();
    $('resultsSection').hidden = false;
    $('resultsSection').scrollIntoView({behavior:'smooth', block:'start'});
  }

  function renderResults() {
    const c = state.cancer ? cancerMap[state.cancer] : null;
    $('resultEyebrow').textContent = c ? `${c.group || ''} · ${c.en}` : 'ALL CURATED CANCERS';
    $('resultTitle').textContent = c ? c.name : '全部已整理給付情境';
    $('resultDescription').textContent = c ? c.description : '目前已完成人工結構化的給付項目；其他癌種已進入每週自動 coverage audit。';

    const base = baseItems();
    setOptions($('lineFilter'), uniq(base.map(lineGroup)), '所有線別');
    setOptions($('biomarkerFilter'), uniq(base.map(x => x.biomarker).filter(x => x !== '—')), '所有 biomarker');
    $('lineFilter').value = state.line;
    $('biomarkerFilter').value = state.biomarker;
    $('authFilter').value = state.auth;

    const items = filteredItems();
    $('resultCount').innerHTML = `<b>${items.length}</b><span> 項符合</span>`;
    $('results').innerHTML = items.map(cardHtml).join('');
    $('emptyState').hidden = items.length > 0;
    if (!items.length) {
      $('emptyState').innerHTML = c && !c.curated
        ? `<strong>${esc(c.name)} 已納入自動監測</strong><span>目前尚未完成 curated records；coverage audit 會先列出健保第 9 節的候選條文，人工核對後再上線。</span>`
        : '<strong>沒有符合條件的項目</strong><span>換一個線別、biomarker 或搜尋詞試試。</span>';
    }
    renderFilterChips();

    document.querySelectorAll('[data-detail]').forEach(btn => btn.addEventListener('click', () => showDetail(btn.dataset.detail)));
  }

  function cardHtml(x) {
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

  function renderFilterChips() {
    const chips = [];
    if (state.query) chips.push(`搜尋：${state.query}`);
    if (state.line) chips.push(`線別：${state.line}`);
    if (state.biomarker) chips.push(`Biomarker：${state.biomarker}`);
    if (state.auth) chips.push(state.auth === 'yes' ? '需事審' : '免事審');
    $('activeFilters').innerHTML = chips.map(x => `<span class="filter-chip">${esc(x)}</span>`).join('');
  }

  function showDetail(id) {
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

  function showChangesDialog() {
    const rows = (changes.changes || []).slice(0,25).map(c => `<li><b>${esc(c.section_id || '')}</b> ${esc(c.title || '')} <span class="muted">${esc(c.change_type || 'changed')}</span></li>`).join('');
    $('dialogContent').innerHTML = `<p class="eyebrow">AUTO DIFF</p><h3 class="dialog-title">待人工核對的條文變更</h3><p class="muted">只有偵測與排隊，不直接覆寫臨床摘要。</p><ul>${rows || '<li>沒有變更</li>'}</ul><div class="dialog-actions"><button class="action-button" value="close">關閉</button></div>`;
    $('detailDialog').showModal();
  }

  function applySearch(value) {
    state.query = value.trim();
    if (state.query && $('resultsSection').hidden) {
      state.cancer = null;
      $('resultsSection').hidden = false;
    }
    renderResults();
  }

  $('globalSearch').addEventListener('input', e => applySearch(e.target.value));
  $('lineFilter').addEventListener('change', e => { state.line=e.target.value; renderResults(); });
  $('biomarkerFilter').addEventListener('change', e => { state.biomarker=e.target.value; renderResults(); });
  $('authFilter').addEventListener('change', e => { state.auth=e.target.value; renderResults(); });
  $('resetFilters').addEventListener('click', () => { state.line=''; state.biomarker=''; state.auth=''; state.query=''; $('globalSearch').value=''; renderResults(); });
  $('showAllBtn').addEventListener('click', () => openCancer(null));
  $('backBtn').addEventListener('click', () => { $('resultsSection').hidden=true; history.replaceState(null,'','#/'); window.scrollTo({top:0, behavior:'smooth'}); });
  document.addEventListener('keydown', e => { if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') { e.preventDefault(); $('globalSearch').focus(); } });

  renderHeader(); renderChanges(); renderCancerGrid();
  const hashId = location.hash.match(/^#\/([^/?#]+)$/)?.[1];
  if (hashId && cancerMap[hashId]) { state.cancer=hashId; $('resultsSection').hidden=false; renderResults(); }
})();

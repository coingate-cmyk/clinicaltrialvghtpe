(() => {
  'use strict';
  const data = window.NHI_DATA;
  const changes = window.NHI_CHANGES || { status: 'not-run', changes: [] };
  if (!data) throw new Error('NHI_DATA not loaded');

  const $ = (id) => document.getElementById(id);
  const state = { cancer: null, query: '', line: '', biomarker: '', auth: '' };
  const cancerMap = Object.fromEntries(data.cancers.map(c => [c.id, c]));
  const sourcePdf = data.meta.source_url;

  function esc(s='') {
    return String(s).replace(/[&<>'"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[m]));
  }
  function normalize(s='') { return String(s).toLowerCase().replace(/\s+/g,' ').trim(); }
  function uniq(arr) { return [...new Set(arr.filter(Boolean))].sort((a,b) => a.localeCompare(b,'zh-Hant')); }
  function lineGroup(x) { return x.line_group || x.line || ''; }
  function pdfLink(item) { return `${sourcePdf}#page=${Number(item.pdf_page || 1)}`; }

  function renderHeader() {
    $('sourceBadge').textContent = `官方來源 ${data.meta.source_update}`;
    $('footerMeta').textContent = `${data.meta.source_name}｜資料核對 ${data.meta.verified_on}｜${data.meta.scope}`;
    const authCount = data.indications.filter(x => x.prior_auth).length;
    const biomarkerCount = data.indications.filter(x => x.biomarker && x.biomarker !== '—').length;
    $('heroStats').innerHTML = [
      [data.cancers.length, '癌種'], [data.indications.length, '給付情境'], [authCount, '需事前審查'], [biomarkerCount, 'biomarker-linked']
    ].map(([n,l]) => `<div class="stat-card"><b>${n}</b><span>${l}</span></div>`).join('');
  }

  function renderChanges() {
    const panel = $('changePanel');
    const n = Array.isArray(changes.changes) ? changes.changes.length : 0;
    if (changes.status === 'ok' && n) {
      panel.innerHTML = `<div><strong>本次偵測到 ${n} 個條文章節有變更</strong><span>自動更新只建立 review queue，不會直接改寫臨床摘要。</span></div><button class="ghost-button compact" id="showChanges">查看變更</button>`;
      $('showChanges').addEventListener('click', () => showChangesDialog());
    } else if (changes.status === 'ok') {
      panel.innerHTML = `<div><strong>本次沒有偵測到第 9 節條文變更</strong><span>來源擷取成功；curated data 維持原版本。</span></div>`;
    } else {
      panel.innerHTML = `<div><strong>自動更新尚未在這份離線 prototype 執行</strong><span>部署到 GitHub 後，每週 workflow 會抓官方 ODT、比對 section diff，再產生 review queue。</span></div>`;
    }
  }

  function renderCancerGrid() {
    $('cancerGrid').innerHTML = data.cancers.map(c => {
      const count = data.indications.filter(x => x.cancer === c.id).length;
      return `<button class="cancer-card" data-cancer="${esc(c.id)}">
        <span class="cancer-icon">${esc(c.icon)}</span>
        <h3>${esc(c.name)}</h3><p>${esc(c.description)}</p>
        <span class="count">${count} 個給付情境 →</span>
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
        const hay = normalize([x.drug,x.regimen,x.setting,x.line,lineGroup(x),x.biomarker,x.summary,x.section,...(x.tags||[]),cancerMap[x.cancer]?.name].join(' '));
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
    $('resultEyebrow').textContent = c ? c.en : 'ALL GI CANCERS';
    $('resultTitle').textContent = c ? c.name : '全部 GI 給付情境';
    $('resultDescription').textContent = c ? c.description : '六癌種目前已結構化的給付項目。';

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
    renderFilterChips();

    document.querySelectorAll('[data-detail]').forEach(btn => btn.addEventListener('click', () => showDetail(btn.dataset.detail)));
  }

  function cardHtml(x) {
    const bio = x.biomarker && x.biomarker !== '—';
    return `<article class="drug-card">
      <div>
        <h3>${esc(x.drug)}</h3>
        <div class="regimen">${esc(x.regimen)}</div>
        <div class="badges">
          <span class="badge">${esc(lineGroup(x))}</span>
          ${x.prior_auth ? '<span class="badge auth">事前審查</span>' : ''}
          ${bio ? `<span class="badge bio">${esc(x.biomarker)}</span>` : ''}
          <span class="badge">§ ${esc(x.section)}</span>
        </div>
      </div>
      <div class="meta-grid">
        <div class="meta-item"><small>Setting</small><span>${esc(x.setting)}</span></div>
        <div class="meta-item"><small>Biomarker</small><span>${esc(x.biomarker)}</span></div>
        <div class="meta-item"><small>Review</small><span>${esc(x.review)}</span></div>
        <div class="meta-item"><small>Duration</small><span>${esc(x.duration)}</span></div>
      </div>
      <div class="card-actions">
        <button class="action-button primary" data-detail="${esc(x.id)}">摘要</button>
        <a class="action-button" href="${esc(pdfLink(x))}" target="_blank" rel="noopener">官方 PDF ↗</a>
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
    $('dialogContent').innerHTML = `<p class="eyebrow">${esc(c.name)} · § ${esc(x.section)}</p>
      <h3 class="dialog-title">${esc(x.drug)}</h3>
      <div class="regimen">${esc(x.regimen)}</div>
      <p class="dialog-summary">${esc(x.summary)}</p>
      <dl class="detail-table">
        <dt>治療情境</dt><dd>${esc(x.setting)}</dd>
        <dt>治療線別</dt><dd>${esc(lineGroup(x))}${x.line && x.line !== lineGroup(x) ? `（${esc(x.line)}）` : ``}</dd>
        <dt>Biomarker</dt><dd>${esc(x.biomarker)}</dd>
        <dt>事前審查</dt><dd>${x.prior_auth ? '需要' : '條目未標為需要'}</dd>
        <dt>審查 / 追蹤</dt><dd>${esc(x.review)}</dd>
        <dt>療程限制</dt><dd>${esc(x.duration)}</dd>
        <dt>條文生效</dt><dd>${esc(x.effective)}</dd>
      </dl>
      <div class="dialog-actions"><a class="action-button primary" href="${esc(pdfLink(x))}" target="_blank" rel="noopener">開啟健保署原始 PDF ↗</a><button class="action-button" value="close">關閉</button></div>`;
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
  const hashCancer = location.hash.match(/^#\/(gastric|esophageal|colorectal|hcc|biliary|pancreatic)$/)?.[1];
  if (hashCancer) { state.cancer=hashCancer; $('resultsSection').hidden=false; renderResults(); }
})();

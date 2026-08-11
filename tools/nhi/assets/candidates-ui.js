(() => {
  'use strict';
  const data = window.NHI_DATA;
  const candidateData = window.NHI_CANDIDATES;
  if (!data || !candidateData) return;

  const sourceUrl = candidateData.meta?.source_url || data.meta?.source_url || '#';
  const cancerMap = Object.fromEntries((data.cancers || []).map(c => [c.id, c]));
  const esc = (s='') => String(s).replace(/[&<>'"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[m]));

  function ensurePanel() {
    let panel = document.getElementById('officialCandidatePanel');
    if (panel) return panel;
    const results = document.getElementById('resultsSection');
    if (!results) return null;
    panel = document.createElement('section');
    panel.id = 'officialCandidatePanel';
    panel.className = 'candidate-panel';
    panel.hidden = true;
    const empty = document.getElementById('emptyState');
    if (empty?.parentNode) empty.parentNode.insertBefore(panel, empty.nextSibling);
    else results.appendChild(panel);
    return panel;
  }

  function currentCancerId() {
    return location.hash.match(/^#\/([^/?#]+)/)?.[1] || null;
  }

  function render() {
    const panel = ensurePanel();
    if (!panel) return;
    const id = currentCancerId();
    const cancer = cancerMap[id];
    const row = candidateData.by_cancer?.[id];
    if (!cancer || cancer.curated || !row || !row.candidates?.length) {
      panel.hidden = true;
      panel.innerHTML = '';
      return;
    }

    panel.hidden = false;
    panel.innerHTML = `
      <div class="section-heading candidate-heading">
        <div>
          <p class="eyebrow">OFFICIAL CANDIDATES · NOT YET CURATED</p>
          <h3>健保第 9 節偵測到 ${row.candidates.length} 個候選章節</h3>
          <p class="muted">這裡只列官方條文章節與藥名/標題，尚未判讀治療線別、biomarker 或完整給付條件；可先用來找藥與協助我們抓漏。</p>
        </div>
      </div>
      <div class="result-list candidate-list">
        ${row.candidates.map(x => `
          <article class="drug-card candidate-card">
            <div>
              <h3>${esc(x.title || x.section_id)}</h3>
              <div class="badges">
                <span class="badge">§ ${esc(x.section_id)}</span>
                <span class="badge auth">官方候選 · 未人工整理</span>
              </div>
            </div>
            <div class="card-actions">
              <a class="action-button" href="${esc(sourceUrl)}" target="_blank" rel="noopener">官方 PDF ↗</a>
            </div>
          </article>`).join('')}
      </div>`;
  }

  document.addEventListener('click', (e) => {
    if (e.target.closest('[data-cancer], #showAllBtn, #backBtn')) setTimeout(render, 0);
  });
  window.addEventListener('hashchange', render);
  setTimeout(render, 0);
})();

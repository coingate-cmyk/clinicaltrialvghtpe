(() => {
  'use strict';

  const data = window.NHI_DATA;
  const resultsSection = document.getElementById('resultsSection');
  const resultsHead = resultsSection?.querySelector('.results-head');
  const filterBar = resultsSection?.querySelector('.filter-bar');
  const activeFilters = document.getElementById('activeFilters');
  const results = document.getElementById('results');
  const emptyState = document.getElementById('emptyState');
  const globalSearch = document.getElementById('globalSearch');
  if (!data || !resultsSection || !resultsHead || !filterBar || !results || !activeFilters || !emptyState) return;

  const byId = Object.fromEntries(data.indications.map(x => [x.id, x]));
  const modeByCancer = {};

  const maps = {
    gastric: {
      kicker: 'GASTRIC / GEJ · NHI PATHWAY',
      title: '先分治療情境，再用 HER2 / PD-L1 / CLDN18.2 找健保路徑',
      intro: '這張圖只整理目前健保給付的臨床分岔，不代表治療指引排序。點藥物即可開啟原本的給付摘要與官方 PDF。',
      alerts: [
        '目前健保規定下，HER2 non-overexpressing 第一線的 nivolumab 組合與 zolbetuximab 組合僅得擇一，治療失敗後不可互換。',
        '化療 backbone 的完整給付（oxaliplatin / fluoropyrimidine / docetaxel / UFT 等）仍可在「完整條文」查看。'
      ],
      stages: [
        {
          step: '1', title: '根除性手術後', subtitle: '先確認是否符合條文分期與手術條件',
          lanes: [
            { label: 'Adjuvant', criterion: '特定 Stage II–III 胃癌，根除性手術後', items: ['gc-s1-adj'] }
          ]
        },
        {
          step: '2', title: '局部晚期不可切除 / 復發 / 轉移：第一線', subtitle: '先看 HER2，再看 PD-L1 / CLDN18.2；同時保留化療 backbone',
          lanes: [
            { label: 'HER2 positive', criterion: 'IHC 3+ 或 FISH+', items: ['gc-trastuzumab'] },
            { label: 'HER2 non-overexpressed + PD-L1', criterion: 'PD-L1 CPS ≥5', items: ['gc-nivo-1l'] },
            { label: 'HER2 negative + CLDN18.2', criterion: 'CLDN18.2 ≥75% tumor cells，中至強染色', items: ['gc-zolbetuximab'] },
            { label: 'Chemotherapy backbone', criterion: '不依賴特定 biomarker 的第一線化療', items: ['gc-capecitabine-platinum'] }
          ]
        },
        {
          step: '3', title: '後線', subtitle: '健保條文中的後線與一般化療選項',
          lanes: [
            { label: '≥3L', criterion: '先前至少 2 種治療；適合者應包含 HER2 targeting', items: ['gc-lonsurf'] },
            { label: '其他 cytotoxic option', criterion: '條文未固定於特定線別', items: ['gc-docetaxel'] }
          ]
        }
      ]
    },

    hcc: {
      kicker: 'HCC · NHI PATHWAY',
      title: '先確認 Child-Pugh A 與 advanced HCC 條件，再看 1L 與 post-sorafenib',
      intro: '這張圖特別把健保「前一線藥物限制」拉出來，避免把 regorafenib / ramucirumab 誤讀成所有第一線失敗後都能接。',
      alerts: [
        'Sorafenib、lenvatinib、atezolizumab+bevacizumab、durvalumab+tremelimumab 在現行一線給付下僅得擇一，原則上不得互換。',
        'Regorafenib 與 ramucirumab 的現行條文都是 post-sorafenib；不是 generic 2L after any 1L。Ramucirumab 另要求 AFP ≥400 ng/mL。',
        'Atezolizumab+bevacizumab 或 durvalumab+tremelimumab 治療失敗後，現行 ICI 條文明載不得再申請 regorafenib 或 ramucirumab。'
      ],
      stages: [
        {
          step: '0', title: '先過共同門檻', subtitle: 'Advanced HCC reimbursement gate',
          lanes: [
            { label: 'Eligibility', criterion: 'Child-Pugh A，且符合肝外轉移 / 大血管侵犯 / 條文定義 TACE failure 等條件之一', items: [] }
          ]
        },
        {
          step: '1', title: '第一線：四選一', subtitle: '依病人狀況選擇；此圖顯示的是健保可申請路徑，不做療效排序',
          lanes: [
            { label: 'TKI', criterion: 'Child-Pugh A advanced HCC', items: ['hcc-sorafenib', 'hcc-lenvatinib'] },
            { label: 'ICI + anti-VEGF', criterion: '未曾接受全身性治療；不需 PD-L1 報告', items: ['hcc-atezo-bev'] },
            { label: 'Dual immunotherapy', criterion: '未曾接受全身性治療；不需 PD-L1 報告', items: ['hcc-durva-treme'] }
          ]
        },
        {
          step: '2', title: 'Sorafenib failure 後', subtitle: '這個 predecessor 是健保條文的關鍵，不應只標成「2L」',
          lanes: [
            { label: 'Post-sorafenib', criterion: 'Child-Pugh A；sorafenib failure', items: ['hcc-regorafenib'] },
            { label: 'Post-sorafenib + AFP high', criterion: 'Child-Pugh A；sorafenib failure；AFP ≥400 ng/mL', items: ['hcc-ramucirumab'] }
          ]
        }
      ]
    },

    aml: {
      kicker: 'AML · NHI PATHWAY',
      title: '用 fitness / FLT3 / CD33 / response / HSCT 把 AML 給付情境拆開',
      intro: 'AML 的健保條文跨 induction、R/R、maintenance 與 transplant 前後；這張圖把真正會改變申請路徑的條件拉到最上層。',
      alerts: [
        '「Unfit」在此依健保條文明確條件呈現：≥75 歲，或 18–74 歲 ECOG 2–3 且符合指定心、肺或肝功能條件。',
        'Midostaurin 與 quizartinib 都屬新診斷 FLT3-directed 路徑；quizartinib 明確要求 FLT3-ITD，條文並限制與 midostaurin 擇一。',
        '灰色的 AML transformation / exclusion records 不放進臨床路徑，避免把 MDS/MPN 藥物誤讀成 AML 治療。'
      ],
      stages: [
        {
          step: '1', title: '新診斷 AML', subtitle: '先分 intensive chemotherapy eligibility，再看 molecular / CD33',
          lanes: [
            { label: '不適合高強度化療', criterion: '符合健保 age / ECOG / organ criteria', items: ['aml-aza-ven', 'aml-venetoclax-ldac'] },
            { label: 'FLT3 mutation+', criterion: '標準 induction / consolidation 路徑；排除 APL', items: ['aml-midostaurin'] },
            { label: 'FLT3-ITD+', criterion: 'Induction / consolidation；後續可進 maintenance；排除 APL', items: ['aml-quizartinib'] },
            { label: 'CD33+ favorable-risk', criterion: '新診斷原發型 AML；favorable cytogenetic risk；排除 APL', items: ['aml-gemtuzumab'] }
          ]
        },
        {
          step: '2', title: 'Relapsed / refractory', subtitle: '目前主要 curated molecular route',
          lanes: [
            { label: 'FLT3-mutated R/R AML', criterion: '成人、計畫 HSCT；移植前使用', items: ['aml-gilteritinib-pre-hsct'] }
          ]
        },
        {
          step: '3', title: 'Maintenance / transplant 後', subtitle: '依 response、HSCT eligibility 與 MRD 狀態分流',
          lanes: [
            { label: 'CR / CRi，未進 HSCT', criterion: '≥55 歲、指定 cytogenetic risk、且不適合 HSCT', items: ['aml-oral-aza-maint'] },
            { label: 'FLT3-ITD 路徑延續', criterion: 'Quizartinib induction/consolidation 後，符合條件者進單藥 maintenance', items: ['aml-quizartinib'] },
            { label: 'Post-HSCT', criterion: '移植前已使用 gilteritinib，移植後符合 response / MRD 條件', items: ['aml-gilteritinib-post-hsct'] }
          ]
        }
      ]
    }
  };

  const toolbar = document.createElement('div');
  toolbar.id = 'clinicalViewToolbar';
  toolbar.className = 'clinical-view-toolbar';
  toolbar.hidden = true;
  toolbar.innerHTML = `
    <div class="clinical-view-label">
      <strong>檢視方式</strong>
      <span>臨床路徑為健保給付導航，不是 treatment guideline。</span>
    </div>
    <div class="view-switch" role="group" aria-label="切換檢視方式">
      <button type="button" data-clinical-view="map">臨床路徑</button>
      <button type="button" data-clinical-view="list">完整條文</button>
    </div>`;

  const panel = document.createElement('section');
  panel.id = 'clinicalMapPanel';
  panel.className = 'clinical-map-panel';
  panel.hidden = true;

  resultsSection.insertBefore(toolbar, filterBar);
  resultsSection.insertBefore(panel, filterBar);

  function esc(value='') {
    return String(value).replace(/[&<>'"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[m]));
  }

  function currentCancer() {
    return location.hash.match(/^#\/([^/?#]+)$/)?.[1] || null;
  }

  function itemButton(itemId) {
    const x = byId[itemId];
    if (!x) return `<div class="pathway-missing">資料項目 ${esc(itemId)} 未載入</div>`;
    const bio = x.biomarker && x.biomarker !== '—' ? `<span>${esc(x.biomarker)}</span>` : '';
    return `<button class="pathway-drug" type="button" data-map-item="${esc(itemId)}">
      <strong>${esc(x.drug)}</strong>
      <small>${esc(x.regimen)}</small>
      <div class="pathway-drug-meta">${bio}<span>§ ${esc(x.section)}</span>${x.prior_auth ? '<span>事審</span>' : ''}</div>
    </button>`;
  }

  function renderLane(lane) {
    const items = (lane.items || []).map(itemButton).join('');
    return `<article class="pathway-lane${items ? '' : ' info-only'}">
      <div class="pathway-lane-head">
        <h4>${esc(lane.label)}</h4>
        <p>${esc(lane.criterion || '')}</p>
      </div>
      ${items ? `<div class="pathway-drugs">${items}</div>` : '<div class="pathway-gate">符合後再進入下一步 ↓</div>'}
    </article>`;
  }

  function renderMap(cancerId) {
    const cfg = maps[cancerId];
    if (!cfg) return;
    panel.innerHTML = `
      <div class="clinical-map-intro">
        <div>
          <p class="eyebrow">${esc(cfg.kicker)}</p>
          <h3>${esc(cfg.title)}</h3>
          <p>${esc(cfg.intro)}</p>
        </div>
        <span class="pathway-disclaimer">NHI reimbursement map</span>
      </div>
      <div class="pathway-stages">
        ${cfg.stages.map(stage => `
          <section class="pathway-stage">
            <div class="pathway-stage-head">
              <span class="pathway-step">${esc(stage.step)}</span>
              <div><h3>${esc(stage.title)}</h3><p>${esc(stage.subtitle || '')}</p></div>
            </div>
            <div class="pathway-lanes">${stage.lanes.map(renderLane).join('')}</div>
          </section>`).join('')}
      </div>
      <div class="pathway-alerts">
        <strong>給付限制提醒</strong>
        <ul>${cfg.alerts.map(x => `<li>${esc(x)}</li>`).join('')}</ul>
      </div>`;
  }

  function setMode(cancerId, mode) {
    if (!maps[cancerId]) return;
    modeByCancer[cancerId] = mode;
    sync();
  }

  function sync() {
    const cancerId = currentCancer();
    const supported = Boolean(cancerId && maps[cancerId] && !resultsSection.hidden);
    toolbar.hidden = !supported;
    panel.hidden = true;

    if (!supported) {
      filterBar.hidden = false;
      activeFilters.hidden = false;
      results.hidden = false;
      return;
    }

    const mode = modeByCancer[cancerId] || 'map';
    toolbar.querySelectorAll('[data-clinical-view]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.clinicalView === mode);
      btn.setAttribute('aria-pressed', btn.dataset.clinicalView === mode ? 'true' : 'false');
    });

    if (mode === 'map') {
      renderMap(cancerId);
      panel.hidden = false;
      filterBar.hidden = true;
      activeFilters.hidden = true;
      results.hidden = true;
      emptyState.hidden = true;
    } else {
      filterBar.hidden = false;
      activeFilters.hidden = false;
      results.hidden = false;
    }
  }

  toolbar.addEventListener('click', event => {
    const btn = event.target.closest('[data-clinical-view]');
    if (!btn) return;
    const cancerId = currentCancer();
    setMode(cancerId, btn.dataset.clinicalView);
  });

  panel.addEventListener('click', event => {
    const btn = event.target.closest('[data-map-item]');
    if (!btn) return;
    const id = btn.dataset.mapItem;
    const detailButton = [...document.querySelectorAll('[data-detail]')].find(x => x.dataset.detail === id);
    if (detailButton) detailButton.click();
  });

  globalSearch?.addEventListener('input', event => {
    const cancerId = currentCancer();
    if (maps[cancerId] && event.target.value.trim()) {
      modeByCancer[cancerId] = 'list';
      setTimeout(sync, 0);
    }
  });

  const title = document.getElementById('resultTitle');
  const observer = new MutationObserver(() => setTimeout(sync, 0));
  if (title) observer.observe(title, { childList: true, subtree: true });
  observer.observe(resultsSection, { attributes: true, attributeFilter: ['hidden'] });
  window.addEventListener('hashchange', () => setTimeout(sync, 0));

  sync();
})();

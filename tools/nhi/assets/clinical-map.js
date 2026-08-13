(() => {
  'use strict';

  const data = window.NHI_DATA;
  const resultsSection = document.getElementById('resultsSection');
  const filterBar = resultsSection?.querySelector('.filter-bar');
  const activeFilters = document.getElementById('activeFilters');
  const results = document.getElementById('results');
  const emptyState = document.getElementById('emptyState');
  const globalSearch = document.getElementById('globalSearch');
  const changePanel = document.getElementById('changePanel');
  const cancerGrid = document.getElementById('cancerGrid');
  const detailDialog = document.getElementById('detailDialog');
  const dialogContent = document.getElementById('dialogContent');
  if (!data || !resultsSection || !filterBar || !activeFilters || !results || !emptyState || !changePanel || !cancerGrid) return;

  const byId = Object.fromEntries(data.indications.map(x => [x.id, x]));
  const cancerMap = Object.fromEntries(data.cancers.map(x => [x.id, x]));
  const modeByCancer = {};
  const sourcePdf = (window.NHI_CHANGES?.source_url || data.meta.source_url || '');

  const heroEyebrow = document.querySelector('.hero .eyebrow');
  const heroCopy = document.querySelector('.hero-copy');
  if (heroEyebrow) heroEyebrow.textContent = 'ALL CANCERS · V0.9 CLINICAL NAVIGATOR';
  if (heroCopy) heroCopy.textContent = '兩種查法並存：Cancer → setting → line → biomarker → reimbursed regimen；或直接用藥名反查所有健保適應症。所有癌種皆可使用臨床路徑視圖，完整條文仍隨時可切回。';

  function esc(value='') {
    return String(value).replace(/[&<>'"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[m]));
  }
  function norm(value='') { return String(value).toLowerCase().replace(/[‐‑–—]/g,'-').replace(/\s+/g,' ').trim(); }
  function lineGroup(x) { return x.line_group || x.line || ''; }
  function isReimbursed(x) { return !x.status || x.status === '給付'; }
  function currentCancer() { return location.hash.match(/^#\/([^/?#]+)$/)?.[1] || null; }
  function pdfLink(x) { return `${sourcePdf}#page=${Number(x.pdf_page || 1)}`; }
  function unique(arr) { return [...new Set(arr.filter(Boolean))]; }

  const manualMaps = {
    gastric: {
      kicker: 'GASTRIC / GEJ · NHI PATHWAY',
      title: '先分治療情境，再用 HER2 / PD-L1 / CLDN18.2 找健保路徑',
      intro: '只呈現健保給付分岔，不代表 guideline 優先順序。完整 cytotoxic 條文仍可切回「完整條文」查看。',
      alerts: [
        'HER2 non-overexpressing 第一線的 nivolumab 組合與 zolbetuximab 組合，依現行健保規定僅得擇一且失敗後不可互換。',
        'CLDN18.2 路徑須同時確認 HER2 陰性與染色門檻；nivolumab 路徑須確認 PD-L1 CPS 門檻。'
      ],
      stages: [
        { step:'1', title:'根除性手術後', subtitle:'先確認分期與手術條件', lanes:[
          {label:'Adjuvant', criterion:'特定 Stage II–III 胃癌，根除性手術後', items:['gc-s1-adj']}
        ]},
        { step:'2', title:'局部晚期不可切除 / 復發 / 轉移：第一線', subtitle:'HER2 → PD-L1 / CLDN18.2 → chemotherapy backbone', lanes:[
          {label:'HER2 positive', criterion:'IHC 3+ 或 FISH+', items:['gc-trastuzumab']},
          {label:'HER2 non-overexpressed + PD-L1', criterion:'PD-L1 CPS ≥5', items:['gc-nivo-1l']},
          {label:'HER2 negative + CLDN18.2', criterion:'CLDN18.2 ≥75% tumor cells，中至強染色', items:['gc-zolbetuximab']},
          {label:'Chemotherapy backbone', criterion:'不依賴特定 biomarker', items:['gc-capecitabine-platinum']}
        ]},
        { step:'3', title:'後線', subtitle:'健保條文中的 later-line 與 cytotoxic option', lanes:[
          {label:'≥3L', criterion:'先前至少 2 種治療；適合者應包含 HER2 targeting', items:['gc-lonsurf']},
          {label:'其他 cytotoxic option', criterion:'條文未固定特定線別', items:['gc-docetaxel']}
        ]}
      ]
    },
    hcc: {
      kicker: 'HCC · NHI PATHWAY',
      title: '先確認 Child-Pugh A 與 advanced HCC 條件，再看 1L 與 post-sorafenib',
      intro: '把 predecessor restriction 拉到最上層，避免把 regorafenib / ramucirumab 誤讀成所有第一線失敗後都能接。',
      alerts: [
        'Sorafenib、lenvatinib、atezolizumab+bevacizumab、durvalumab+tremelimumab 現行一線給付僅得擇一，原則上不得互換。',
        'Regorafenib 與 ramucirumab 都是 post-sorafenib；ramucirumab 另要求 AFP ≥400 ng/mL。',
        'Atezo+bev 或 durva+treme 失敗後，現行條文明載不得再申請 regorafenib 或 ramucirumab。'
      ],
      stages: [
        { step:'0', title:'共同門檻', subtitle:'Advanced HCC reimbursement gate', lanes:[
          {label:'Eligibility', criterion:'Child-Pugh A，且符合肝外轉移 / 大血管侵犯 / 條文定義 TACE failure 等條件之一', items:[]}
        ]},
        { step:'1', title:'第一線：四選一', subtitle:'顯示健保可申請路徑，不做療效排序', lanes:[
          {label:'TKI', criterion:'Child-Pugh A advanced HCC', items:['hcc-sorafenib','hcc-lenvatinib']},
          {label:'ICI + anti-VEGF', criterion:'未曾接受全身性治療；不需 PD-L1 report', items:['hcc-atezo-bev']},
          {label:'Dual immunotherapy', criterion:'未曾接受全身性治療；不需 PD-L1 report', items:['hcc-durva-treme']}
        ]},
        { step:'2', title:'Sorafenib failure 後', subtitle:'前一線藥物是健保條文核心條件', lanes:[
          {label:'Post-sorafenib', criterion:'Child-Pugh A；sorafenib failure', items:['hcc-regorafenib']},
          {label:'Post-sorafenib + AFP high', criterion:'Child-Pugh A；sorafenib failure；AFP ≥400 ng/mL', items:['hcc-ramucirumab']}
        ]}
      ]
    },
    aml: {
      kicker: 'AML · NHI PATHWAY',
      title: '用 fitness / FLT3 / CD33 / response / HSCT 拆開 AML 給付情境',
      intro: 'AML 條文跨 induction、R/R、maintenance 與 transplant 前後；路徑只放真正 AML 給付，不把 transformation 提示混進治療選項。',
      alerts: [
        'Unfit eligibility 仍應回到個別條文確認年齡、ECOG 與器官功能條件。',
        'Midostaurin 與 quizartinib 都屬 FLT3-directed 路徑；quizartinib 明確要求 FLT3-ITD，且與 midostaurin 有擇一限制。',
        'MDS/MPN 條文中僅提到 AML transformation 的 record 不進入治療路徑。'
      ],
      stages: [
        { step:'1', title:'新診斷 AML', subtitle:'先分 intensive chemotherapy eligibility，再看 molecular / CD33', lanes:[
          {label:'不適合高強度化療', criterion:'符合健保 age / ECOG / organ criteria', items:['aml-aza-ven','aml-venetoclax-ldac']},
          {label:'FLT3 mutation+', criterion:'標準 induction / consolidation；排除 APL', items:['aml-midostaurin']},
          {label:'FLT3-ITD+', criterion:'Induction / consolidation → maintenance；排除 APL', items:['aml-quizartinib']},
          {label:'CD33+ favorable-risk', criterion:'新診斷原發型 AML；排除 APL', items:['aml-gemtuzumab']}
        ]},
        { step:'2', title:'Relapsed / refractory', subtitle:'目前主要 molecular reimbursement route', lanes:[
          {label:'FLT3-mutated R/R AML', criterion:'成人、計畫 HSCT；移植前使用', items:['aml-gilteritinib-pre-hsct']}
        ]},
        { step:'3', title:'Maintenance / transplant 後', subtitle:'依 response、HSCT eligibility 與 MRD 分流', lanes:[
          {label:'CR / CRi，未進 HSCT', criterion:'符合年齡、cytogenetic risk 與 HSCT eligibility 條件', items:['aml-oral-aza-maint']},
          {label:'FLT3-ITD 路徑延續', criterion:'Quizartinib induction/consolidation 後符合條件者', items:['aml-quizartinib']},
          {label:'Post-HSCT', criterion:'移植前已使用 gilteritinib，移植後符合 response / MRD 條件', items:['aml-gilteritinib-post-hsct']}
        ]}
      ]
    }
  };

  const stageOrder = [
    ['術前 / 前導', /術前|前導|neoadjuvant|induction|誘導/i],
    ['術後 / 輔助', /術後|輔助|adjuvant/i],
    ['第一線 / 初始治療', /(^|\b)1l\b|第一線|初診|新診斷|first.?line/i],
    ['第二線', /(^|\b)2l\b|第二線|second.?line/i],
    ['後線 / 復發難治', /r\/r|復發|難治|頑固|後線|≥3l|3l|third.?line|later.?line|failure|失敗/i],
    ['維持治療', /維持|maintenance/i],
    ['其他給付情境', /.*/]
  ];

  function stageLabelFor(x, cancerId) {
    const text = norm([x.setting,x.line,lineGroup(x),x.regimen,(x.tags||[]).join(' ')].join(' '));
    if (cancerId === 'prostate') {
      if (/mcspc|mhs?pc|hormone.?sensitive|荷爾蒙敏感/.test(text)) return 'mCSPC / hormone-sensitive';
      if (/nmcrpc|non.?metastatic.*crpc|非轉移.*去勢抗性/.test(text)) return 'nmCRPC';
      if (/mcrpc|metastatic.*crpc|轉移.*去勢抗性/.test(text)) return 'mCRPC';
    }
    if (cancerId === 'lung') {
      if (/小細胞|sclc/.test(text)) return 'Small-cell lung cancer';
      if (/術前|neoadjuvant|鞏固|consolidation/.test(text)) return 'Early / locally advanced NSCLC';
      if (/egfr|alk|ros.?1|braf|met |ntrk|ret|her2/.test(norm(x.biomarker||''))) return 'NSCLC · driver-directed';
      if (/非小細胞|nsclc|肺腺|鱗狀/.test(text)) return 'NSCLC · non-driver / systemic';
    }
    if (cancerId === 'breast') {
      const bio = norm(x.biomarker||'');
      if (/術前|術後|早期|adjuvant|neoadjuvant/.test(text)) return 'Early breast cancer';
      if (/her2/.test(bio)) return 'HER2-directed';
      if (/triple|tnbc|三陰/.test(text + ' ' + bio)) return 'TNBC';
      if (/hr|er\+|pr\+|hormone/.test(text + ' ' + bio)) return 'HR+ / HER2−';
    }
    if (cancerId === 'urothelial') {
      if (/維持|maintenance/.test(text)) return 'Platinum response → maintenance';
      if (/1l|第一線/.test(text)) return 'First-line';
      if (/2l|第二線/.test(text)) return 'Second-line';
      if (/3l|第三線|後線/.test(text)) return 'Later-line / ADC';
    }
    for (const [label, re] of stageOrder) if (re.test(text)) return label;
    return '其他給付情境';
  }

  function laneKeyFor(x) {
    const bio = x.biomarker && x.biomarker !== '—' ? x.biomarker : '';
    if (bio) return bio;
    return x.setting || lineGroup(x) || '一般條件';
  }

  function buildGenericMap(cancerId) {
    const cancer = cancerMap[cancerId];
    const all = data.indications.filter(x => x.cancer === cancerId);
    const active = all.filter(isReimbursed);
    const exclusions = all.filter(x => !isReimbursed(x));
    if (!active.length) {
      return {
        kicker: `${cancer?.en || cancerId} · NHI PATHWAY`,
        title: `${cancer?.name || cancerId}：目前沒有已人工整理的健保給付節點`,
        intro: '此癌種仍保留在每週第九節 coverage audit；若未來新增條文或 scanner 偵測到候選，會進入 review queue。',
        alerts: exclusions.length ? [`目前有 ${exclusions.length} 筆非適用 / 排除提示，可切回「完整條文」查看。`] : ['目前第九節尚無已 curated 的給付 record。'],
        stages: [{step:'—', title:'持續監測', subtitle:'Weekly NHI coverage audit', lanes:[{label:'尚無 active curated record', criterion:'不以空白頁冒充無給付；仍請以健保署最新原文核對。', items:[]}]}]
      };
    }

    const grouped = new Map();
    active.forEach(x => {
      const stage = stageLabelFor(x, cancerId);
      if (!grouped.has(stage)) grouped.set(stage, []);
      grouped.get(stage).push(x);
    });

    const preferredOrder = unique([
      ...stageOrder.map(x=>x[0]),
      'Early breast cancer','HER2-directed','TNBC','HR+ / HER2−',
      'Early / locally advanced NSCLC','NSCLC · driver-directed','NSCLC · non-driver / systemic','Small-cell lung cancer',
      'mCSPC / hormone-sensitive','nmCRPC','mCRPC',
      'First-line','Platinum response → maintenance','Second-line','Later-line / ADC'
    ]);
    const labels = [...grouped.keys()].sort((a,b) => {
      const ia = preferredOrder.indexOf(a), ib = preferredOrder.indexOf(b);
      return (ia < 0 ? 999 : ia) - (ib < 0 ? 999 : ib) || a.localeCompare(b,'zh-Hant');
    });

    const stages = labels.map((label, idx) => {
      const records = grouped.get(label);
      const lanesMap = new Map();
      records.forEach(x => {
        const key = laneKeyFor(x);
        if (!lanesMap.has(key)) lanesMap.set(key, []);
        lanesMap.get(key).push(x.id);
      });
      const lanes = [...lanesMap.entries()].map(([key, ids]) => ({
        label: key.length > 52 ? `${key.slice(0,49)}…` : key,
        criterion: ids.length === 1 ? (byId[ids[0]]?.setting || '') : `${ids.length} 個給付選項；點藥物看完整條件`,
        items: ids
      }));
      return {step:String(idx+1), title:label, subtitle:`${records.length} 個 active reimbursement record`, lanes};
    });

    const alerts = [
      '此路徑由已人工核對的 curated records 自動分組；只表示健保給付結構，不代表 treatment guideline 或療效排序。',
      '同一藥物可能因不同 setting / line / biomarker 形成多個節點；事前審查時請點入摘要或官方 PDF 核對完整文字。'
    ];
    if (exclusions.length) alerts.push(`${exclusions.length} 筆「非適用 / 提示」未放進 active pathway，可在「完整條文」看到。`);
    return {
      kicker: `${cancer?.en || cancerId} · NHI PATHWAY`,
      title: `${cancer?.name || cancerId}：依治療階段與 biomarker 瀏覽健保給付`,
      intro: `目前共 ${active.length} 個 active curated reimbursement record。新增或修訂 record 後，這張路徑會跟著資料自動重建。`,
      alerts,
      stages
    };
  }

  function mapFor(cancerId) { return manualMaps[cancerId] || buildGenericMap(cancerId); }

  const toolbar = document.createElement('div');
  toolbar.id = 'clinicalViewToolbar';
  toolbar.className = 'clinical-view-toolbar';
  toolbar.hidden = true;
  toolbar.innerHTML = `
    <div class="clinical-view-label"><strong>檢視方式</strong><span>臨床路徑 = reimbursement navigation，不是 treatment guideline。</span></div>
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

  function itemButton(itemId) {
    const x = byId[itemId];
    if (!x) return `<div class="pathway-missing">資料項目 ${esc(itemId)} 未載入</div>`;
    const bio = x.biomarker && x.biomarker !== '—' ? `<span>${esc(x.biomarker)}</span>` : '';
    return `<button class="pathway-drug" type="button" data-map-item="${esc(itemId)}">
      <strong>${esc(x.drug)}</strong><small>${esc(x.regimen)}</small>
      <div class="pathway-drug-meta"><span>${esc(lineGroup(x))}</span>${bio}<span>§ ${esc(x.section)}</span>${x.prior_auth ? '<span>事審</span>' : ''}</div>
    </button>`;
  }
  function renderLane(lane) {
    const items = (lane.items || []).map(itemButton).join('');
    return `<article class="pathway-lane${items ? '' : ' info-only'}"><div class="pathway-lane-head"><h4>${esc(lane.label)}</h4><p>${esc(lane.criterion || '')}</p></div>${items ? `<div class="pathway-drugs">${items}</div>` : '<div class="pathway-gate">持續監測 / 符合後再進下一步</div>'}</article>`;
  }
  function renderMap(cancerId) {
    const cfg = mapFor(cancerId);
    if (!cfg) return;
    panel.innerHTML = `
      <div class="clinical-map-intro"><div><p class="eyebrow">${esc(cfg.kicker)}</p><h3>${esc(cfg.title)}</h3><p>${esc(cfg.intro)}</p></div><span class="pathway-disclaimer">NHI reimbursement map</span></div>
      <div class="pathway-stages">${cfg.stages.map(stage => `<section class="pathway-stage"><div class="pathway-stage-head"><span class="pathway-step">${esc(stage.step)}</span><div><h3>${esc(stage.title)}</h3><p>${esc(stage.subtitle || '')}</p></div></div><div class="pathway-lanes">${stage.lanes.map(renderLane).join('')}</div></section>`).join('')}</div>
      <div class="pathway-alerts"><strong>給付限制提醒</strong><ul>${cfg.alerts.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>`;
  }
  function syncClinicalMap() {
    const cancerId = currentCancer();
    const supported = Boolean(cancerId && cancerMap[cancerId] && !resultsSection.hidden && document.body.dataset.lookupMode !== 'drug');
    toolbar.hidden = !supported;
    panel.hidden = true;
    if (!supported) {
      if (document.body.dataset.lookupMode !== 'drug') {
        filterBar.hidden = false; activeFilters.hidden = false; results.hidden = false;
      }
      return;
    }
    const mode = modeByCancer[cancerId] || 'map';
    toolbar.querySelectorAll('[data-clinical-view]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.clinicalView === mode);
      btn.setAttribute('aria-pressed', btn.dataset.clinicalView === mode ? 'true' : 'false');
    });
    if (mode === 'map') {
      renderMap(cancerId); panel.hidden = false; filterBar.hidden = true; activeFilters.hidden = true; results.hidden = true; emptyState.hidden = true;
    } else {
      panel.hidden = true; filterBar.hidden = false; activeFilters.hidden = false; results.hidden = false;
    }
  }
  toolbar.addEventListener('click', e => {
    const btn = e.target.closest('[data-clinical-view]');
    if (!btn) return;
    const cancerId = currentCancer();
    if (!cancerId) return;
    modeByCancer[cancerId] = btn.dataset.clinicalView;
    syncClinicalMap();
  });
  panel.addEventListener('click', e => {
    const btn = e.target.closest('[data-map-item]');
    if (!btn) return;
    const listButton = [...document.querySelectorAll('[data-detail]')].find(x => x.dataset.detail === btn.dataset.mapItem);
    if (listButton) listButton.click();
  });

  // -------- Drug-centric reimbursement lookup --------
  const brandAliases = {
    keytruda:'pembrolizumab', opdivo:'nivolumab', tecentriq:'atezolizumab', bavencio:'avelumab', yervoy:'ipilimumab', imfinzi:'durvalumab', imjudo:'tremelimumab', libtayo:'cemiplimab', jemperli:'dostarlimab',
    herceptin:'trastuzumab', perjeta:'pertuzumab', phesgo:'pertuzumab trastuzumab', kadcyla:'trastuzumab emtansine', enhertu:'trastuzumab deruxtecan', avastin:'bevacizumab', erbitux:'cetuximab', vectibix:'panitumumab', cyramza:'ramucirumab',
    nexavar:'sorafenib', lenvima:'lenvatinib', stivarga:'regorafenib', xeloda:'capecitabine', abraxane:'nab-paclitaxel paclitaxel', onivyde:'irinotecan liposome', lonsurf:'trifluridine tipiracil', vitrakvi:'larotrectinib', rozlytrek:'entrectinib',
    tagrisso:'osimertinib', iressa:'gefitinib', tarceva:'erlotinib', gilotrif:'afatinib', vizimpro:'dacomitinib', xalkori:'crizotinib', zykadia:'ceritinib', alecensa:'alectinib', alunbrig:'brigatinib', lorbrena:'lorlatinib', rybrevant:'amivantamab',
    zytiga:'abiraterone', xtandi:'enzalutamide', erleada:'apalutamide', nubeqa:'darolutamide', lynparza:'olaparib', zejula:'niraparib', padcev:'enfortumab vedotin',
    gleevec:'imatinib', sprycel:'dasatinib', tasigna:'nilotinib', iclusig:'ponatinib', scemblix:'asciminib', blincyto:'blinatumomab', besponsa:'inotuzumab', xospata:'gilteritinib', rydapt:'midostaurin',
    darzalex:'daratumumab', kyprolis:'carfilzomib', ninlaro:'ixazomib', pomalyst:'pomalidomide', revlimid:'lenalidomide', velcade:'bortezomib', teclistamab:'teclistamab', elrexfio:'elranatamab'
  };

  const cancerBrowseSection = cancerGrid.closest('.section-block');
  const lookupBar = document.createElement('section');
  lookupBar.className = 'lookup-mode-bar';
  lookupBar.innerHTML = `
    <div><p class="eyebrow">TWO-WAY LOOKUP</p><strong>你要從哪一邊開始？</strong><span>病人導向用癌種；事審 / 查藥導向直接用藥名。</span></div>
    <div class="lookup-switch" role="group" aria-label="查詢模式">
      <button type="button" class="active" data-lookup-mode="cancer">依癌種 / 臨床路徑</button>
      <button type="button" data-lookup-mode="drug">依藥物查所有適應症</button>
    </div>`;
  changePanel.insertAdjacentElement('afterend', lookupBar);

  const drugSection = document.createElement('section');
  drugSection.id = 'drugLookupSection';
  drugSection.className = 'section-block drug-lookup-section';
  drugSection.hidden = true;
  drugSection.innerHTML = `
    <div class="section-heading drug-heading"><div><p class="eyebrow">SEARCH BY DRUG</p><h2>用藥名反查健保適應症</h2><p class="muted">可輸入 generic name；常用商品名亦支援別名轉換。結果會跨癌種列出 setting、line、biomarker、事審與 §9.x。</p></div><div id="drugLookupCount" class="result-count"></div></div>
    <div class="drug-search-box"><input id="drugLookupInput" type="search" autocomplete="off" placeholder="例如：nivolumab、bevacizumab、Keytruda、Tagrisso…"><button id="clearDrugLookup" type="button" class="ghost-button">清除</button></div>
    <div class="drug-filter-row"><select id="drugCancerFilter"><option value="">所有癌種</option></select><select id="drugAuthFilter"><option value="">事審不限</option><option value="yes">需事前審查</option><option value="no">未標示事審</option></select><label class="drug-hint-toggle"><input id="includeDrugHints" type="checkbox"> 包含「非適用 / 提示」</label></div>
    <div id="drugAliasNotice" class="drug-alias-notice" hidden></div>
    <div id="drugDirectory" class="drug-directory"></div>
    <div id="drugLookupResults" class="drug-lookup-results"></div>`;
  cancerBrowseSection.insertAdjacentElement('afterend', drugSection);

  const drugInput = document.getElementById('drugLookupInput');
  const drugCancerFilter = document.getElementById('drugCancerFilter');
  const drugAuthFilter = document.getElementById('drugAuthFilter');
  const includeDrugHints = document.getElementById('includeDrugHints');
  const drugDirectory = document.getElementById('drugDirectory');
  const drugResults = document.getElementById('drugLookupResults');
  const drugCount = document.getElementById('drugLookupCount');
  const aliasNotice = document.getElementById('drugAliasNotice');
  let previousResultsHidden = true;

  data.cancers.filter(c => data.indications.some(x => x.cancer === c.id)).forEach(c => {
    const o = document.createElement('option'); o.value = c.id; o.textContent = c.name; drugCancerFilter.appendChild(o);
  });

  function aliasExpansion(q) {
    const n = norm(q);
    if (!n) return {terms:[], alias:null};
    const terms = [n];
    let hit = null;
    for (const [brand,generic] of Object.entries(brandAliases)) {
      if (brand.includes(n) || n.includes(brand)) { terms.push(norm(generic)); hit = `${brand} → ${generic}`; }
    }
    return {terms:unique(terms), alias:hit};
  }
  function drugHay(x) {
    const c = cancerMap[x.cancer];
    return norm([x.drug,x.regimen,x.setting,x.line,lineGroup(x),x.biomarker,x.summary,x.section,(x.tags||[]).join(' '),c?.name,c?.en].join(' '));
  }
  function drugFilteredRecords() {
    const {terms, alias} = aliasExpansion(drugInput.value);
    aliasNotice.hidden = !alias;
    if (alias) aliasNotice.textContent = `商品名別名：${alias}`;
    return data.indications.filter(x => {
      if (!includeDrugHints.checked && !isReimbursed(x)) return false;
      if (drugCancerFilter.value && x.cancer !== drugCancerFilter.value) return false;
      if (drugAuthFilter.value === 'yes' && !x.prior_auth) return false;
      if (drugAuthFilter.value === 'no' && x.prior_auth) return false;
      if (terms.length && !terms.some(t => drugHay(x).includes(t))) return false;
      return true;
    });
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
  function drugHitHtml(x) {
    const c = cancerMap[x.cancer];
    const bio = x.biomarker && x.biomarker !== '—' ? `<span class="badge bio">${esc(x.biomarker)}</span>` : '';
    return `<article class="drug-hit"><div class="drug-hit-main"><div class="drug-hit-kicker"><span>${esc(c?.name || x.cancer)}</span><span>${esc(lineGroup(x))}</span></div><h4>${esc(x.regimen)}</h4><p>${esc(x.setting)}</p><div class="badges">${x.status && x.status !== '給付' ? `<span class="badge">${esc(x.status)}</span>` : ''}${x.prior_auth ? '<span class="badge auth">事前審查</span>' : ''}${bio}<span class="badge">§ ${esc(x.section)}</span></div></div><div class="drug-hit-actions"><button type="button" class="action-button primary" data-drug-detail="${esc(x.id)}">摘要</button><a class="action-button" href="${esc(pdfLink(x))}" target="_blank" rel="noopener">官方 PDF ↗</a></div></article>`;
  }
  function renderDrugDirectory() {
    if (drugInput.value.trim()) { drugDirectory.hidden = true; return; }
    const active = data.indications.filter(isReimbursed);
    const groups = groupByDrug(active);
    drugDirectory.hidden = false;
    drugDirectory.innerHTML = `<div class="drug-directory-head"><strong>${groups.length} 個藥物 / 組合名稱</strong><span>點一下直接反查跨癌種適應症</span></div><div class="drug-chip-grid">${groups.map(([name,rows]) => `<button type="button" data-drug-chip="${esc(name)}"><strong>${esc(name)}</strong><span>${rows.length} 筆</span></button>`).join('')}</div>`;
  }
  function renderDrugLookup() {
    const records = drugFilteredRecords();
    const groups = groupByDrug(records);
    const actual = records.filter(isReimbursed).length;
    drugCount.innerHTML = `<b>${actual}</b><span> 給付情境</span>`;
    renderDrugDirectory();
    if (!drugInput.value.trim()) {
      drugResults.innerHTML = '<div class="drug-lookup-empty">輸入藥名或點上方藥物名稱，即可反查所有癌種的健保適應症。</div>';
      return;
    }
    drugResults.innerHTML = groups.length ? groups.map(([name,rows]) => `<section class="drug-group"><div class="drug-group-head"><h3>${esc(name)}</h3><span>${rows.filter(isReimbursed).length} 個 active reimbursement record${rows.length !== rows.filter(isReimbursed).length ? ` · ${rows.length-rows.filter(isReimbursed).length} 個提示` : ''}</span></div><div class="drug-group-list">${rows.map(drugHitHtml).join('')}</div></section>`).join('') : '<div class="drug-lookup-empty"><strong>找不到符合的 curated record</strong><span>可以改用 generic name，或切回癌種模式查看完整條文。</span></div>';
  }

  function showDrugDetail(id) {
    const x = byId[id]; if (!x || !detailDialog || !dialogContent) return;
    const c = cancerMap[x.cancer];
    dialogContent.innerHTML = `<p class="eyebrow">${esc(c?.name || x.cancer)} · § ${esc(x.section)}</p><h3 class="dialog-title">${esc(x.drug)}</h3><div class="regimen">${esc(x.regimen)}</div><p class="dialog-summary">${esc(x.summary)}</p><dl class="detail-table"><dt>治療情境</dt><dd>${esc(x.setting)}</dd><dt>給付狀態</dt><dd>${esc(x.status || '給付')}</dd><dt>治療線別</dt><dd>${esc(lineGroup(x))}${x.line && x.line !== lineGroup(x) ? `（${esc(x.line)}）` : ''}</dd><dt>Biomarker</dt><dd>${esc(x.biomarker)}</dd><dt>事前審查</dt><dd>${x.prior_auth ? '需要' : '條目未標為需要'}</dd><dt>審查 / 追蹤</dt><dd>${esc(x.review)}</dd><dt>療程限制</dt><dd>${esc(x.duration)}</dd><dt>條文生效</dt><dd>${esc(x.effective)}</dd></dl><div class="dialog-actions"><a class="action-button primary" href="${esc(pdfLink(x))}" target="_blank" rel="noopener">開啟健保署原始 PDF ↗</a><button class="action-button" value="close">關閉</button></div>`;
    detailDialog.showModal();
  }

  function setLookupMode(mode) {
    document.body.dataset.lookupMode = mode;
    lookupBar.querySelectorAll('[data-lookup-mode]').forEach(btn => btn.classList.toggle('active', btn.dataset.lookupMode === mode));
    if (mode === 'drug') {
      previousResultsHidden = resultsSection.hidden;
      cancerBrowseSection.hidden = true;
      resultsSection.hidden = true;
      drugSection.hidden = false;
      renderDrugLookup();
      setTimeout(() => drugInput.focus({preventScroll:true}), 0);
    } else {
      cancerBrowseSection.hidden = false;
      drugSection.hidden = true;
      resultsSection.hidden = previousResultsHidden;
      syncClinicalMap();
    }
  }
  lookupBar.addEventListener('click', e => { const btn = e.target.closest('[data-lookup-mode]'); if (btn) setLookupMode(btn.dataset.lookupMode); });
  drugInput.addEventListener('input', renderDrugLookup);
  drugCancerFilter.addEventListener('change', renderDrugLookup);
  drugAuthFilter.addEventListener('change', renderDrugLookup);
  includeDrugHints.addEventListener('change', renderDrugLookup);
  document.getElementById('clearDrugLookup').addEventListener('click', () => { drugInput.value=''; drugCancerFilter.value=''; drugAuthFilter.value=''; includeDrugHints.checked=false; renderDrugLookup(); drugInput.focus(); });
  drugDirectory.addEventListener('click', e => { const btn=e.target.closest('[data-drug-chip]'); if (!btn) return; drugInput.value=btn.dataset.drugChip; renderDrugLookup(); drugInput.focus(); });
  drugResults.addEventListener('click', e => { const btn=e.target.closest('[data-drug-detail]'); if (btn) showDrugDetail(btn.dataset.drugDetail); });

  // Keep pathway UI in sync with the original app, which uses history.replaceState.
  const resultTitle = document.getElementById('resultTitle');
  if (resultTitle) new MutationObserver(() => setTimeout(syncClinicalMap,0)).observe(resultTitle,{childList:true,subtree:true});
  new MutationObserver(() => setTimeout(syncClinicalMap,0)).observe(resultsSection,{attributes:true,attributeFilter:['hidden']});
  document.addEventListener('click', e => { if (e.target.closest('[data-cancer],#backBtn,#showAllBtn')) setTimeout(syncClinicalMap,0); });
  window.addEventListener('hashchange', syncClinicalMap);

  document.body.dataset.lookupMode = 'cancer';
  renderDrugDirectory();
  syncClinicalMap();
})();
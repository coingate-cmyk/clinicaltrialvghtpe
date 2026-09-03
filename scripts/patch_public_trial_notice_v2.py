from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'index.html'
PUBLIC = ROOT / 'public-trials.html'
FALLBACK = ROOT / 'public_trials.json'

DEFAULT_REG = 'https://www6.vghtpe.gov.tw/reg/'
VISIBLE_STATUSES = {'收案中','需問名額','暫停收案','尚未開放','預備中'}


def infer_departments_from_types(types):
    text = ' '.join(types or []).lower()
    out = []
    def add(x):
        if x not in out:
            out.append(x)
    if re.search(r'乳|breast', text, re.I):
        add('乳房外科'); add('腫瘤醫學部')
    if re.search(r'肺|lung|胸膜|mesothelioma', text, re.I):
        add('胸腔部'); add('腫瘤醫學部')
    if re.search(r'攝護|前列腺|prostate|泌尿|膀胱|bladder|尿路|urothel|腎癌|kidney|renal|睪丸|testis|陰莖|penis', text, re.I):
        add('泌尿部'); add('腫瘤醫學部')
    if re.search(r'胃|食道|胰|膽|肝|大腸|結腸|直腸|腸癌|gastric|stomach|esoph|pancre|biliary|cholangi|hcc|liver|colon|rect|gastro', text, re.I):
        add('腫瘤醫學部'); add('胃腸肝膽科')
    if re.search(r'頭頸|口腔|鼻咽|咽|喉|salivary|orophary|nasophary|laryn', text, re.I):
        add('耳鼻喉頭頸部'); add('腫瘤醫學部')
    if re.search(r'子宮|卵巢|婦|cervix|uter|ovary|vulva|vagina', text, re.I):
        add('婦女醫學部'); add('腫瘤醫學部')
    if re.search(r'淋巴|白血|骨髓|myeloma|lymph|leuk|mds|mpn', text, re.I):
        add('血液科')
    if not out:
        add('相關專科門診')
    return out


def patch_index(text):
    if 'PUBLIC_NOTICE_SCHEMA_VERSION' in text:
        return text

    old_default = "        inclusion: '',\n        exclusion: ''\n    });"
    new_default = "        inclusion: '',\n        exclusion: '',\n        publicDisclosureApproved: false,\n        publicDepartments: ''\n    });"
    if old_default not in text:
        raise SystemExit('TrialForm default anchor not found')
    text = text.replace(old_default, new_default, 1)

    exclusion_anchor = """                e('div', null,\n                    e('label', {className: 'block text-sm font-semibold text-slate-700 mb-1'}, '排除條件'),\n                    e('textarea', {\n                        value: form.exclusion,\n                        onChange: (ev) => update('exclusion', ev.target.value),\n                        rows: 2,\n                        placeholder: '請輸入排除條件...',\n                        className: 'w-full px-3 py-2 border-2 border-slate-300 rounded-lg focus:border-blue-500 focus:outline-none'\n                    })\n                ),\n                e('div', null,\n                    e('label', {className: 'block text-sm font-semibold text-slate-700 mb-1'}, '附註 / comments'),"""
    public_settings = """                e('div', null,\n                    e('label', {className: 'block text-sm font-semibold text-slate-700 mb-1'}, '排除條件'),\n                    e('textarea', {\n                        value: form.exclusion,\n                        onChange: (ev) => update('exclusion', ev.target.value),\n                        rows: 2,\n                        placeholder: '請輸入排除條件...',\n                        className: 'w-full px-3 py-2 border-2 border-slate-300 rounded-lg focus:border-blue-500 focus:outline-none'\n                    })\n                ),\n                e('div', {className: 'sm:col-span-2 rounded-xl border border-sky-200 bg-sky-50 p-4'},\n                    e('div', {className: 'flex items-start gap-3'},\n                        e('input', {\n                            id: 'publicDisclosureApproved',\n                            type: 'checkbox',\n                            checked: form.publicDisclosureApproved === true,\n                            onChange: (ev) => update('publicDisclosureApproved', ev.target.checked),\n                            className: 'mt-1 h-4 w-4'\n                        }),\n                        e('label', {htmlFor: 'publicDisclosureApproved', className: 'text-sm text-sky-950'},\n                            e('div', {className: 'font-bold'}, '可刊登於民眾版臨床試驗資訊公告'),\n                            e('div', {className: 'mt-1 text-xs leading-relaxed'}, '勾選代表已確認此案可公開；民眾版只輸出疾病/癌種、試驗名稱、Phase、治療線別、招募狀態、建議科別與掛號入口。Inclusion/Exclusion、PI/Sub-I、CRC、電話、Email 與內部備註永不輸出。')\n                        )\n                    ),\n                    e('label', {className: 'block text-sm font-semibold text-slate-700 mt-3 mb-1'}, '民眾版建議科別（選填）'),\n                    e('input', {\n                        type: 'text',\n                        value: form.publicDepartments || '',\n                        onChange: (ev) => update('publicDepartments', ev.target.value),\n                        placeholder: '例如：腫瘤醫學部、胸腔部；留空則依癌種自動建議',\n                        className: 'w-full px-3 py-2 border-2 border-sky-200 rounded-lg bg-white focus:border-sky-500 focus:outline-none'\n                    })\n                ),\n                e('div', null,\n                    e('label', {className: 'block text-sm font-semibold text-slate-700 mb-1'}, '附註 / comments'),"""
    if exclusion_anchor not in text:
        raise SystemExit('TrialForm exclusion UI anchor not found')
    text = text.replace(exclusion_anchor, public_settings, 1)

    helper = r"""const PUBLIC_NOTICE_SCHEMA_VERSION = 'public-trials-v2.0-20260904';
const PUBLIC_DEFAULT_REGISTRATION_URL = 'https://www6.vghtpe.gov.tw/reg/';
const PUBLIC_VISIBLE_STATUSES = new Set(['收案中','需問名額','暫停收案','尚未開放','預備中']);
const PUBLIC_FORBIDDEN_KEYS = new Set(['inclusion','exclusion','pi','subI','sub_i','investigator','publicPhysicians','nurse','crc','phone','email','lineId','comments','subjects','sponsor','targetNum','enrolled','monthSigned','monthEnrolled']);
const PUBLIC_TRIAL_ALLOWED_KEYS = new Set(['code','studyTitle','phase','publicStatus','statusClass','cancerTypes','departments','registrationUrl','updatedAt']);

const normalizeDepartmentList = (value) => {
    const raw = Array.isArray(value) ? value : String(value || '').split(/[、,，;/；\n]+/);
    return [...new Set(raw.map(normalizePublicText).filter(Boolean))];
};

const getSuggestedPublicDepartments = (trial) => {
    const explicit = normalizeDepartmentList(trial && trial.publicDepartments);
    if (explicit.length) return explicit;
    const cancerTypes = getPublicCancerTypes(trial || []);
    const haystack = cancerTypes.map(ct => ct.type).join(' ').toLowerCase();
    const out = [];
    const add = (x) => { if (x && !out.includes(x)) out.push(x); };
    if (/乳|breast/i.test(haystack)) { add('乳房外科'); add('腫瘤醫學部'); }
    if (/肺|lung|胸膜|mesothelioma/i.test(haystack)) { add('胸腔部'); add('腫瘤醫學部'); }
    if (/攝護|前列腺|prostate|泌尿|膀胱|bladder|尿路|urothel|腎癌|kidney|renal|睪丸|testis|陰莖|penis/i.test(haystack)) { add('泌尿部'); add('腫瘤醫學部'); }
    if (/胃|食道|胰|膽|肝|大腸|結腸|直腸|腸癌|gastric|stomach|esoph|pancre|biliary|cholangi|hcc|liver|colon|rect|gastro/i.test(haystack)) { add('腫瘤醫學部'); add('胃腸肝膽科'); }
    if (/頭頸|口腔|鼻咽|咽|喉|salivary|orophary|nasophary|laryn/i.test(haystack)) { add('耳鼻喉頭頸部'); add('腫瘤醫學部'); }
    if (/子宮|卵巢|婦|cervix|uter|ovary|vulva|vagina/i.test(haystack)) { add('婦女醫學部'); add('腫瘤醫學部'); }
    if (/淋巴|白血|骨髓|myeloma|lymph|leuk|mds|mpn/i.test(haystack)) add('血液科');
    if (!out.length) add('相關專科門診');
    return out;
};

const assertPublicDatasetSafe = (payload) => {
    const trials = Array.isArray(payload && payload.trials) ? payload.trials : [];
    trials.forEach((trial, index) => {
        Object.keys(trial || {}).forEach(key => {
            if (PUBLIC_FORBIDDEN_KEYS.has(key)) throw new Error(`公開資料安全檢查失敗：trial[${index}] 禁止欄位 ${key}`);
            if (!PUBLIC_TRIAL_ALLOWED_KEYS.has(key)) throw new Error(`公開資料 schema 檢查失敗：trial[${index}] 未核准欄位 ${key}`);
        });
    });
    return payload;
};

const shouldPublishPublicTrial = (trial, publicStatus) => !!(
    trial && trial.publicDisclosureApproved === true && !trial.isArchived && PUBLIC_VISIBLE_STATUSES.has(publicStatus)
);
"""
    pattern = re.compile(r"const getPublicPhysicians = \(trial\) => \{.*?\n\};\n\n(?=const getPublicCancerTypes)", re.S)
    if not pattern.search(text):
        raise SystemExit('getPublicPhysicians anchor not found')
    text = pattern.sub(helper + '\n', text, count=1)

    new_build = r"""const buildPublicTrialsDataset = (sourceTrials) => {
    const cleanTrials = sanitizeTrialListForRuntime(Array.isArray(sourceTrials) ? sourceTrials : []);
    const trials = cleanTrials
        .filter(trial => trial && trial.code)
        .map(trial => {
            const publicStatus = getPublicTrialStatusLabel(trial);
            if (!shouldPublishPublicTrial(trial, publicStatus)) return null;
            return {
                code: normalizeCode(trial.code),
                studyTitle: normalizePublicText(trial.studyTitle || ''),
                phase: normalizePublicText(trial.phase || ''),
                publicStatus,
                statusClass: getPublicStatusClass(publicStatus),
                cancerTypes: getPublicCancerTypes(trial),
                departments: getSuggestedPublicDepartments(trial),
                registrationUrl: PUBLIC_DEFAULT_REGISTRATION_URL,
                updatedAt: normalizePublicText(trial.updatedAt || trial.updated_at || '')
            };
        })
        .filter(Boolean);
    return assertPublicDatasetSafe({
        schemaVersion: PUBLIC_NOTICE_SCHEMA_VERSION,
        generatedAt: new Date().toISOString(),
        source: 'Taipei Veterans General Hospital internal clinical trial management system public notice projection',
        privacyLevel: 'strict-public-allowlist',
        noticeType: 'clinical-trial-information-notice',
        appointmentLinks: { registration: PUBLIC_DEFAULT_REGISTRATION_URL },
        disclaimer: '本頁為臺北榮民總醫院臨床試驗資訊公告與查詢。內容供民眾了解目前可公開之臨床試驗資訊；不提供納入或排除條件、主持人或研究團隊聯絡資訊。若對特定試驗有興趣，請至建議科別門診掛號，由臨床醫師進一步評估。',
        trialCount: trials.length,
        trials
    });
};

"""
    build_pattern = re.compile(r"const buildPublicTrialsDataset = \(sourceTrials\) => \{.*?\n\};\n\n(?=const publishPublicTrialsToFirestore)", re.S)
    if not build_pattern.search(text):
        raise SystemExit('buildPublicTrialsDataset anchor not found')
    text = build_pattern.sub(new_build, text, count=1)

    text = text.replace(
        "公開版只包含癌種、線別、收案狀態、納入/排除條件與公開洽詢醫師，不包含研究護理師、電話、LINE、受試者或內部備註。",
        "公開版只包含疾病/癌種、試驗名稱、Phase、治療線別、目前狀態、建議科別與掛號入口。Inclusion/Exclusion、PI/Sub-I、CRC、電話、Email 與內部備註不會輸出。未勾選『可刊登於民眾版』或已停止/收滿的試驗不會發布。"
    )
    text = text.replace(
        "title: '將目前內部資料轉成去識別化公開版並發布到 Firestore public/clinical-trials'",
        "title: '依民眾版白名單 schema 發布到 Firestore public/clinical-trials；不輸出 I/E、PI/Sub-I、CRC 或聯絡資訊'"
    )
    text = text.replace(
        "title: '下載去識別化公開版 public_trials.json；不含研究護理師、電話、LINE、受試者或內部備註'",
        "title: '下載民眾版白名單 public_trials.json；不含 I/E、PI/Sub-I、CRC、電話、Email 或內部備註'"
    )
    return text


def new_public_page():
    return r'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>臺北榮民總醫院臨床試驗資訊公開查詢</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore-compat.js"></script>
  <style>html,body{max-width:100%;overflow-x:hidden}*{min-width:0}.break-anywhere{overflow-wrap:anywhere;word-break:break-word}</style>
</head>
<body class="bg-slate-50 text-slate-900">
<div class="min-h-screen">
<header class="bg-white border-b shadow-sm">
  <div class="max-w-6xl mx-auto px-4 py-6 flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
    <div><div class="text-sm font-semibold text-blue-700">臺北榮民總醫院</div><h1 class="text-2xl md:text-3xl font-bold mt-1">臨床試驗資訊公開查詢</h1><p class="text-sm text-slate-600 mt-2">依器官、疾病別與治療情境查詢目前可公開的臨床試驗資訊。</p></div>
    <a id="registrationLink" href="https://www6.vghtpe.gov.tw/reg/" target="_blank" rel="noopener" class="px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold text-center hover:bg-blue-700">臺北榮總網路掛號</a>
  </div>
</header>
<main class="max-w-6xl mx-auto px-4 py-6">
  <section class="bg-sky-50 border border-sky-200 rounded-2xl p-4 mb-5 text-sm text-sky-950"><div class="font-semibold mb-1">關於本頁</div><div id="disclaimer">本頁為臨床試驗資訊公告與查詢，不提供納入/排除條件、主持人或研究團隊聯絡資訊。若對特定試驗有興趣，請至建議科別門診掛號，由臨床醫師進一步評估。</div></section>
  <section class="bg-white rounded-2xl border shadow-sm p-4 mb-6"><div class="grid md:grid-cols-4 gap-3"><input id="searchInput" class="md:col-span-2 px-4 py-2.5 rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="搜尋：疾病、癌種、試驗代碼、藥名，例如乳癌、肺癌、HER2、KRAS"/><select id="cancerFilter" class="px-4 py-2.5 rounded-xl border bg-white"><option value="全部">全部疾病 / 癌種</option></select><select id="statusFilter" class="px-4 py-2.5 rounded-xl border bg-white"><option value="全部">全部狀態</option><option value="收案中">收案中</option><option value="需問名額">需問名額</option><option value="暫停收案">暫停收案</option><option value="尚未開放">尚未開放</option><option value="預備中">預備中</option></select></div><div class="flex flex-wrap gap-2 mt-3 text-xs" id="summaryChips"></div></section>
  <div id="meta" class="text-sm text-slate-500 mb-4"></div><div id="emptyState" class="hidden bg-white border rounded-2xl p-8 text-center text-slate-600">找不到符合條件的臨床試驗。</div><div id="cards" class="space-y-4"></div>
</main></div>
<script>
const DEFAULT_FIREBASE_CONFIG={apiKey:'AIzaSyDQREDbVoc6QpcKitiU5JN5gWk4JHKE1Og',authDomain:'clinicaltrial-vghtpe.firebaseapp.com',databaseURL:'https://clinicaltrial-vghtpe-default-rtdb.firebaseio.com',projectId:'clinicaltrial-vghtpe',storageBucket:'clinicaltrial-vghtpe.firebasestorage.app',messagingSenderId:'220821651319',appId:'1:220821651319:web:19dbfbaea0ea999472eb72'};
const PUBLIC_DOC={collection:'public',id:'clinical-trials'};
const FORBIDDEN=new Set(['inclusion','exclusion','pi','subI','sub_i','investigator','publicPhysicians','nurse','crc','phone','email','lineId','comments','subjects','sponsor','targetNum','enrolled','monthSigned','monthEnrolled']);
const state={data:null,filtered:[],search:'',cancer:'全部',status:'全部',loadedFrom:''};
const norm=v=>String(v||'').toLowerCase().replace(/[\s　\r\n、，,\/／\-–—_()（）.]+/g,'').trim();
const esc=value=>String(value||'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const statusClassMap={open:'bg-emerald-100 text-emerald-800 border-emerald-200',ask:'bg-blue-100 text-blue-800 border-blue-200',paused:'bg-amber-100 text-amber-800 border-amber-200',preparing:'bg-purple-100 text-purple-800 border-purple-200',unknown:'bg-gray-100 text-gray-700 border-gray-200'};
function chip(text,cls='bg-slate-100 text-slate-700 border-slate-200'){return `<span class="inline-flex items-center px-2.5 py-1 rounded-full border ${cls}">${esc(text)}</span>`}
function safeTrial(t){if(!t||typeof t!=='object')return null;for(const k of Object.keys(t)){if(FORBIDDEN.has(k)){console.warn('Rejected legacy/unsafe public trial key',k,t.code);return null}}return t}
const textBlob=t=>[t.code,t.studyTitle,t.phase,t.publicStatus,...(t.departments||[]),...(t.cancerTypes||[]).flatMap(ct=>[ct.type,...(ct.lines||[]).map(x=>x.line)])].join(' ');
function setData(data,loadedFrom){const incoming=data||{trials:[],trialCount:0};incoming.trials=(incoming.trials||[]).map(safeTrial).filter(Boolean);incoming.trialCount=incoming.trials.length;state.data=incoming;state.loadedFrom=loadedFrom||'';document.getElementById('disclaimer').textContent=incoming.disclaimer||document.getElementById('disclaimer').textContent;const links=incoming.appointmentLinks||{};if(links.registration)document.getElementById('registrationLink').href=links.registration;renderFilters();applyFilters()}
function renderFilters(){const s=new Set();(state.data.trials||[]).forEach(t=>(t.cancerTypes||[]).forEach(ct=>ct.type&&s.add(ct.type)));const el=document.getElementById('cancerFilter'),cur=el.value||'全部';el.innerHTML='<option value="全部">全部疾病 / 癌種</option>';[...s].sort((a,b)=>a.localeCompare(b,'zh-Hant')).forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;el.appendChild(o)});el.value=[...el.options].some(o=>o.value===cur)?cur:'全部'}
function applyFilters(){if(!state.data)return;const s=norm(state.search);state.filtered=(state.data.trials||[]).filter(t=>{if(state.status!=='全部'&&t.publicStatus!==state.status)return false;if(state.cancer!=='全部'&&!(t.cancerTypes||[]).some(ct=>ct.type===state.cancer))return false;if(s&&!norm(textBlob(t)).includes(s))return false;return true});render()}
function renderSummary(){const counts={};(state.data.trials||[]).forEach(t=>counts[t.publicStatus]=(counts[t.publicStatus]||0)+1);const order=['收案中','需問名額','暫停收案','尚未開放','預備中'];document.getElementById('summaryChips').innerHTML=order.filter(k=>counts[k]).map(k=>chip(`${k} ${counts[k]}`)).join('')+chip(`目前顯示 ${state.filtered.length}/${state.data.trialCount||0}`)}
function renderCard(t){const statusCls=statusClassMap[t.statusClass]||statusClassMap.unknown;const cancers=(t.cancerTypes||[]).map(ct=>{const lines=(ct.lines||[]).map(x=>chip(x.line+(x.status&&x.status!=='依全試驗狀態'?`｜${x.status}`:''),x.status==='該線暫停/收滿'?'bg-rose-50 text-rose-700 border-rose-200':'bg-slate-100 text-slate-700 border-slate-200')).join(' ');return `<div class="mt-2"><span class="font-semibold text-slate-800">${esc(ct.type||'未分類')}</span><div class="flex flex-wrap gap-1.5 mt-1">${lines||chip('未指定治療線')}</div></div>`}).join('');const deps=(t.departments||['相關專科門診']).map(d=>chip(d,'bg-blue-50 text-blue-800 border-blue-200')).join(' ');const reg=esc(t.registrationUrl||(state.data.appointmentLinks||{}).registration||'https://www6.vghtpe.gov.tw/reg/');return `<article class="bg-white border rounded-2xl shadow-sm p-5"><div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4"><div class="min-w-0 flex-1"><div class="flex flex-wrap gap-2 items-center mb-2">${chip(t.publicStatus,statusCls)}${t.phase?chip('Phase '+t.phase):''}${chip(t.code)}</div><h2 class="text-lg font-bold text-slate-900 leading-snug break-anywhere">${esc(t.studyTitle||t.code)}</h2></div><div class="text-sm bg-blue-50 border border-blue-100 text-blue-950 rounded-xl p-3 md:w-64 shrink-0"><div class="font-semibold">建議就診科別</div><div class="flex flex-wrap gap-1.5 mt-2">${deps}</div><a href="${reg}" target="_blank" rel="noopener" class="mt-3 block text-center px-3 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700">前往掛號</a></div></div><div class="mt-3 border-t pt-3">${cancers}</div></article>`}
function render(){renderSummary();const cards=document.getElementById('cards'),empty=document.getElementById('emptyState');cards.innerHTML=state.filtered.map(renderCard).join('');empty.classList.toggle('hidden',state.filtered.length>0);const updated=state.data.generatedAt?new Date(state.data.generatedAt).toLocaleString('zh-TW'):'未知';document.getElementById('meta').textContent=`資料來源：${state.loadedFrom}｜資料更新：${updated}｜共 ${state.data.trialCount||0} 個試驗｜本公開版不含 I/E、主持人、研究團隊聯絡資訊或受試者資料。`}
async function loadFallbackJSON(){const r=await fetch('public_trials.json',{cache:'no-store'});if(!r.ok)throw new Error('public_trials.json not found');return await r.json()}
async function loadData(){document.getElementById('cards').innerHTML='<div class="bg-white border rounded-2xl p-8 text-center text-slate-600">載入公開試驗資料中...</div>';try{firebase.initializeApp(DEFAULT_FIREBASE_CONFIG);const db=firebase.firestore();let first=true;db.collection(PUBLIC_DOC.collection).doc(PUBLIC_DOC.id).onSnapshot(async doc=>{if(doc.exists)setData(doc.data(),'Firebase 公開資料');else if(first)setData(await loadFallbackJSON(),'public_trials.json 備份');first=false},async err=>{console.warn(err);setData(await loadFallbackJSON(),'public_trials.json 備份')})}catch(err){try{setData(await loadFallbackJSON(),'public_trials.json 備份')}catch(e){document.getElementById('cards').innerHTML='<div class="bg-white border rounded-2xl p-8 text-center text-slate-700"><div class="font-bold text-lg mb-2">尚未找到公開版資料</div><div class="text-sm">請由院內管理系統發布民眾版資料。</div></div>'}}}
document.getElementById('searchInput').addEventListener('input',e=>{state.search=e.target.value;applyFilters()});document.getElementById('cancerFilter').addEventListener('change',e=>{state.cancer=e.target.value;applyFilters()});document.getElementById('statusFilter').addEventListener('change',e=>{state.status=e.target.value;applyFilters()});loadData();
</script></body></html>'''


def sanitize_fallback():
    if not FALLBACK.exists():
        return
    data = json.loads(FALLBACK.read_text(encoding='utf-8'))
    safe = []
    for t in data.get('trials', []):
        status = t.get('publicStatus', '')
        if status not in VISIBLE_STATUSES:
            continue
        cancer_types = t.get('cancerTypes') or []
        deps = t.get('departments') or infer_departments_from_types([x.get('type','') for x in cancer_types if isinstance(x, dict)])
        safe.append({
            'code': t.get('code',''),
            'studyTitle': t.get('studyTitle',''),
            'phase': t.get('phase',''),
            'publicStatus': status,
            'statusClass': t.get('statusClass','unknown'),
            'cancerTypes': cancer_types,
            'departments': deps,
            'registrationUrl': DEFAULT_REG,
            'updatedAt': t.get('updatedAt','')
        })
    out = {
        'schemaVersion': 'public-trials-v2.0-20260904',
        'generatedAt': data.get('generatedAt',''),
        'source': 'legacy fallback sanitized to strict public allowlist',
        'privacyLevel': 'strict-public-allowlist',
        'noticeType': 'clinical-trial-information-notice',
        'appointmentLinks': {'registration': DEFAULT_REG},
        'disclaimer': '本頁為臺北榮民總醫院臨床試驗資訊公告與查詢。內容供民眾了解目前可公開之臨床試驗資訊；不提供納入或排除條件、主持人或研究團隊聯絡資訊。若對特定試驗有興趣，請至建議科別門診掛號，由臨床醫師進一步評估。',
        'trialCount': len(safe),
        'trials': safe
    }
    FALLBACK.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    idx = INDEX.read_text(encoding='utf-8')
    patched = patch_index(idx)
    INDEX.write_text(patched, encoding='utf-8')
    PUBLIC.write_text(new_public_page(), encoding='utf-8')
    sanitize_fallback()
    print('patched public clinical trial notice v2')

if __name__ == '__main__':
    main()

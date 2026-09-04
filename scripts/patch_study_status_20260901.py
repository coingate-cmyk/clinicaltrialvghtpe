from pathlib import Path
import json
import re

INDEX = Path('index.html')
DATA = Path('data.json')
VERSION = 'v4.3.6-20260901-study-status-pdf'
DATE = '2026-09-01'
SNAPSHOT = {'DB1311-201': {'targetNum': '3', 'enrolled': '3', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '暫停收案'},
 'TTY': {'targetNum': '150', 'enrolled': '16', 'monthSigned': '1', 'monthEnrolled': '1', 'status': '進行中'},
 'D702AC00001': {'targetNum': '5', 'enrolled': 'pre-screen 1 /screen 0', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'DS8201-724': {'targetNum': '7', 'enrolled': '5(screen failure)/1', 'monthSigned': '1', 'monthEnrolled': '0', 'status': '進行中'},
 'D967LC0001': {'targetNum': '3', 'enrolled': '0', 'monthSigned': '1', 'monthEnrolled': '0', 'status': '暫無slot'},
 'D9803C00001': {'targetNum': '15', 'enrolled': '1', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 '8951-CL-0305': {'targetNum': '2', 'enrolled': '0 / 6 Prescreen', 'monthSigned': '1 screen', 'monthEnrolled': '0', 'status': '停止收案'},
 'MK-3475-06C': {'targetNum': '6', 'enrolled': '0', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'C6461016': {'targetNum': '3', 'enrolled': '1', 'monthSigned': '1', 'monthEnrolled': '0', 'status': '進行中'},
 'T1223': {'targetNum': '25', 'enrolled': '15', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'MK-3475-06D': {'targetNum': '3-6', 'enrolled': '1', 'monthSigned': '1', 'monthEnrolled': '0', 'status': '暫無slot'},
 'D9800C00001': {'targetNum': '10','enrolled': '3胃癌(screen) / 3胰臟癌(screen) / 3膽道癌','monthSigned': '1胰臟癌(prescreen) / 0胃癌(prescreen) / 0膽管癌(screen)','monthEnrolled': '0','status': '名額已滿'},
 'BBI-4182-101': {'targetNum': '2','enrolled': '1','monthSigned': '','monthEnrolled': '1','status': '暫無slot','comments': '目前沒名額/可以預排/已排3個病人'},
 'RMC-6236-303': {'targetNum': '15', 'enrolled': '0', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'C3651021': {'targetNum': '15', 'enrolled': '7', 'monthSigned': '1', 'monthEnrolled': '1', 'status': '進行中'},
 'CA2400030': {'targetNum': '12', 'enrolled': '10', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '暫停收案'},
 'MK-3475-06E': {'targetNum': '3-5', 'enrolled': '2', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '暫無slot'},
 'CHS-114-02': {'targetNum': '6','enrolled': '4 (Cohort A 1 / Cohort B 1 / Cohort C 2)','monthSigned': '0','monthEnrolled': '0','status': '需問slot'},
 'MK-3475-06B': {'targetNum': '6- 10', 'enrolled': '6', 'monthSigned': '1', 'monthEnrolled': '0', 'status': '進行中'},
 'DS7300-202': {'targetNum': '4', 'enrolled': '0 / 4 screen failure', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'MK-3475-06F': {'targetNum': '3-5', 'enrolled': '5', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '名額已滿'},
 'D702NC00001': {'targetNum': '15', 'enrolled': '5 screen failure / 3 有用藥', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'DESTINY-BILIARY TRACT': {'targetNum': '6','enrolled': '5(有用藥)/ 3(screen failure)','monthSigned': '0','monthEnrolled': '0','status': '進行中'},
 'TT420C2308': {'targetNum': '6', 'enrolled': '4', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '停止收案'},
 'TAI-301': {'targetNum': '15', 'enrolled': '6', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'MK-1022': {'targetNum': '6', 'enrolled': '2', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'PEP08-101': {'targetNum': '9', 'enrolled': '4', 'monthSigned': '2', 'monthEnrolled': '2', 'status': '進行中'},
 'PEP07-102': {'targetNum': '20', 'enrolled': '3', 'monthSigned': '1', 'monthEnrolled': '1', 'status': '需問slot'},
 'MK-9999-02A': {'targetNum': '4','enrolled': 'pancrea ca:1 / CHOLANGIOCARCINOMA:1','monthSigned': '0','monthEnrolled': '0','status': '名額已滿'},
 'MK5909-005': {'targetNum': '4-6','enrolled': 'pancrea ca:4 / stomach ca:1 / CHOLANGIOCARCINOMA:1','monthSigned': '0','monthEnrolled': '0','status': '名額已滿'},
 'TYR430-101': {'targetNum': '15', 'enrolled': '', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '停止收案'},
 'BGM-2121-001': {'targetNum': '15', 'enrolled': '2', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 '20250004': {'targetNum': '5','enrolled': '1','monthSigned': '1 (planning on 2026/8/24)','monthEnrolled': '0','status': '需問slot','comments': '須向 sponsor 申請 slot'},
 'C23-101': {'targetNum': '10', 'enrolled': '0', 'monthSigned': '1', 'monthEnrolled': '0', 'status': '進行中'},
 'C6461003': {'targetNum': '10', 'enrolled': '3', 'monthSigned': '1', 'monthEnrolled': '0', 'status': '進行中'},
 'MK-1082-012': {'targetNum': 'Part 1: 2 Part 2: 2 (預計 2026.04 開始收案)','enrolled': 'Part 1: 2','monthSigned': '2','monthEnrolled': '2','status': '進行中'},
 'M24-533': {'targetNum': '5', 'enrolled': '3', 'monthSigned': '2', 'monthEnrolled': '1', 'status': '進行中'},
 '20210081': {'targetNum': '2', 'enrolled': '1', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'SGNTUC-029': {'targetNum': '6', 'enrolled': '3', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'CA266-0003': {'targetNum': '8', 'enrolled': '0', 'monthSigned': '2', 'monthEnrolled': '2', 'status': '進行中'},
 'WO42758': {'targetNum': '10', 'enrolled': '6', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 '61186372COR3002': {'targetNum': '5', 'enrolled': '4', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'MS914001_0002': {'targetNum': '9', 'enrolled': '0', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '進行中'},
 'XL092-311': {'targetNum': '3', 'enrolled': '', 'monthSigned': '', 'monthEnrolled': '', 'status': '進行中'},
 'GW-020202': {'targetNum': '3', 'enrolled': '0', 'monthSigned': '0', 'monthEnrolled': '0', 'status': '還未SIV'}}
NEW_TRIALS = [{'cancerType': '胰臟癌','line': '一線','studyTitle': 'RASolute 303：一項第 3 期全球、多中心、開放標示、隨機分配、3 組別試驗，研究 Daraxonrasib 單一療法或 Daraxonrasib 加 Gemcitabine 併用 Nab-paclitaxel，相較於 Gemcitabine 併用 Nab-paclitaxel 作為轉移性胰臟腺癌患者的第一線治療','code': 'RMC-6236-303','phase': 'III','sponsor': 'Revolution Medicines, Inc.','targetNum': '15','enrolled': '0','monthSigned': '0','monthEnrolled': '0','pi': '姜乃榕','nurse': '王昭蘋','phone': '0919377185','status': '進行中','inclusion': '收案條件：1. 資料顯示有轉移性胰管腺癌 2. 尚未接受過治療（一線治療） 3. Measurable lesion by RECIST 1.1 4. NON-B,C 肝 5. 需要送腫瘤切片 11 片 6. 需有 RAS 報告 7. 分三組：1.標靶 2.標靶+化療 3.化療','exclusion': '','cancerTypes': [{'type': '胰臟癌', 'lines': ['一線']}],'subjects': [],'statusSource': 'explicit-field','statusDetectedFromText': False},
 {'cancerType': '神經內分泌腫瘤','line': '','studyTitle': 'Zanzalintinib 相對於 Everolimus，用於罹患無法切除、局部晚期或轉移性神經內分泌瘤，先前接受過治療參與者的一項第 2/3 期、多中心、隨機分配、開放性試驗','code': 'XL092-311','phase': 'II/III','sponsor': 'Exelixis, Inc.','targetNum': '3','enrolled': '','monthSigned': '','monthEnrolled': '','pi': '陳明晃','nurse': '宋秀薇 / 賴姵妤','phone': '82935 / 82999 / 0936385216','status': '進行中','inclusion': '','exclusion': '','contractNo': 'C2602100','cancerTypes': [{'type': '神經內分泌腫瘤', 'lines': []}],'subjects': [],'statusSource': 'explicit-field','statusDetectedFromText': False}]

def normalize_code(value):
    raw = str(value or '').strip().upper()
    compact = re.sub(r'\s+', '', raw)
    if re.fullmatch(r'DESTINY-BILIARY-?TRACT', compact, re.I): return 'DESTINY-BILIARY TRACT'
    return raw

def apply_patch_to_trial(trial):
    t = dict(trial or {}); key = normalize_code(t.get('code')); patch = SNAPSHOT.get(key)
    if patch:
        t.update(patch); t['studyStatusSnapshotVersion'] = VERSION; t['studyStatusSnapshotDate'] = DATE
        t['statusSource'] = 'explicit-field'; t['statusDetectedFromText'] = False
    return t

def merge_new_trials(trials):
    out = [dict(t) for t in (trials or [])]; existing = {normalize_code(t.get('code')) for t in out}
    next_id = max([int(t.get('id')) for t in out if str(t.get('id','')).isdigit()] or [0]) + 1
    for src in NEW_TRIALS:
        key = normalize_code(src.get('code'))
        if key in existing: continue
        item = dict(src); item['id'] = next_id; next_id += 1; item = apply_patch_to_trial(item); out.append(item); existing.add(key)
    return out

def patch_index(html):
    if VERSION not in html:
        old_fn = re.search(r"const applyStudyStatusSnapshot20260822 = \(trial\) => \{[\s\S]*?\n\};", html)
        if not old_fn: raise SystemExit('Cannot locate 2026-08-22 Study Status function anchor')
        js_snapshot = json.dumps(SNAPSHOT, ensure_ascii=False, separators=(',', ':'))
        block = """
const STUDY_STATUS_SNAPSHOT_VERSION_20260901 = '__VERSION__';
const STUDY_STATUS_SNAPSHOT_20260901 = __SNAPSHOT_JS__;
const applyStudyStatusSnapshot20260901 = (trial) => {
    const t = { ...(trial || {}) };
    const key = normalizeCode(t.code);
    const patch = STUDY_STATUS_SNAPSHOT_20260901[key];
    if (!patch || t.studyStatusSnapshotVersion === STUDY_STATUS_SNAPSHOT_VERSION_20260901) return t;
    Object.entries(patch).forEach(([field, value]) => { t[field] = value; });
    t.studyStatusSnapshotVersion = STUDY_STATUS_SNAPSHOT_VERSION_20260901;
    t.studyStatusSnapshotDate = '2026-09-01';
    t.statusSource = STATUS_SOURCE_EXPLICIT_FIELD;
    t.statusDetectedFromText = false;
    return t;
};
""".replace('__VERSION__', VERSION).replace('__SNAPSHOT_JS__', js_snapshot)
        html = html[:old_fn.end()] + '\n\n' + block.strip() + html[old_fn.end():]
    old_call = "    t = applyStudyStatusSnapshot20260822(t);"
    new_calls = old_call + "\n    t = applyStudyStatusSnapshot20260901(t);"
    if 't = applyStudyStatusSnapshot20260901(t);' not in html:
        if old_call not in html: raise SystemExit('Cannot locate runtime Study Status call')
        html = html.replace(old_call, new_calls, 1)
    m = re.search(r"const INITIAL_TRIALS = (\[[\s\S]*?\]);\n\nfunction AccessPasswordModal", html)
    if not m: raise SystemExit('Cannot locate INITIAL_TRIALS')
    trials = [apply_patch_to_trial(t) for t in merge_new_trials(json.loads(m.group(1)))]
    replacement = 'const INITIAL_TRIALS = ' + json.dumps(trials, ensure_ascii=False, separators=(',', ':')) + ';\n\nfunction AccessPasswordModal'
    return html[:m.start()] + replacement + html[m.end():]

def patch_data():
    if not DATA.exists(): raise SystemExit('data.json missing')
    obj = json.loads(DATA.read_text(encoding='utf-8')); trials = merge_new_trials(obj.get('trials', []))
    obj['trials'] = [apply_patch_to_trial(t) for t in trials]
    DATA.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def main():
    if not INDEX.exists(): raise SystemExit('index.html missing')
    html = INDEX.read_text(encoding='utf-8'); html = patch_index(html); INDEX.write_text(html, encoding='utf-8'); patch_data()
    print(f'Applied Study Status {DATE}: {len(SNAPSHOT)} status rows; added/updated RMC-6236-303 and XL092-311.')

if __name__ == '__main__': main()

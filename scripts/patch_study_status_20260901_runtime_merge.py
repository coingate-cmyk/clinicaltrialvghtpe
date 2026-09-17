from pathlib import Path
import json

INDEX = Path('index.html')
TITLE_IMPORT_PATCH_VERSION = 'v4.3.7-20260917-study-title-import'
NEW_TRIALS = [
    {
        'cancerType': '胰臟癌',
        'line': '一線',
        'studyTitle': 'RASolute 303：一項第 3 期全球、多中心、開放標示、隨機分配、3 組別試驗，研究 Daraxonrasib 單一療法或 Daraxonrasib 加 Gemcitabine 併用 Nab-paclitaxel，相較於 Gemcitabine 併用 Nab-paclitaxel 作為轉移性胰臟腺癌患者的第一線治療',
        'code': 'RMC-6236-303',
        'phase': 'III',
        'sponsor': 'Revolution Medicines, Inc.',
        'targetNum': '15',
        'enrolled': '0',
        'monthSigned': '0',
        'monthEnrolled': '0',
        'pi': '姜乃榕',
        'nurse': '王昭蘋',
        'phone': '0919377185',
        'status': '進行中',
        'inclusion': '收案條件：1. 資料顯示有轉移性胰管腺癌 2. 尚未接受過治療（一線治療） 3. Measurable lesion by RECIST 1.1 4. NON-B,C 肝 5. 需要送腫瘤切片 11 片 6. 需有 RAS 報告 7. 分三組：1.標靶 2.標靶+化療 3.化療',
        'exclusion': '',
        'cancerTypes': [{'type': '胰臟癌', 'lines': ['一線']}],
        'subjects': [],
        'statusSource': 'explicit-field',
        'statusDetectedFromText': False,
        'studyStatusSnapshotVersion': 'v4.3.6-20260901-study-status-pdf',
        'studyStatusSnapshotDate': '2026-09-01'
    },
    {
        'cancerType': '神經內分泌腫瘤',
        'line': '',
        'studyTitle': 'Zanzalintinib 相對於 Everolimus，用於罹患無法切除、局部晚期或轉移性神經內分泌瘤，先前接受過治療參與者的一項第 2/3 期、多中心、隨機分配、開放性試驗',
        'code': 'XL092-311',
        'phase': 'II/III',
        'sponsor': 'Exelixis, Inc.',
        'targetNum': '3',
        'enrolled': '',
        'monthSigned': '',
        'monthEnrolled': '',
        'pi': '陳明晃',
        'nurse': '宋秀薇 / 賴姵妤',
        'phone': '82935 / 82999 / 0936385216',
        'status': '進行中',
        'inclusion': '',
        'exclusion': '',
        'contractNo': 'C2602100',
        'cancerTypes': [{'type': '神經內分泌腫瘤', 'lines': []}],
        'subjects': [],
        'statusSource': 'explicit-field',
        'statusDetectedFromText': False,
        'studyStatusSnapshotVersion': 'v4.3.6-20260901-study-status-pdf',
        'studyStatusSnapshotDate': '2026-09-01'
    }
]


def replace_required(text, old, new, label, count=1):
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    return text.replace(old, new, count)


def patch_study_title_import(html):
    marker = f"const STUDY_TITLE_IMPORT_PATCH_VERSION = '{TITLE_IMPORT_PATCH_VERSION}';"
    if marker in html:
        return html

    normalize_text_anchor = r"const normalizeText = (v) => String(v || '').replace(/\s+/g, ' ').trim();"
    title_helpers = normalize_text_anchor + f"""
const STUDY_TITLE_IMPORT_PATCH_VERSION = '{TITLE_IMPORT_PATCH_VERSION}';
const normalizeStudyTitleHeaderToken = (value) => String(value || '')
    .toLowerCase()
    .replace(/[\\s_\\-（）()\\/:：.]+/g, '');
const isStudyTitleHeaderText = (value) => {{
    const token = normalizeStudyTitleHeaderToken(value);
    return /^(?:study(?:title|tittle)|trialtitle|protocoltitle|試驗名稱|試驗標題|計畫名稱)$/.test(token);
}};
const normalizeImportedStudyTitle = (value) => {{
    const lines = String(value || '').replace(/\\r/g, '\\n').split(/\\n+/)
        .map(line => String(line || '').replace(/^\\s*(?:study\\s*(?:title|tittle)|trial\\s*title|protocol\\s*title|試驗名稱|試驗標題|計畫名稱)\\s*(?:[:：\\-–—]\\s*)?/i, '').trim())
        .filter(Boolean)
        .filter(line => !isStudyTitleHeaderText(line));
    return normalizeText(lines.join(' '));
}};
const chooseImportedStudyTitle = (previousValue, incomingValue) => {{
    const previous = normalizeImportedStudyTitle(previousValue);
    const incoming = normalizeImportedStudyTitle(incomingValue);
    return incoming || previous;
}};"""
    html = replace_required(html, normalize_text_anchor, title_helpers, 'normalizeText')

    html = replace_required(
        html,
        "'studytitle','study title','title','trial title','protocol title'",
        "'studytitle','study title','studytittle','study tittle','title','trial title','protocol title'",
        'studyTitle aliases'
    )

    # Accept the common typo in PDF/worksheet headers everywhere the standard header is recognized.
    html = html.replace(r'Study\s*title', r'Study\s*(?:title|tittle)')

    old_runtime = """const sanitizeTrialForRuntime = (trial) => {
    let t = { ...(trial || {}) };
    t = sanitizePersonFields(t);"""
    new_runtime = """const sanitizeTrialForRuntime = (trial) => {
    let t = { ...(trial || {}) };
    t.studyTitle = normalizeImportedStudyTitle(t.studyTitle);
    t = sanitizePersonFields(t);"""
    html = replace_required(html, old_runtime, new_runtime, 'sanitizeTrialForRuntime')

    html = replace_required(
        html,
        'cleaned.studyTitle = normalizeText(cleaned.studyTitle);',
        'cleaned.studyTitle = normalizeImportedStudyTitle(cleaned.studyTitle);',
        'cleanTrialForSave studyTitle'
    )
    html = replace_required(
        html,
        'trial.studyTitle = normalizeText(trial.studyTitle);',
        'trial.studyTitle = normalizeImportedStudyTitle(trial.studyTitle);',
        'normalizeFirestoreTrial studyTitle'
    )

    old_import_normalize = """const normalizeImportedTrialFields = (item, options = {}) => {
    let out = { ...(item || {}) };
    out = sanitizePersonFields(out, [out.pi, out.nurse, out.studyTitle, out.inclusion, out.comments].filter(Boolean).join('\\n'));"""
    new_import_normalize = """const normalizeImportedTrialFields = (item, options = {}) => {
    let out = { ...(item || {}) };
    out.studyTitle = normalizeImportedStudyTitle(out.studyTitle);
    out = sanitizePersonFields(out, [out.pi, out.nurse, out.studyTitle, out.inclusion, out.comments].filter(Boolean).join('\\n'));"""
    html = replace_required(html, old_import_normalize, new_import_normalize, 'normalizeImportedTrialFields studyTitle')

    old_merge_fields = """        Object.entries(row || {}).forEach(([field, value]) => {
            if (field === 'cancerTypes') return;
            if (field === 'status') {"""
    new_merge_fields = """        Object.entries(row || {}).forEach(([field, value]) => {
            if (field === 'cancerTypes') return;
            if (field === 'studyTitle') {
                merged.studyTitle = chooseImportedStudyTitle(merged.studyTitle, value);
                return;
            }
            if (field === 'status') {"""
    html = replace_required(html, old_merge_fields, new_merge_fields, 'consolidateParsedTrials studyTitle merge')

    html = replace_required(
        html,
        'studyTitle: normalizeText(incomingForMerge.studyTitle || prev.studyTitle),',
        'studyTitle: chooseImportedStudyTitle(prev.studyTitle, incomingForMerge.studyTitle),',
        'upsertTrialsByCode studyTitle merge'
    )

    old_first_line = """const firstLineMatching = (lines, regex, start = 0) => {
    for (let i = Math.max(0, start); i < lines.length; i++) {
        if (regex.test(lines[i])) return { index: i, value: lines[i] };
    }
    return { index: -1, value: '' };
};"""
    new_first_line = """const firstLineMatching = (lines, regex, start = 0) => {
    for (let i = Math.max(0, start); i < lines.length; i++) {
        if (isStudyTitleHeaderText(lines[i])) continue;
        if (regex.test(lines[i])) return { index: i, value: lines[i] };
    }
    return { index: -1, value: '' };
};"""
    html = replace_required(html, old_first_line, new_first_line, 'firstLineMatching header guard')

    html = replace_required(
        html,
        ".filter(block => /(一項|試驗|study|trial)/i.test(block.text) && block.text.length > 20)",
        ".filter(block => !isStudyTitleHeaderText(block.text) && /(一項|試驗|study|trial)/i.test(block.text) && block.text.length > 20)",
        'wide PDF title header guard'
    )

    # A standard PDF should carry a real title. Surface blank-title rows in the existing warning list,
    # but do not reject them because status-only updates are allowed and must preserve the previous title.
    old_suspicious = """        return /(?:吳\\s*佳\\s*勳|王\\s*秋\\s*眉|陳\\s*秀\\s*玲|孔\\s*亭\\s*方|張\\s*台\\s*依)/.test(progress)
            || /(?:reen\\d|f\\d?ailure\\)|佳\\s*勳\\s*\\d)/i.test(progress);"""
    new_suspicious = """        return !normalizeImportedStudyTitle(row.studyTitle)
            || /(?:吳\\s*佳\\s*勳|王\\s*秋\\s*眉|陳\\s*秀\\s*玲|孔\\s*亭\\s*方|張\\s*台\\s*依)/.test(progress)
            || /(?:reen\\d|f\\d?ailure\\)|佳\\s*勳\\s*\\d)/i.test(progress);"""
    html = replace_required(html, old_suspicious, new_suspicious, 'PDF blank-title warning')

    required = [
        marker,
        "'studytittle','study tittle'",
        't.studyTitle = normalizeImportedStudyTitle(t.studyTitle);',
        'out.studyTitle = normalizeImportedStudyTitle(out.studyTitle);',
        'chooseImportedStudyTitle(prev.studyTitle, incomingForMerge.studyTitle)',
        'merged.studyTitle = chooseImportedStudyTitle(merged.studyTitle, value);',
        r'Study\s*(?:title|tittle)',
        'if (isStudyTitleHeaderText(lines[i])) continue;'
    ]
    missing = [item for item in required if item not in html]
    if missing:
        raise SystemExit('Study title import patch incomplete: ' + ', '.join(missing))
    return html


def main():
    html = INDEX.read_text(encoding='utf-8')
    if 'const STUDY_STATUS_NEW_TRIALS_20260901' not in html:
        marker = 'const applyStudyStatusSnapshot20260901 = (trial) => {'
        if marker not in html:
            raise SystemExit('2026-09-01 Study Status snapshot must be applied first')
        additions = 'const STUDY_STATUS_NEW_TRIALS_20260901 = ' + json.dumps(NEW_TRIALS, ensure_ascii=False, separators=(',', ':')) + ';\n\n'
        html = html.replace(marker, additions + marker, 1)

    old_list = """const sanitizeTrialListForRuntime = (list) => (Array.isArray(list) ? list : [])
    .map(sanitizeTrialForRuntime)
    .filter(t => isPlausibleRuntimeTrialRecord(t));"""
    new_list = """const ensureStudyStatusAdditions20260901 = (list) => {
    const out = (Array.isArray(list) ? list : []).map(t => ({ ...(t || {}) }));
    const seen = new Set(out.map(t => normalizeCode(t.code)).filter(Boolean));
    STUDY_STATUS_NEW_TRIALS_20260901.forEach(src => {
        const code = normalizeCode(src.code);
        if (code && !seen.has(code)) { out.push({ ...src }); seen.add(code); }
    });
    return out;
};

const sanitizeTrialListForRuntime = (list) => ensureStudyStatusAdditions20260901(list)
    .map(sanitizeTrialForRuntime)
    .filter(t => isPlausibleRuntimeTrialRecord(t));"""
    if old_list in html:
        html = html.replace(old_list, new_list, 1)
    elif 'const ensureStudyStatusAdditions20260901' not in html:
        raise SystemExit('sanitizeTrialListForRuntime anchor not found')

    html = patch_study_title_import(html)
    INDEX.write_text(html, encoding='utf-8')
    print('Ensured latest Study Status additions and hardened study-title import/header handling.')


if __name__ == '__main__':
    main()

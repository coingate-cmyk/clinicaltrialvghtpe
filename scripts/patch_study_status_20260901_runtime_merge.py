from pathlib import Path
import json

INDEX = Path('index.html')
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

    INDEX.write_text(html, encoding='utf-8')
    print('Ensured RMC-6236-303 and XL092-311 remain visible when Firestore still has the older collection.')


if __name__ == '__main__':
    main()

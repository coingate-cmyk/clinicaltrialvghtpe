from pathlib import Path
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'scripts' / 'patch_public_trial_notice_v2.py'
INDEX = ROOT / 'index.html'
FALLBACK = ROOT / 'public_trials.json'

spec = importlib.util.spec_from_file_location('public_notice_base', BASE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.main()

text = INDEX.read_text(encoding='utf-8')
# re.sub replacement strings interpret backslash escapes. Normalize the affected
# JavaScript regex back to a literal backslash-n escape before syntax validation.
bad = "split(/[、,，;/；\n]+/)"
good = "split(/[、,，;/；\\n]+/)"
if bad in text:
    text = text.replace(bad, good)

# Existing trials continue to publish like the prior workflow. The checkbox is an
# opt-out for individual Sponsor/contract/confidentiality restrictions.
text = text.replace('publicDisclosureApproved: false,', 'publicDisclosureApproved: true,', 1)
text = text.replace('checked: form.publicDisclosureApproved === true,', 'checked: form.publicDisclosureApproved !== false,', 1)
text = text.replace('trial && trial.publicDisclosureApproved === true && !trial.isArchived', 'trial && trial.publicDisclosureApproved !== false && !trial.isArchived', 1)
text = text.replace(
    '勾選代表已確認此案可公開；民眾版只輸出疾病/癌種、試驗名稱、Phase、治療線別、招募狀態、建議科別與掛號入口。Inclusion/Exclusion、PI/Sub-I、CRC、電話、Email 與內部備註永不輸出。',
    '預設可刊登；若個別案件因 Sponsor、合約或保密限制不宜公開，取消勾選即可。民眾版只輸出疾病/癌種、試驗名稱、Phase、治療線別、招募狀態、建議科別與掛號入口；Inclusion/Exclusion、PI/Sub-I、CRC、電話、Email 與內部備註永不輸出。'
)
text = text.replace(
    "未勾選『可刊登於民眾版』或已停止/收滿的試驗不會發布。",
    "取消『可刊登於民眾版』或已停止/收滿的試驗不會發布。"
)

# Some imported studyTitle values contain appended eligibility/contact notes. Strip
# those tails before public projection while retaining the official title/drug text.
if 'const normalizePublicStudyTitle' not in text:
    anchor = "const shouldPublishPublicTrial = (trial, publicStatus) => !!("
    helper = r"""const normalizePublicStudyTitle = (value) => {
    const lines = String(value || '').replace(/\r/g, '\n').split(/\n+/).map(x => x.trim()).filter(Boolean);
    const kept = [];
    for (const line of lines) {
        if (/(specific\s+)?inclusion\s+criteria|exclusion\s+criteria|主要納入條件|主要排除條件|納入條件|排除條件|請洽|聯絡|contact\s*:|line\s*id\s*:|\b(?:09\d{8}|0\d{1,2}-?\d{6,8})\b/i.test(line)) break;
        if (/^\s*\d{1,2}[\/.-]\d{1,2}\s+(?:SIV|COV|PSV)\b/i.test(line)) continue;
        kept.push(line);
    }
    return normalizePublicText((kept.length ? kept : lines.slice(0, 1)).join(' '));
};

"""
    if anchor not in text:
        raise SystemExit('shouldPublishPublicTrial anchor not found')
    text = text.replace(anchor, helper + anchor, 1)
text = text.replace("studyTitle: normalizePublicText(trial.studyTitle || ''),", "studyTitle: normalizePublicStudyTitle(trial.studyTitle || ''),", 1)
INDEX.write_text(text, encoding='utf-8')


def clean_public_title(value):
    lines = [x.strip() for x in str(value or '').replace('\r', '\n').split('\n') if x.strip()]
    kept = []
    stop = re.compile(r'(specific\s+)?inclusion\s+criteria|exclusion\s+criteria|主要納入條件|主要排除條件|納入條件|排除條件|請洽|聯絡|contact\s*:|line\s*id\s*:|\b(?:09\d{8}|0\d{1,2}-?\d{6,8})\b', re.I)
    skip = re.compile(r'^\s*\d{1,2}[\/.-]\d{1,2}\s+(?:SIV|COV|PSV)\b', re.I)
    for line in lines:
        if stop.search(line):
            break
        if skip.search(line):
            continue
        kept.append(line)
    return ' '.join(kept or lines[:1]).strip()

if FALLBACK.exists():
    data = json.loads(FALLBACK.read_text(encoding='utf-8'))
    for trial in data.get('trials', []):
        trial['studyTitle'] = clean_public_title(trial.get('studyTitle', ''))
    FALLBACK.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print('normalized public notice JS escapes, legacy publish behavior, and public titles')

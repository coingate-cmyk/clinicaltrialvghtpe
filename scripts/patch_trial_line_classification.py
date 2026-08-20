from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

VERSION = 'v4.3.3-20260820-gastric-line-repair'

# 1) Add a small, explicit clinical override table. These are intentionally curated,
# not inferred from arbitrary eligibility prose. It protects against stale Firestore/local
# values that were imported by older parsers.
if VERSION not in s:
    anchor = "const ENGLISH_LINE_NUMERAL = { one: '一', two: '二', three: '三', four: '四', five: '五', six: '六', seven: '七', eight: '八', nine: '九', first: '一', second: '二', third: '三', fourth: '四', fifth: '五', sixth: '六', seventh: '七', eighth: '八', ninth: '九' };\n"
    block = anchor + "\n" + r"""// Curated cancer/line repairs for records known to have stale classifications from older imports.
// Keep this list small and evidence-based; do not turn free-text eligibility into an automatic treatment-line label.
const TRIAL_CLASSIFICATION_REPAIR_VERSION = 'v4.3.3-20260820-gastric-line-repair';
const TRIAL_CLASSIFICATION_REPAIRS = {
    // COOL trial: title explicitly says second-line metastatic gastric cancer.
    'T1223': [
        { type: '胃癌', lines: ['二線'] }
    ],
    // AZD0901: current cohort notes explicitly separate pancreatic 1L, gastric 2/3L, biliary 2/3L.
    'D9800C00001': [
        { type: '胃癌', lines: ['二線', '三線'] },
        { type: '胰臟癌', lines: ['一線'] },
        { type: '膽道癌', lines: ['二線', '三線'] }
    ],
    // KEYMAKER 06C: GEA (gastric/GEJ/EAC) first-line; older seed was wrongly carried as pancreatic cancer.
    'MK-3475-06C': [
        { type: '胃癌', lines: ['一線'] }
    ],
    // KEYMAKER 06D: previously treated gastric/GEJ/EAC, explicitly 2L.
    'MK-3475-06D': [
        { type: '胃癌', lines: ['二線'] }
    ]
};
"""
    if anchor not in s:
        raise SystemExit('Could not find ENGLISH_LINE_NUMERAL anchor')
    s = s.replace(anchor, block, 1)

# 2) Define repair after normalizeCancerTypes is available.
fn_anchor = "const normalizeCancerTypes = (list) => mergeCancerTypes(list);\n"
if 'const applyKnownTrialClassificationRepair' not in s:
    fn_block = fn_anchor + r"""

const applyKnownTrialClassificationRepair = (trial) => {
    const t = { ...(trial || {}) };
    const code = normalizeCode(t.code);
    const override = TRIAL_CLASSIFICATION_REPAIRS[code];
    if (!override) return t;
    const repaired = normalizeCancerTypes(override);
    if (!repaired.length) return t;
    t.cancerTypes = repaired;
    t.cancerType = repaired[0].type || '';
    t.line = (repaired[0].lines || [])[0] || '';
    t.classificationRepairVersion = TRIAL_CLASSIFICATION_REPAIR_VERSION;
    t.classificationRepairReason = 'Curated correction of stale cancer/treatment-line mapping from legacy import.';
    return t;
};
"""
    if fn_anchor not in s:
        raise SystemExit('Could not find normalizeCancerTypes anchor')
    s = s.replace(fn_anchor, fn_block, 1)

# 3) Apply the repair at the very end of runtime sanitization, so it wins over stale
# seed, localStorage and Firestore values.
old_return = """    if (Array.isArray(t.cancerTypes) && t.cancerTypes.length) {
        t.cancerTypes = normalizeCancerTypes(t.cancerTypes);
        t.cancerType = t.cancerTypes[0].type;
        t.line = (t.cancerTypes[0].lines || [])[0] || t.line || '';
    }
    return t;
};


const looksLikeCriteriaFragmentTitle"""
new_return = """    if (Array.isArray(t.cancerTypes) && t.cancerTypes.length) {
        t.cancerTypes = normalizeCancerTypes(t.cancerTypes);
        t.cancerType = t.cancerTypes[0].type;
        t.line = (t.cancerTypes[0].lines || [])[0] || t.line || '';
    }
    // Known clinical corrections must win over stale legacy/Firestore classifications.
    t = applyKnownTrialClassificationRepair(t);
    return t;
};


const looksLikeCriteriaFragmentTitle"""
if 't = applyKnownTrialClassificationRepair(t);' not in s:
    if old_return not in s:
        raise SystemExit('Could not find sanitizeTrialForRuntime return anchor')
    s = s.replace(old_return, new_return, 1)

# 4) Defensive filter semantics: a value meaning "after first line" must never match 1L,
# even if an old record escapes normalization.
old_line = "    if (selected === '第一線') return lineHasTreatmentNumber(line, '一') || n.includes('firstline');\n"
new_line = """    if (selected === '第一線') {
        if (n.includes('一線後') || n.includes('1l後') || n.includes('post1l') || n.includes('postfirstline') || n.includes('afterfirstline') || n.includes('secondline')) return false;
        return lineHasTreatmentNumber(line, '一') || n.includes('firstline');
    }
"""
if old_line in s:
    s = s.replace(old_line, new_line, 1)
elif "if (n.includes('一線後')" not in s:
    raise SystemExit('Could not find first-line selection logic')

p.write_text(s, encoding='utf-8')
print('Clinical trial classification repair patch applied')

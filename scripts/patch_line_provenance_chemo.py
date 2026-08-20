from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

MARKER = 'v4.3.4-line-provenance-20260820'

# -----------------------------------------------------------------------------
# 0) Bring the explicit cancer/line audit into the runtime repair table.
# -----------------------------------------------------------------------------
if 'v4.3.4-20260820-explicit-line-audit' not in s:
    anchor = """    'MK-3475-06D': [
        { type: '胃癌', lines: ['二線'] }
    ]
};"""
    replacement = """    'MK-3475-06D': [
        { type: '胃癌', lines: ['二線'] }
    ],

    // v4.3.4-20260820-explicit-line-audit
    // CHS-114-02 has explicit cohort labels: 2L GEA, 2L/1L ESCC and 4L+ CRC.
    'CHS-114-02': [
        { type: '胃癌', lines: ['二線'] },
        { type: '食道癌', lines: ['一線', '二線'] },
        { type: '大腸癌', lines: ['四線以上'] }
    ],
    // KEYMAKER 06E is explicitly first-line ESCC.
    'MK-3475-06E': [
        { type: '食道癌', lines: ['一線'] }
    ],
    // KEYMAKER 06B requires progression after one prior line including platinum + PD-1/PD-L1.
    'MK-3475-06B': [
        { type: '食道癌', lines: ['二線'] }
    ],
    // IDeate-Esophageal01: pretreated ESCC, maximum one prior systemic line.
    'DS7300-202': [
        { type: '食道癌', lines: ['二線'] }
    ],
    // mCRC study explicitly requires one prior systemic line for metastatic disease.
    '61186372COR3002': [
        { type: '大腸癌', lines: ['二線'] }
    ],
    // KANDLELIT-012: Part 1 allows treatment-naive or one prior line; Part 2 is treatment-naive.
    'MK-1082-012': [
        { type: '大腸癌', lines: ['一線', '二線'] }
    ],
    // FIRST-308 requires prior chemotherapy plus a prior FGFR inhibitor: two prior treatment lines.
    'TT420C2308': [
        { type: '膽道癌', lines: ['三線'] }
    ],
    // MK-9999-02A cohort wording explicitly lists pancreatic/CRC 2L and biliary 2/3L.
    'MK-9999-02A': [
        { type: '胰臟癌', lines: ['二線'] },
        { type: '膽道癌', lines: ['二線', '三線'] },
        { type: '大腸癌', lines: ['二線'] }
    ],
    // MK5909-005 explicitly lists pancreatic/CRC 2L, biliary 2/3L and gastric 3L+.
    'MK5909-005': [
        { type: '胃癌', lines: ['三線以上'] },
        { type: '胰臟癌', lines: ['二線'] },
        { type: '膽道癌', lines: ['二線', '三線'] },
        { type: '大腸癌', lines: ['二線'] }
    ],
    // SUFR-431 enrollment note says patients may have any number of prior therapies / later-line HCC.
    'TYR430-101': [
        { type: '肝癌', lines: ['多線'] }
    ]
};"""
    if anchor not in s:
        raise SystemExit('classification repair table anchor not found')
    s = s.replace(anchor, replacement, 1)

# -----------------------------------------------------------------------------
# 1) Provenance vocabulary. Keep provenance outside cancerTypes to avoid breaking
#    the established cancerTypes schema: trial.lineSources maps cancer|line -> source.
# -----------------------------------------------------------------------------
if MARKER not in s:
    anchor = "const TRIAL_CLASSIFICATION_REPAIR_VERSION = 'v4.3.3-20260820-gastric-line-repair';\n"
    block = anchor + """
// v4.3.4-line-provenance-20260820
const LINE_SOURCE_LABELS = {
    'manual': '人工設定',
    'curated-repair': '人工核對',
    'trial-title': '試驗標題明示',
    'cohort-explicit': 'Cohort 明示',
    'table-explicit': '線別欄位',
    'table-inherited': '⚠ 表格沿用',
    'auto-inferred': '⚠ 自動推論',
    'legacy': '? 舊資料未標記'
};
const LINE_SOURCE_REVIEW_REQUIRED = new Set(['table-inherited', 'auto-inferred', 'legacy']);
const lineSourceKey = (type, line) => `${normalizeFilterValue(normalizeCancerTypeLabel(type || '') || type || '')}|${normalizeFilterValue(normalizeTreatmentLine(line) || line || '')}`;
const getLineSourceLabel = (source) => LINE_SOURCE_LABELS[source] || LINE_SOURCE_LABELS.legacy;
const getLineSourceBadgeClass = (source) => {
    if (source === 'manual' || source === 'curated-repair') return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    if (source === 'trial-title' || source === 'cohort-explicit') return 'bg-blue-100 text-blue-800 border-blue-200';
    if (source === 'table-explicit') return 'bg-violet-100 text-violet-800 border-violet-200';
    if (LINE_SOURCE_REVIEW_REQUIRED.has(source)) return 'bg-amber-100 text-amber-900 border-amber-300';
    return 'bg-slate-100 text-slate-700 border-slate-200';
};
"""
    if anchor not in s:
        raise SystemExit('classification version anchor not found')
    s = s.replace(anchor, block, 1)

# -----------------------------------------------------------------------------
# 2) Curated repair should stamp provenance, then derive provenance for all other
#    cancer/line pairs from title/cohort/general text or table import source.
# -----------------------------------------------------------------------------
old = """    t.cancerTypes = repaired;
    t.cancerType = repaired[0].type || '';
    t.line = (repaired[0].lines || [])[0] || '';
    t.classificationRepairVersion = TRIAL_CLASSIFICATION_REPAIR_VERSION;
    t.classificationRepairReason = 'Curated correction of stale cancer/treatment-line mapping from legacy import.';
    return t;
};"""
new = """    t.cancerTypes = repaired;
    t.cancerType = repaired[0].type || '';
    t.line = (repaired[0].lines || [])[0] || '';
    t.classificationRepairVersion = TRIAL_CLASSIFICATION_REPAIR_VERSION;
    t.classificationRepairReason = 'Curated correction of stale cancer/treatment-line mapping from legacy import.';
    const sources = { ...(t.lineSources || {}) };
    repaired.forEach(ct => (ct.lines || []).forEach(line => { sources[lineSourceKey(ct.type, line)] = 'curated-repair'; }));
    t.lineSources = sources;
    return t;
};"""
if old in s:
    s = s.replace(old, new, 1)
elif "sources[lineSourceKey(ct.type, line)] = 'curated-repair'" not in s:
    raise SystemExit('applyKnownTrialClassificationRepair body anchor not found')

normalize_anchor = "const normalizeCancerTypes = (list) => mergeCancerTypes(list);\n"
if 'const annotateTrialLineSources' not in s:
    provenance_functions = normalize_anchor + """

const pairListHasCancerLine = (pairs, type, line) => (Array.isArray(pairs) ? pairs : []).some(ct =>
    valueMatches(ct.type, type) && Array.isArray(ct.lines) && ct.lines.some(v => valueMatches(v, line))
);

const getTrialLineSource = (trial, type, line) => {
    const sources = trial && trial.lineSources && typeof trial.lineSources === 'object' ? trial.lineSources : {};
    return sources[lineSourceKey(type, line)] || trial && trial.lineSourceDefault || 'legacy';
};

const annotateTrialLineSources = (trial) => {
    const t = { ...(trial || {}) };
    const sources = { ...(t.lineSources || {}) };
    const titlePairs = inferCancerLinePairsFromText(t.studyTitle || '');
    const eligibilityText = [t.inclusion, t.exclusion, t.comments].filter(Boolean).join(' ');
    const eligibilityPairs = inferCancerLinePairsFromText(eligibilityText);
    const hasCohortCue = /\bcohort\b|\barm\s*[a-z0-9]+\b|substudy|sub-study|specific\s+inclusion|part\s*[a-z0-9]+|組別|子試驗/i.test(eligibilityText);
    const cancerTypes = Array.isArray(t.cancerTypes) && t.cancerTypes.length
        ? t.cancerTypes
        : (t.cancerType && t.line ? [{ type: t.cancerType, lines: [t.line] }] : []);
    cancerTypes.forEach(ct => (ct.lines || []).forEach(line => {
        const key = lineSourceKey(ct.type, line);
        if (sources[key]) return;
        if (pairListHasCancerLine(titlePairs, ct.type, line)) sources[key] = 'trial-title';
        else if (hasCohortCue && pairListHasCancerLine(eligibilityPairs, ct.type, line)) sources[key] = 'cohort-explicit';
        else if (pairListHasCancerLine(eligibilityPairs, ct.type, line)) sources[key] = 'auto-inferred';
        else sources[key] = t.lineSourceDefault || 'legacy';
    }));
    t.lineSources = sources;
    return t;
};
"""
    if normalize_anchor not in s:
        raise SystemExit('normalizeCancerTypes anchor not found')
    s = s.replace(normalize_anchor, provenance_functions, 1)

old = """    // Known clinical corrections must win over stale legacy/Firestore classifications.
    t = applyKnownTrialClassificationRepair(t);
    return t;
};"""
new = """    // Known clinical corrections must win over stale legacy/Firestore classifications.
    t = applyKnownTrialClassificationRepair(t);
    // Stamp line provenance after final cancer/line normalization so stale parser guesses stay visible.
    t = annotateTrialLineSources(t);
    return t;
};"""
if old in s:
    s = s.replace(old, new, 1)
elif 't = annotateTrialLineSources(t);' not in s:
    raise SystemExit('sanitizeTrialForRuntime provenance anchor not found')

# -----------------------------------------------------------------------------
# 3) Future import provenance: distinguish an explicit line cell from a carried
#    merged-cell value, while content-derived pairs are reclassified by annotation.
# -----------------------------------------------------------------------------
old = """    if (mergedPairs.length) {
        out.cancerTypes = mergedPairs;
        out.cancerType = mergedPairs[0].type || out.cancerType || '';
        out.line = mergedPairs[0].lines && mergedPairs[0].lines.length ? mergedPairs[0].lines.join('、') : (out.line || '');
    }
    return out;
};"""
new = """    if (mergedPairs.length) {
        out.cancerTypes = mergedPairs;
        out.cancerType = mergedPairs[0].type || out.cancerType || '';
        out.line = mergedPairs[0].lines && mergedPairs[0].lines.length ? mergedPairs[0].lines.join('、') : (out.line || '');
    }
    if (!out.lineSourceDefault) {
        if (options.explicitLineOnRow) out.lineSourceDefault = 'table-explicit';
        else if (reliableInferredPairs.length || contextLinesForExplicitCancer.length) out.lineSourceDefault = 'auto-inferred';
        else if (out.line) out.lineSourceDefault = 'table-inherited';
        else out.lineSourceDefault = 'legacy';
    }
    return out;
};"""
if old in s:
    s = s.replace(old, new, 1)
elif "out.lineSourceDefault = 'table-explicit'" not in s:
    raise SystemExit('normalizeImportedTrialFields return anchor not found')

old = "parsed.push(normalizeImportedTrialFields(item, { explicitCancerOnRow }));"
new = "parsed.push(normalizeImportedTrialFields(item, { explicitCancerOnRow, explicitLineOnRow: Boolean(lineCell && isValidTreatmentLineText(normalizeTreatmentLine(lineCell))) }));"
if old in s:
    s = s.replace(old, new, 1)
elif 'explicitLineOnRow: Boolean(lineCell' not in s:
    raise SystemExit('table parser provenance anchor not found')

old = "const normalized = normalizeImportedTrialFields(fragment, { explicitCancerOnRow: cancerLine.explicitCancer });"
new = "const normalized = normalizeImportedTrialFields(fragment, { explicitCancerOnRow: cancerLine.explicitCancer, explicitLineOnRow: Boolean(raw.cancerLine && cancerLine.line) });"
if old in s:
    s = s.replace(old, new, 1)

# -----------------------------------------------------------------------------
# 4) Human edits: preserve existing provenance and mark only newly introduced
#    lines as manual.
# -----------------------------------------------------------------------------
old = """            cancerTypes: cancerTypes,
            id: isEdit ? form.id : Date.now(),"""
new = """            cancerTypes: cancerTypes,
            lineSources: (() => {
                const sources = { ...(form.lineSources || {}) };
                cancerTypes.forEach(ct => (ct.lines || []).forEach(line => {
                    const key = lineSourceKey(ct.type, line);
                    if (!sources[key]) sources[key] = 'manual';
                }));
                return sources;
            })(),
            id: isEdit ? form.id : Date.now(),"""
if old in s:
    s = s.replace(old, new, 1)
elif 'lineSources: (() =>' not in s:
    raise SystemExit('manual form provenance anchor not found')

# -----------------------------------------------------------------------------
# 5) Show provenance badge directly beside every cancer/line chip.
# -----------------------------------------------------------------------------
old = """                                tags.push(e('span', {
                                    key: idx + '-' + lineIdx,
                                    title: closed ? '此癌種 / 線數目前收滿或暫停收案' : '',
                                    className: closed
                                        ? 'px-3 py-1 bg-gray-200 text-gray-500 border border-gray-300 rounded-full text-sm line-through decoration-red-500 decoration-2'
                                        : 'px-3 py-1 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-full text-sm'
                                }, (closed ? '✕ ' : '') + ct.type + ' - ' + line));"""
new = """                                const lineSource = getTrialLineSource(trial, ct.type, line);
                                tags.push(e('span', {
                                    key: idx + '-' + lineIdx,
                                    title: (closed ? '此癌種 / 線數目前收滿或暫停收案；' : '') + '線別來源：' + getLineSourceLabel(lineSource),
                                    className: closed
                                        ? 'inline-flex items-center gap-1.5 px-3 py-1 bg-gray-200 text-gray-500 border border-gray-300 rounded-full text-sm line-through decoration-red-500 decoration-2'
                                        : 'inline-flex items-center gap-1.5 px-3 py-1 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-full text-sm'
                                },
                                    e('span', null, (closed ? '✕ ' : '') + ct.type + ' - ' + line),
                                    e('span', {className: 'px-1.5 py-0.5 rounded-full border text-[10px] leading-none no-underline ' + getLineSourceBadgeClass(lineSource)}, getLineSourceLabel(lineSource))
                                ));"""
if old in s:
    s = s.replace(old, new, 1)
elif "getLineSourceLabel(lineSource)" not in s:
    raise SystemExit('TrialCard provenance chip anchor not found')

# -----------------------------------------------------------------------------
# 6) Review-only filter: parser guesses / inherited lines / unmarked legacy data.
# -----------------------------------------------------------------------------
state_anchor = "    const [onlyOpenEnrollment, setOnlyOpenEnrollment] = useState(false);\n"
if 'onlyLineNeedsReview' not in s:
    if state_anchor not in s:
        raise SystemExit('App filter state anchor not found')
    s = s.replace(state_anchor, state_anchor + "    const [onlyLineNeedsReview, setOnlyLineNeedsReview] = useState(false);\n", 1)

trial_open_end = """const trialHasOpenEnrollment = (trial, selectedCancerType = '全部', selectedTreatmentLine = '全部') => {
    if (!trial || trial.isArchived) return false;
    if (isGloballyUnavailableTrial(trial) || isTrialNumericallyFull(trial)) return false;
    const pairs = getTrialCancerLinePairs(trial).filter(pair => {
        if (selectedCancerType !== '全部' && !valueMatches(pair.type, selectedCancerType)) return false;
        if (selectedTreatmentLine !== '全部' && !lineMatchesSelection(pair.line, selectedTreatmentLine)) return false;
        return true;
    });
    if (!pairs.length) return false;
    return pairs.some(pair => !isClosedTreatmentLine(pair.ct, pair.line));
};"""
if 'const trialHasLineSourceNeedingReview' not in s:
    review_fn = trial_open_end + """

const trialHasLineSourceNeedingReview = (trial, selectedCancerType = '全部', selectedTreatmentLine = '全部') => {
    if (!trial) return false;
    return getTrialCancerLinePairs(trial).some(pair => {
        if (selectedCancerType !== '全部' && !valueMatches(pair.type, selectedCancerType)) return false;
        if (selectedTreatmentLine !== '全部' && !lineMatchesSelection(pair.line, selectedTreatmentLine)) return false;
        return LINE_SOURCE_REVIEW_REQUIRED.has(getTrialLineSource(trial, pair.type, pair.line));
    });
};"""
    if trial_open_end not in s:
        raise SystemExit('trialHasOpenEnrollment anchor not found')
    s = s.replace(trial_open_end, review_fn, 1)

filter_anchor = """        if (onlyOpenEnrollment) {
            result = result.filter(t => trialHasOpenEnrollment(t, cancerType, selectedLine));
        }
        
        // 搜尋篩選"""
if 'trialHasLineSourceNeedingReview(t, cancerType, selectedLine)' not in s:
    filter_repl = """        if (onlyOpenEnrollment) {
            result = result.filter(t => trialHasOpenEnrollment(t, cancerType, selectedLine));
        }

        // 線別來源稽核：只顯示 parser 自動推論、表格沿用或尚未標記的舊資料。
        if (onlyLineNeedsReview) {
            result = result.filter(t => trialHasLineSourceNeedingReview(t, cancerType, selectedLine));
        }
        
        // 搜尋篩選"""
    if filter_anchor not in s:
        raise SystemExit('filtered provenance filter anchor not found')
    s = s.replace(filter_anchor, filter_repl, 1)

old_dep = "}, [trials, search, cancerType, selectedLine, showArchived, onlyOpenEnrollment]);"
new_dep = "}, [trials, search, cancerType, selectedLine, showArchived, onlyOpenEnrollment, onlyLineNeedsReview]);"
if old_dep in s:
    s = s.replace(old_dep, new_dep, 1)
elif new_dep not in s:
    raise SystemExit('filtered dependency anchor not found')

open_checkbox = """                e('label', {
                    className: 'flex items-center gap-2 cursor-pointer px-3 py-2 rounded-lg border font-medium ' +
                        (onlyOpenEnrollment ? 'bg-emerald-100 border-emerald-400 text-emerald-900' : 'bg-emerald-50 border-emerald-200 text-emerald-800')
                },
                    e('input', {
                        type: 'checkbox',
                        checked: onlyOpenEnrollment,
                        onChange: (ev) => setOnlyOpenEnrollment(ev.target.checked),
                        className: 'w-4 h-4'
                    }),
                    e('span', null, onlyOpenEnrollment ? '✓ 只顯示仍能收案（已啟用）' : '只顯示仍能收案')
                )"""
if "只顯示線別需核對" not in s:
    checkbox_repl = open_checkbox + ",\n" + """                e('label', {
                    className: 'flex items-center gap-2 cursor-pointer px-3 py-2 rounded-lg border font-medium ' +
                        (onlyLineNeedsReview ? 'bg-amber-100 border-amber-400 text-amber-950' : 'bg-amber-50 border-amber-200 text-amber-900')
                },
                    e('input', {
                        type: 'checkbox',
                        checked: onlyLineNeedsReview,
                        onChange: (ev) => setOnlyLineNeedsReview(ev.target.checked),
                        className: 'w-4 h-4'
                    }),
                    e('span', null, onlyLineNeedsReview ? '⚠ 只顯示線別需核對（已啟用）' : '只顯示線別需核對')
                )"""
    if open_checkbox not in s:
        raise SystemExit('open enrollment checkbox anchor not found')
    s = s.replace(open_checkbox, checkbox_repl, 1)

# Add a compact provenance legend below filter toggles.
legend_anchor = """            e('div', {className: 'mb-6 space-y-4'},"""
if "線別來源標記：" not in s:
    legend = """            e('div', {className: 'mb-4 flex flex-wrap items-center gap-2 text-xs text-slate-600'},
                e('span', {className: 'font-semibold'}, '線別來源標記：'),
                ['manual','curated-repair','trial-title','cohort-explicit','table-explicit','table-inherited','auto-inferred','legacy'].map(source =>
                    e('span', {key: source, className: 'px-2 py-1 rounded-full border ' + getLineSourceBadgeClass(source)}, getLineSourceLabel(source))
                )
            ),
""" + legend_anchor
    if legend_anchor not in s:
        raise SystemExit('filter legend anchor not found')
    s = s.replace(legend_anchor, legend, 1)

old_count = "'找到 ' + filtered.length + ' 個試驗' + (onlyOpenEnrollment ? '（已篩選仍能收案）' : '')"
new_count = "'找到 ' + filtered.length + ' 個試驗' + (onlyOpenEnrollment ? '（仍能收案）' : '') + (onlyLineNeedsReview ? '（線別需核對）' : '')"
if old_count in s:
    s = s.replace(old_count, new_count, 1)

# -----------------------------------------------------------------------------
# 7) Put the new dose calculator on the no-login clinical tools panel.
# -----------------------------------------------------------------------------
if "./tools/chemo-dose.html" not in s:
    renal_card = """                    e('a', {href: './tools/renal.html', target: '_blank', rel: 'noopener', className: toolButtonClass},
                        e('div', {className: 'font-semibold text-gray-900'}, '腎功能 / BSA 計算機'),
                        e('div', {className: 'text-xs text-gray-500 mt-1'}, 'Cockcroft-Gault、CKD-EPI 2021、MDRD、BSA、trial cutoff')
                    ),"""
    chemo_card = renal_card + """
                    e('a', {href: './tools/chemo-dose.html', target: '_blank', rel: 'noopener', className: toolButtonClass},
                        e('div', {className: 'font-semibold text-cyan-800'}, '化療 / 抗癌藥物劑量計算機'),
                        e('div', {className: 'text-xs text-gray-500 mt-1'}, 'BSA、IBW/AdjBW、mg/m²、mg/kg、dose reduction、rounding、Carboplatin AUC')
                    ),"""
    if renal_card not in s:
        raise SystemExit('clinical tools renal card anchor not found')
    s = s.replace(renal_card, chemo_card, 1)

# Version bump is deliberately narrow: visible application labels only.
s = s.replace('臨床試驗管理系統 v4.3.2 Firebase版', '臨床試驗管理系統 v4.3.4 Firebase版')
s = s.replace('臨床工具；目前包含 renal/BSA、腫瘤分期、CTCAE、RECIST/TLS 與抗癌藥物健保給付查詢。',
              '臨床工具；目前包含 renal/BSA、化療劑量、腫瘤分期、CTCAE、RECIST/TLS 與抗癌藥物健保給付查詢。')

p.write_text(s, encoding='utf-8')
print('Applied line provenance + chemo tool navigation patch')

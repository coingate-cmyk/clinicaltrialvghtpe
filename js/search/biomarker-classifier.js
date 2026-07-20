(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) {
        root.ClinicalTrialApp = root.ClinicalTrialApp || {};
        root.ClinicalTrialApp.search = Object.assign(root.ClinicalTrialApp.search || {}, api);
    }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    const HER2_MARKER = 'HER2';
    const STATUS = Object.freeze({
        POSITIVE: 'positive',
        NEGATIVE: 'negative',
        LOW: 'low',
        ANY: 'any',
        MENTIONED: 'mentioned',
        NONE: 'none',
        MIXED: 'mixed'
    });

    const ROLE = Object.freeze({
        ELIGIBILITY: 'eligibility',
        EXCLUSION: 'exclusion',
        TREATMENT_HISTORY: 'treatment-history',
        DESCRIPTIVE: 'descriptive'
    });

    const normalizeUnicode = (value) => String(value || '')
        .normalize('NFKC')
        .replace(/[–—−]/g, '-')
        .replace(/[＋]/g, '+')
        .replace(/[（]/g, '(')
        .replace(/[）]/g, ')')
        .replace(/\u00A0/g, ' ');

    const compactWhitespace = (value) => normalizeUnicode(value).replace(/[\t ]+/g, ' ').trim();

    const hasHer2Mention = (value) => /\bHER\s*-?\s*2\b|\bERBB\s*2\b/i.test(normalizeUnicode(value));

    const isHeading = (value, type) => {
        const text = compactWhitespace(value).replace(/[:：].*$/, '').trim();
        if (type === 'inclusion') return /^(?:inclusion(?: criteria)?|eligibility|主要收案|收案條件|納入條件)$/i.test(text);
        return /^(?:exclusion(?: criteria)?|主要排除|排除條件|排除標準)$/i.test(text);
    };

    const splitTrialTextIntoSegments = (trial) => {
        const fields = [
            ['studyTitle', trial && trial.studyTitle, ROLE.ELIGIBILITY],
            ['inclusion', trial && trial.inclusion, ROLE.ELIGIBILITY],
            ['exclusion', trial && trial.exclusion, ROLE.EXCLUSION],
            ['comments', trial && trial.comments, ROLE.DESCRIPTIVE]
        ];
        const segments = [];

        fields.forEach(([field, rawValue, defaultRole]) => {
            const source = normalizeUnicode(rawValue);
            if (!source.trim()) return;
            let role = defaultRole;
            const lines = source.split(/\r?\n/);

            lines.forEach((rawLine) => {
                let line = compactWhitespace(rawLine);
                if (!line) return;

                if (/^inclusion(?: criteria)?\s*[:：]?/i.test(line)) {
                    role = ROLE.ELIGIBILITY;
                    line = line.replace(/^inclusion(?: criteria)?\s*[:：]?/i, '').trim();
                } else if (/^exclusion(?: criteria)?\s*[:：]?/i.test(line)) {
                    role = ROLE.EXCLUSION;
                    line = line.replace(/^exclusion(?: criteria)?\s*[:：]?/i, '').trim();
                } else if (isHeading(line, 'inclusion')) {
                    role = ROLE.ELIGIBILITY;
                    return;
                } else if (isHeading(line, 'exclusion')) {
                    role = ROLE.EXCLUSION;
                    return;
                }

                const clauses = line.split(/(?<=[。；;])\s+|\s+(?=\d+[.)、]\s*)/).map(compactWhitespace).filter(Boolean);
                clauses.forEach((clause) => segments.push({ field, role, text: clause }));
            });
        });

        return segments;
    };

    const statusWindow = (text) => {
        const source = normalizeUnicode(text);
        const match = /\bHER\s*-?\s*2\b|\bERBB\s*2\b/i.exec(source);
        if (!match) return source;
        const start = Math.max(0, match.index - 55);
        const end = Math.min(source.length, match.index + match[0].length + 100);
        return source.slice(start, end);
    };

    const detectHer2Status = (text) => {
        const windowText = statusWindow(text);
        const normalized = compactWhitespace(windowText);

        const result = (status, statuses, ruleId, confidence) => ({ status, statuses, ruleId, confidence });

        const anyPattern = /regardless\s+of\s+HER\s*-?\s*2|any\s+HER\s*-?\s*2\s+status|HER\s*-?\s*2\s+status\s+(?:is\s+)?not\s+required|不限\s*HER\s*-?\s*2|HER\s*-?\s*2\s*不限/i;
        if (anyPattern.test(normalized)) return result(STATUS.ANY, [STATUS.ANY], 'HER2_ANY_STATUS', 0.98);

        const negativePattern = /非\s*HER\s*-?\s*2(?:\s*\/\s*neu)?\s*陽性|non\s*-?\s*HER\s*-?\s*2(?:\s*\/\s*neu)?\s*(?:positive|amplified)|HER\s*-?\s*2\s*(?:\(\s*-\s*\)|[- ]?(?:negative|negatve|陰性)|\s*非陽性)|HER\s*-?\s*2\s*:\s*(?:negative|陰性|-)|HER\s*-?\s*2\s+0\b/i;
        if (negativePattern.test(normalized)) return result(STATUS.NEGATIVE, [STATUS.NEGATIVE], 'HER2_NEGATIVE', 0.99);

        const lowPattern = /HER\s*-?\s*2\s*[- ]?low|HER\s*-?\s*2\s*低表現|IHC\s*1\s*\+|IHC\s*2\s*\+.{0,35}(?:ISH|FISH)\s*(?:negative|陰性|-(?=$|[\s,;)]))|(?:ISH|FISH)\s*(?:negative|陰性|-(?=$|[\s,;)])).{0,35}IHC\s*2\s*\+/i;
        if (lowPattern.test(normalized)) return result(STATUS.LOW, [STATUS.LOW], 'HER2_LOW', 0.99);

        const strongPositivePattern = /HER\s*-?\s*2\s*(?:\(\s*\+\s*\)|[- ]?(?:positive|postive|positve|陽性)|\s*3\s*\+)|HER\s*-?\s*2\s*:\s*(?:positive|陽性|\+)|IHC\s*2\s*\+.{0,35}(?:ISH|FISH)\s*(?:\+|positive|postive|陽性)|(?:ISH|FISH)\s*(?:\+|positive|postive|陽性).{0,35}IHC\s*2\s*\+|HER\s*-?\s*2.{0,35}(?:amplified|amplification|擴增)/i;
        if (strongPositivePattern.test(normalized)) return result(STATUS.POSITIVE, [STATUS.POSITIVE], 'HER2_POSITIVE', 0.99);

        const expressionRangePattern = /IHC\s*2\s*\+\s*(?:\/|or|或|至|~|-)\s*(?:IHC\s*)?3\s*\+|IHC\s*3\s*\+\s*(?:\/|or|或|至|~|-)\s*(?:IHC\s*)?2\s*\+/i;
        if (expressionRangePattern.test(normalized)) {
            return result(STATUS.MIXED, [STATUS.POSITIVE, STATUS.LOW], 'HER2_EXPRESSION_IHC2_OR_3', 0.9);
        }

        const ihc3PositivePattern = /IHC\s*3\s*\+/i;
        if (ihc3PositivePattern.test(normalized)) return result(STATUS.POSITIVE, [STATUS.POSITIVE], 'HER2_IHC3_POSITIVE', 0.96);

        return result(STATUS.MENTIONED, [], 'HER2_MENTION_ONLY', 0.55);
    };

    const isTreatmentHistoryContext = (text, detectedStatus) => {
        if (detectedStatus !== STATUS.MENTIONED) return false;
        const normalized = compactWhitespace(text);
        return /(?:prior|previous(?:ly)?|treated|received|exposure|用過|接受過|曾接受|先前接受).{0,45}(?:anti\s*-?\s*HER\s*-?\s*2|HER\s*-?\s*2\s*(?:therapy|treatment|治療))|anti\s*-?\s*HER\s*-?\s*2\s*(?:therapy|treatment|治療)/i.test(normalized);
    };

    const unique = (values) => Array.from(new Set(values));

    const classifyHER2 = (trial) => {
        const mentions = [];
        splitTrialTextIntoSegments(trial || {}).forEach((segment) => {
            if (!hasHer2Mention(segment.text)) return;
            const detected = detectHer2Status(segment.text);
            const role = isTreatmentHistoryContext(segment.text, detected.status)
                ? ROLE.TREATMENT_HISTORY
                : segment.role;
            mentions.push({
                marker: HER2_MARKER,
                status: detected.status,
                statuses: detected.statuses,
                role,
                field: segment.field,
                evidence: segment.text,
                ruleId: detected.ruleId,
                confidence: detected.confidence
            });
        });

        const eligibleStatuses = unique(mentions
            .filter((item) => item.role === ROLE.ELIGIBILITY)
            .flatMap((item) => item.statuses || [])
            .filter((status) => [STATUS.POSITIVE, STATUS.NEGATIVE, STATUS.LOW, STATUS.ANY].includes(status)));
        const excludedStatuses = unique(mentions
            .filter((item) => item.role === ROLE.EXCLUSION)
            .flatMap((item) => item.statuses || [])
            .filter((status) => [STATUS.POSITIVE, STATUS.NEGATIVE, STATUS.LOW].includes(status)));

        let summary = STATUS.NONE;
        if (eligibleStatuses.length > 1) summary = STATUS.MIXED;
        else if (eligibleStatuses.length === 1) summary = eligibleStatuses[0];
        else if (mentions.length) summary = STATUS.MENTIONED;

        return {
            marker: HER2_MARKER,
            summary,
            eligibleStatuses,
            excludedStatuses,
            mentions,
            mentioned: mentions.length > 0,
            excludesPositive: excludedStatuses.includes(STATUS.POSITIVE),
            hasTreatmentHistoryOnly: mentions.length > 0 && mentions.every((item) => item.role === ROLE.TREATMENT_HISTORY)
        };
    };

    const matchesHER2Status = (classification, requestedStatus) => {
        const data = classification || { eligibleStatuses: [], excludedStatuses: [], mentioned: false };
        const eligible = data.eligibleStatuses || [];
        const excluded = data.excludedStatuses || [];
        if (requestedStatus === 'anyMention') return Boolean(data.mentioned);
        if (requestedStatus === STATUS.POSITIVE) {
            if (excluded.includes(STATUS.POSITIVE) && !eligible.includes(STATUS.POSITIVE)) return false;
            return eligible.includes(STATUS.POSITIVE);
        }
        if (requestedStatus === STATUS.NEGATIVE) return eligible.includes(STATUS.NEGATIVE);
        if (requestedStatus === STATUS.LOW) return eligible.includes(STATUS.LOW);
        if (requestedStatus === 'nonPositive') {
            const explicitlyNonPositive = (eligible.includes(STATUS.NEGATIVE) || eligible.includes(STATUS.LOW))
                && !eligible.includes(STATUS.POSITIVE)
                && !eligible.includes(STATUS.ANY);
            return explicitlyNonPositive || excluded.includes(STATUS.POSITIVE);
        }
        if (requestedStatus === STATUS.ANY) return eligible.includes(STATUS.ANY);
        return false;
    };

    return {
        BIOMARKER_STATUS: STATUS,
        BIOMARKER_ROLE: ROLE,
        normalizeUnicode,
        splitTrialTextIntoSegments,
        classifyHER2,
        matchesHER2Status
    };
});
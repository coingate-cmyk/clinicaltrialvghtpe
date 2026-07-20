'use strict';

const assert = require('assert');
const biomarker = require('../js/search/biomarker-classifier.js');
const search = require('../js/search/search-engine.js');

const fixtures = {
    positive: {
        code: 'D702AC00001',
        studyTitle: 'HER2 陽性胃癌第一線治療',
        inclusion: 'HER2 (+); IHC 3+ or IHC 2+ with FISH-positive'
    },
    negative: {
        code: 'M24-977',
        studyTitle: 'First-line gastric cancer study',
        inclusion: '1. HER2(-)\n2. Measurable lesion'
    },
    low: {
        code: 'D967LC0001',
        studyTitle: 'Study for HER2 expression gastric cancer',
        inclusion: 'HER2 low (IHC 1+ or IHC 2+ with FISH-negative)'
    },
    excludesPositive: {
        code: '61186372COR3002',
        inclusion: 'Inclusion: KRAS, NRAS, and BRAF WT tumor\nExclusion:\nHER2-positive/amplified tumor'
    },
    positiveWithTreatmentExclusion: {
        code: 'SGNTUC-029',
        studyTitle: 'First-line therapy for HER2+ metastatic colorectal cancer',
        inclusion: 'Central confirmed HER2 3+ or ISH +\nExclusion\nHave previously been treated with anti-HER2 therapy'
    },
    mentionOnly: {
        code: 'D000',
        studyTitle: 'Study in tumors with HER2 expression',
        inclusion: 'No biomarker threshold is specified.'
    }
};

const positive = biomarker.classifyHER2(fixtures.positive);
assert.deepStrictEqual(positive.eligibleStatuses, ['positive']);
assert.strictEqual(biomarker.matchesHER2Status(positive, 'positive'), true);
assert.strictEqual(biomarker.matchesHER2Status(positive, 'negative'), false);

const negative = biomarker.classifyHER2(fixtures.negative);
assert.deepStrictEqual(negative.eligibleStatuses, ['negative']);
assert.strictEqual(biomarker.matchesHER2Status(negative, 'positive'), false);
assert.strictEqual(biomarker.matchesHER2Status(negative, 'negative'), true);
assert.strictEqual(biomarker.matchesHER2Status(negative, 'anyMention'), true);

const low = biomarker.classifyHER2(fixtures.low);
assert.deepStrictEqual(low.eligibleStatuses, ['low']);
assert.strictEqual(biomarker.matchesHER2Status(low, 'low'), true);
assert.strictEqual(biomarker.matchesHER2Status(low, 'positive'), false);

const excluded = biomarker.classifyHER2(fixtures.excludesPositive);
assert.deepStrictEqual(excluded.excludedStatuses, ['positive']);
assert.strictEqual(biomarker.matchesHER2Status(excluded, 'positive'), false);
assert.strictEqual(biomarker.matchesHER2Status(excluded, 'nonPositive'), true);
assert.strictEqual(biomarker.matchesHER2Status(excluded, 'negative'), false);

const positiveTreatment = biomarker.classifyHER2(fixtures.positiveWithTreatmentExclusion);
assert.strictEqual(biomarker.matchesHER2Status(positiveTreatment, 'positive'), true);
assert.strictEqual(positiveTreatment.mentions.some((item) => item.role === 'treatment-history'), true);

const anyStatus = biomarker.classifyHER2({ code: 'ANY', inclusion: '不限 HER2 (- or +)' });
assert.strictEqual(biomarker.matchesHER2Status(anyStatus, 'positive'), false);
assert.strictEqual(biomarker.matchesHER2Status(anyStatus, 'negative'), false);
assert.strictEqual(biomarker.matchesHER2Status(anyStatus, 'any'), true);

const mixedExpression = biomarker.classifyHER2({ code: 'MIXED', inclusion: 'HER2 expression IHC 2+ or 3+' });
assert.deepStrictEqual(mixedExpression.eligibleStatuses, ['positive', 'low']);
assert.strictEqual(biomarker.matchesHER2Status(mixedExpression, 'positive'), true);
assert.strictEqual(biomarker.matchesHER2Status(mixedExpression, 'low'), true);
assert.strictEqual(biomarker.matchesHER2Status(mixedExpression, 'nonPositive'), false);

const mentionOnly = biomarker.classifyHER2(fixtures.mentionOnly);
assert.strictEqual(mentionOnly.summary, 'mentioned');
assert.strictEqual(biomarker.matchesHER2Status(mentionOnly, 'anyMention'), true);
assert.strictEqual(biomarker.matchesHER2Status(mentionOnly, 'positive'), false);

assert.strictEqual(search.parseSearchQuery('HER2').filters[0].status, 'anyMention');
assert.strictEqual(search.parseSearchQuery('HER2+ 胃癌').filters[0].status, 'positive');
assert.strictEqual(search.parseSearchQuery('HER2+ 胃癌').freeText, '胃癌');
assert.strictEqual(search.parseSearchQuery('HER2 negative').filters[0].status, 'negative');
assert.strictEqual(search.parseSearchQuery('HER2 low').filters[0].status, 'low');

const precisePositive = search.searchTrials(Object.values(fixtures), 'HER2+').map((item) => item.trial.code);
assert.deepStrictEqual(precisePositive, ['D702AC00001', 'SGNTUC-029']);

const broadHer2 = search.searchTrials(Object.values(fixtures), 'HER2').map((item) => item.trial.code);
assert.strictEqual(broadHer2.includes('M24-977'), true);
assert.strictEqual(broadHer2.includes('61186372COR3002'), true);
assert.strictEqual(broadHer2.length, Object.keys(fixtures).length);

console.log('search-core.test.js: all tests passed');

#!/usr/bin/env python3
"""Integrate the structured search core into the current single-file app.

This script only:
1. loads the two external search scripts before the inline application script;
2. replaces the current keyword-only search block with the structured engine;
3. ranks active search results by search score before the existing clinical sort.

It does not change Firebase, parsing, trial data, filters, or UI markup.
"""

from __future__ import annotations

import argparse
from pathlib import Path

REACT_DOM_TAG = '    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>\n'
SEARCH_TAGS = (
    '    <script src="./js/search/biomarker-classifier.js"></script>\n'
    '    <script src="./js/search/search-engine.js"></script>\n'
)

OLD_START = """    const filtered = useMemo(() => {\n        let result = trials;\n"""
NEW_START = """    const filtered = useMemo(() => {\n        let result = trials;\n        const searchScores = new Map();\n"""

OLD_SEARCH = """        // 搜尋篩選\n        if (search) {\n            const q = search.toLowerCase().trim();\n            const normalize = (v) => String(v || '').toLowerCase().replace(/[\\s　]+/g, ' ').trim();\n            const haystack = (t) => [\n                t.studyTitle,\n                t.code,\n                t.sponsor,\n                t.pi,\n                t.nurse,\n                t.phone,\n                Array.isArray(t.cancerTypes) ? t.cancerTypes.map(ct => `${ct.type || ''} ${(ct.lines || []).join(' ')}`).join(' ') : '',\n                t.comments\n            ].map(normalize).join(' | ');\n            result = result.filter(t => haystack(t).includes(q));\n        }\n"""

NEW_SEARCH = """        // 搜尋篩選：優先使用結構化搜尋；外部模組未載入時保留原本的關鍵字搜尋。\n        if (search) {\n            const searchApi = window.ClinicalTrialApp && window.ClinicalTrialApp.search;\n            if (searchApi && typeof searchApi.searchTrials === 'function') {\n                const matches = searchApi.searchTrials(result, search);\n                result = matches.map(item => {\n                    searchScores.set(item.trial, item.result && Number(item.result.score) || 0);\n                    return item.trial;\n                });\n            } else {\n                const q = search.toLowerCase().trim();\n                const normalize = (v) => String(v || '').toLowerCase().replace(/[\\s　]+/g, ' ').trim();\n                const haystack = (t) => [\n                    t.studyTitle,\n                    t.code,\n                    t.sponsor,\n                    t.pi,\n                    t.nurse,\n                    t.phone,\n                    Array.isArray(t.cancerTypes) ? t.cancerTypes.map(ct => `${ct.type || ''} ${(ct.lines || []).join(' ')}`).join(' ') : '',\n                    t.comments\n                ].map(normalize).join(' | ');\n                result = result.filter(t => haystack(t).includes(q));\n            }\n        }\n"""

OLD_SORT = """        return [...result].sort((a, b) => {\n            const ak = trialSortKey(a);\n            const bk = trialSortKey(b);\n            return ak.cancerRank - bk.cancerRank || ak.lineRank - bk.lineRank || ak.code.localeCompare(bk.code);\n        });\n"""

NEW_SORT = """        return [...result].sort((a, b) => {\n            if (search) {\n                const scoreDifference = (searchScores.get(b) || 0) - (searchScores.get(a) || 0);\n                if (scoreDifference) return scoreDifference;\n            }\n            const ak = trialSortKey(a);\n            const bk = trialSortKey(b);\n            return ak.cancerRank - bk.cancerRank || ak.lineRank - bk.lineRank || ak.code.localeCompare(bk.code);\n        });\n"""


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"Expected exactly one {label}; found {count}")
    return source.replace(old, new, 1)


def integrate(source: str) -> str:
    if SEARCH_TAGS not in source:
        source = replace_once(source, REACT_DOM_TAG, REACT_DOM_TAG + SEARCH_TAGS, "ReactDOM script tag")
    source = replace_once(source, OLD_START, NEW_START, "filtered useMemo start")
    source = replace_once(source, OLD_SEARCH, NEW_SEARCH, "legacy search block")
    source = replace_once(source, OLD_SORT, NEW_SORT, "trial sort block")
    return source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()
    if bool(args.output) == bool(args.in_place):
        parser.error("choose exactly one of --output or --in-place")

    source = args.index.read_text(encoding="utf-8")
    updated = integrate(source)
    output = args.index if args.in_place else args.output
    assert output is not None
    output.write_text(updated, encoding="utf-8")
    print(f"output={output}")
    print("search_core_tags=2")
    print("structured_search_calls=1")


if __name__ == "__main__":
    main()

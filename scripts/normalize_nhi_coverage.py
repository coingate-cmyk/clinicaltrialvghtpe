#!/usr/bin/env python3
"""Normalize curated subsection IDs against official top-level 9.x sections.

The official snapshot is tracked at top-level section granularity (e.g. 9.12), while
curated records may cite a more specific subsection (e.g. 9.12.1). Coverage matching
must therefore compare on the top-level section to avoid false gaps/orphans.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "tools/nhi/assets"
DATA = ROOT / "tools/nhi/data"
COVERAGE = DATA / "coverage-report.json"
REVIEW = DATA / "review-queue.json"
CURRENT = DATA / "raw/current.json"
STATUS_JS = ASSETS / "nhi-status.js"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def top_section(value: str) -> str:
    value = str(value or "").strip()
    m = re.match(r"^(9\.\d{1,3})(?:\.\d+)*$", value)
    return m.group(1) if m else value


def load_curated_records() -> list[dict]:
    records = []
    for path in sorted(ASSETS.glob("data-*.js")):
        if path.name == "data-core.js":
            continue
        src = path.read_text(encoding="utf-8")
        m = re.search(r"push\(\.\.\.(\[[\s\S]*\])\s*\);", src)
        if not m:
            continue
        payload = json.loads(m.group(1))
        records.extend(x for x in payload if isinstance(x, dict))
    return records


def rewrite_status(coverage: dict, review: dict):
    text = STATUS_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.NHI_CHANGES\s*=\s*(\{[\s\S]*\})\s*;\s*$", text)
    if not m:
        raise RuntimeError("Cannot parse nhi-status.js")
    status = json.loads(m.group(1))
    status["coverage"] = {
        "missing_candidate_count": coverage.get("missing_candidate_count", 0),
        "orphan_count": coverage.get("orphan_count", 0),
        "review_item_count": review.get("item_count", 0),
    }
    STATUS_JS.write_text("window.NHI_CHANGES = " + json.dumps(status, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")


def main():
    coverage = load(COVERAGE)
    current = load(CURRENT)
    review = load(REVIEW)
    records = load_curated_records()
    official_sections = set(current.get("sections", {}))

    curated_pairs = {
        (top_section(r.get("section")), str(r.get("cancer", "")).strip())
        for r in records
        if r.get("section") and r.get("cancer")
    }

    candidates = []
    for row in coverage.get("by_cancer", []):
        cid = row.get("cancer")
        for sid in row.get("candidate_sections", []):
            candidates.append((top_section(sid), cid))

    missing_pairs = {(sid, cid) for sid, cid in candidates if (sid, cid) not in curated_pairs}
    old_missing = coverage.get("missing_candidates", [])
    missing_lookup = {(top_section(x.get("section_id")), x.get("cancer")): x for x in old_missing}
    new_missing = []
    for sid, cid in sorted(missing_pairs, key=lambda x: (x[1] or "", [int(n) for n in x[0].split(".")])):
        base = dict(missing_lookup.get((sid, cid), {}))
        if not base:
            base = {
                "section_id": sid,
                "cancer": cid,
                "cancer_name": cid,
                "title": current.get("sections", {}).get(sid, {}).get("text", "")[:180],
                "reason": "Official section mentions this cancer, but curated navigator has no matching section+cancer record.",
            }
        base["section_id"] = sid
        new_missing.append(base)

    new_orphans = []
    for r in records:
        raw_sid = str(r.get("section", "")).strip()
        sid = top_section(raw_sid)
        if sid and sid not in official_sections:
            new_orphans.append({
                "id": r.get("id"),
                "section_id": raw_sid,
                "top_section_id": sid,
                "cancer": r.get("cancer"),
                "reason": "Curated section not found in current official chapter 9 after top-level normalization.",
            })

    for row in coverage.get("by_cancer", []):
        cid = row.get("cancer")
        normalized_candidates = sorted({top_section(s) for s in row.get("candidate_sections", [])}, key=lambda x: [int(n) for n in x.split(".")])
        normalized_curated = sorted({sid for sid, cancer in curated_pairs if cancer == cid}, key=lambda x: [int(n) for n in x.split(".")])
        row["candidate_sections"] = normalized_candidates
        row["candidate_count"] = len(normalized_candidates)
        row["curated_sections"] = normalized_curated
        row["curated_count"] = len(normalized_curated)
        row["missing_count"] = sum(1 for sid, cancer in missing_pairs if cancer == cid)

    coverage["curated_record_count"] = len(records)
    coverage["missing_candidate_count"] = len(new_missing)
    coverage["orphan_count"] = len(new_orphans)
    coverage["missing_candidates"] = new_missing
    coverage["orphans"] = new_orphans
    coverage["normalization"] = "Curated subsection IDs are matched to official top-level 9.x sections."
    COVERAGE.write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")

    valid_missing = {(x["section_id"], x["cancer"]) for x in new_missing}
    preserved = [
        x for x in review.get("items", [])
        if x.get("type") != "coverage-gap"
        or (top_section(x.get("section_id")), x.get("cancer")) in valid_missing
    ]
    # Ensure every normalized missing candidate is represented exactly once.
    existing = {(top_section(x.get("section_id")), x.get("cancer")) for x in preserved if x.get("type") == "coverage-gap"}
    for item in new_missing:
        key = (item["section_id"], item["cancer"])
        if key not in existing:
            preserved.append({"priority": "normal", "type": "coverage-gap", **item})
    review["items"] = preserved
    review["item_count"] = len(preserved)
    REVIEW.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    rewrite_status(coverage, review)

    print(json.dumps({
        "official_sections": len(official_sections),
        "curated_records": len(records),
        "normalized_curated_pairs": len(curated_pairs),
        "missing_candidates": len(new_missing),
        "orphans": len(new_orphans),
        "review_items": len(preserved),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

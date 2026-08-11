#!/usr/bin/env python3
"""Build a browser-safe list of official NHI section candidates by cancer.

This is intentionally NOT curated clinical data: it exposes only section IDs and a
short heading/snippet derived from the official chapter-9 snapshot, so uncurated
cancers can already be browsed without inventing line/biomarker/reimbursement logic.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tools/nhi/data"
ASSETS = ROOT / "tools/nhi/assets"
COVERAGE = DATA / "coverage-report.json"
CURRENT = DATA / "raw/current.json"
OUT = ASSETS / "nhi-candidates.js"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def concise_title(section_id: str, text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(rf"^\s*{re.escape(section_id)}\s*[.．、:：-]?\s*", "", text)
    # Most headings place revision dates or the first numbered criterion after the drug/class name.
    parts = re.split(r"\s*[（(]\s*\d{2,3}[./]", text, maxsplit=1)
    title = parts[0].strip(" .：:") if parts else text
    if len(title) > 110:
        # Fall back to a readable leading snippet when the heading itself is complex.
        title = text[:110].rstrip() + "…"
    return title or section_id


def main():
    coverage = load(COVERAGE)
    current = load(CURRENT)
    sections = current.get("sections", {})
    out = {
        "meta": {
            "fetched_at": coverage.get("fetched_at"),
            "source_update": current.get("source", {}).get("source_update", ""),
            "source_url": current.get("source", {}).get("pdf") or current.get("source", {}).get("page"),
            "note": "Official-section candidates only; not yet clinically curated."
        },
        "by_cancer": {}
    }
    for row in coverage.get("by_cancer", []):
        cid = row.get("cancer")
        candidates = []
        for sid in row.get("candidate_sections", []):
            sec = sections.get(sid, {})
            candidates.append({
                "section_id": sid,
                "title": concise_title(sid, sec.get("text", "")),
                "official_only": True,
            })
        out["by_cancer"][cid] = {
            "name": row.get("name", cid),
            "group": row.get("group", ""),
            "candidate_count": len(candidates),
            "curated_count": row.get("curated_count", 0),
            "candidates": candidates,
        }
    ASSETS.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.NHI_CANDIDATES = " + json.dumps(out, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    print(f"Built {OUT}: {sum(x['candidate_count'] for x in out['by_cancer'].values())} candidate section appearances")


if __name__ == "__main__":
    main()

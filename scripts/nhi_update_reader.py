#!/usr/bin/env python3
"""Fallback NHI fetch through a read-through service when nhi.gov.tw blocks GitHub IPs.

The read-through service is transport only. Source URLs stored in output remain the
official NHI page/PDF URLs. Curated clinical records are never modified here.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests

from nhi_update import (
    PAGE_URL, ALIAS_FILE, CURRENT_FILE, RAW_DIR, SNAPSHOT_DIR, DATA_DIR, ASSET_DIR,
    CHANGES_FILE, COVERAGE_FILE, REVIEW_FILE, STATUS_JS,
    now_iso, sha, load_json, make_diff, make_coverage,
)

READER = "https://r.jina.ai/"
UA = "Mozilla/5.0 (compatible; clinicaltrialvghtpe NHI reader fallback/1.3)"


def reader_get(url: str) -> str:
    target = READER + url
    r = requests.get(target, timeout=120, headers={"User-Agent": UA, "Accept": "text/plain,text/markdown,*/*"})
    r.raise_for_status()
    text = r.text
    if len(text) < 5000:
        raise RuntimeError(f"Reader response unexpectedly small for {url}: {len(text)} chars")
    return text


def discover_from_markdown(md: str) -> dict:
    marker = re.search(r"第九節\s*抗癌瘤藥物[^\n]*", md)
    if not marker:
        raise RuntimeError("Reader page does not contain 第九節 抗癌瘤藥物")
    tail = md[marker.end():marker.end()+7000]
    urls = re.findall(r"https://www\.nhi\.gov\.tw/[^\s)\]>\"']+", tail)
    out = {"page": PAGE_URL, "label": marker.group(0).strip(), "transport": "reader-proxy"}
    for url in urls:
        clean = url.rstrip(".,;：，")
        if re.search(r"\.pdf(?:\?|$)", clean, re.I):
            out.setdefault("pdf", clean)
        elif re.search(r"\.odt(?:\?|$)", clean, re.I):
            out.setdefault("odt", clean)
        elif re.search(r"\.doc(?:\?|$)", clean, re.I):
            out.setdefault("doc", clean)
        if all(k in out for k in ("pdf", "odt", "doc")):
            break
    m = re.search(r"(\d{3}[./]\d{1,2}[./]\d{1,2})\s*更新", out["label"])
    out["source_update"] = m.group(1) if m else ""
    if "pdf" not in out:
        raise RuntimeError("Cannot discover official chapter 9 PDF URL after chapter marker")
    return out


def clean_reader_text(md: str) -> str:
    """Remove Markdown decoration but preserve document order and enough separators."""
    cleaned = []
    for raw in md.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*]\s+", "", line)
        line = line.replace("**", "").replace("__", "")
        line = line.replace("．", ".").replace("。", ".")
        line = line.strip("| ")
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            cleaned.append(line)
    text = "\n".join(cleaned)
    if len(text) < 5000:
        raise RuntimeError(f"Reader PDF text unexpectedly small: {len(text)} chars")
    return text


def section_number_pattern(n: int) -> re.Pattern:
    # PDF extraction occasionally inserts spaces inside a number: `9.1 2.1` for 9.12.1.
    digits = r"\s*".join(re.escape(ch) for ch in str(n))
    return re.compile(
        rf"(?<!\d)9\s*\.\s*{digits}(?!\s*\d)(?:\s*\.\s*\d+)?",
        re.I,
    )


def is_likely_heading(text: str, match: re.Match) -> bool:
    before = text[max(0, match.start()-35):match.start()]
    after = text[match.end():match.end()+80].lstrip(" .、:：|-–—\n")
    # Explicit body references are common in reimbursement rules; do not use them as boundaries.
    if re.search(r"(?:依|符合|參照|詳見|請見|依據)\s*$", before):
        return False
    if re.match(r"(?:規定|之規定|項規定|條規定|給付規定|辦理)", after):
        return False
    # Headings normally introduce a drug/class name or deletion marker and are not bare references.
    return bool(after)


def find_section_heading(text: str, n: int, start: int) -> re.Match | None:
    pat = section_number_pattern(n)
    fallback = None
    for m in pat.finditer(text, start):
        if fallback is None:
            fallback = m
        if is_likely_heading(text, m):
            return m
        # Do not scan arbitrarily far past the first few candidates for the same number.
        if m.start() - (fallback.start() if fallback else m.start()) > 25000:
            break
    return fallback


def split_reader_sections(text: str) -> dict:
    """Split chapter 9 by ordered section-number positions, independent of PDF line wrapping."""
    headings: list[tuple[int, re.Match]] = []
    cursor = 0
    # Current chapter has ~130 top-level numbers; leave headroom for future additions.
    for n in range(1, 251):
        m = find_section_heading(text, n, cursor)
        if not m:
            continue
        # Reject absurd backward/duplicate situations; positions must advance.
        if m.start() < cursor:
            continue
        headings.append((n, m))
        cursor = m.start() + 1

    if len(headings) < 80:
        preview = [(n, m.start(), text[m.start():m.start()+90].replace("\n", " ")) for n, m in headings[:30]]
        raise RuntimeError(f"Reader positional parser found only {len(headings)} sections; preview={preview}")

    sections = {}
    for idx, (n, m) in enumerate(headings):
        end = headings[idx+1][1].start() if idx+1 < len(headings) else len(text)
        body = text[m.start():end].strip()
        # Canonicalize the boundary only; preserve the rest of official text.
        body = re.sub(section_number_pattern(n), f"9.{n}", body, count=1)
        sections[f"9.{n}"] = {"text": body, "sha256": sha(body)}

    if "9.1" not in sections:
        raise RuntimeError("Chapter-9 sanity check failed: 9.1 missing")
    return sections


def main():
    for d in (DATA_DIR, RAW_DIR, SNAPSHOT_DIR, ASSET_DIR):
        d.mkdir(parents=True, exist_ok=True)
    aliases = load_json(ALIAS_FILE, {})
    if len(aliases) < 20:
        raise RuntimeError("Cancer alias taxonomy looks incomplete")

    fetched_at = now_iso()
    page_md = reader_get(PAGE_URL)
    sources = discover_from_markdown(page_md)
    print("Reader selected official chapter-9 PDF:", sources["pdf"])
    pdf_md = reader_get(sources["pdf"])
    document_text = clean_reader_text(pdf_md)
    sections = split_reader_sections(document_text)
    previous = load_json(CURRENT_FILE, {})
    old_sections = previous.get("sections", {}) if isinstance(previous, dict) else {}

    source_hash = sha(pdf_md)
    current = {
        "schema_version": "nhi-ch9-source-v1",
        "fetched_at": fetched_at,
        "source": sources,
        "odt_sha256": source_hash,
        "transport_note": "Text fetched through reader proxy because nhi.gov.tw blocks GitHub-hosted runner IPs; official source URL retained.",
        "paragraph_count": document_text.count("\n") + 1,
        "section_count": len(sections),
        "sections": sections,
    }
    changes = make_diff(old_sections, sections, fetched_at) if old_sections else {
        "status": "ok", "fetched_at": fetched_at, "baseline_created": True, "change_count": 0, "changes": []
    }
    coverage, _ = make_coverage(sections, aliases, fetched_at)
    changed_ids = {x.get("section_id") for x in changes.get("changes", [])}
    review_items = []
    for item in coverage.get("missing_candidates", []):
        review_items.append({"priority": "high" if item["section_id"] in changed_ids else "normal", "type": "coverage-gap", **item})
    for item in changes.get("changes", []):
        sid = item.get("section_id")
        if not any(x.get("section_id") == sid for x in review_items):
            review_items.append({"priority": "high", "type": "section-change", "section_id": sid, "title": item.get("title", ""), "change_type": item.get("change_type", "modified")})
    review = {"status": "ok", "fetched_at": fetched_at, "item_count": len(review_items), "items": review_items}

    source_changed = previous.get("odt_sha256") != source_hash if previous else True
    if source_changed and previous:
        old_date = (previous.get("fetched_at") or "previous")[:10]
        snapshot = SNAPSHOT_DIR / f"{old_date}.json"
        if not snapshot.exists():
            snapshot.write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding="utf-8")

    CURRENT_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    CHANGES_FILE.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
    COVERAGE_FILE.write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
    REVIEW_FILE.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")

    status = {
        **changes,
        "transport": "reader-proxy",
        "source_update": sources.get("source_update", ""),
        "source_label": sources.get("label", ""),
        "source_url": sources.get("pdf") or sources.get("page"),
        "section_count": len(sections),
        "coverage": {
            "missing_candidate_count": coverage.get("missing_candidate_count", 0),
            "orphan_count": coverage.get("orphan_count", 0),
            "review_item_count": review.get("item_count", 0),
        },
    }
    STATUS_JS.write_text("window.NHI_CHANGES = " + json.dumps(status, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    print(json.dumps({
        "transport": "reader-proxy",
        "source_update": sources.get("source_update"),
        "sections": len(sections),
        "changes": changes.get("change_count", 0),
        "coverage_gaps": coverage.get("missing_candidate_count", 0),
        "review_items": review.get("item_count", 0),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

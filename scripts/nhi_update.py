#!/usr/bin/env python3
"""Fetch NHI chapter 9, diff section-level text, and audit cancer coverage.

Safety principle: this script NEVER edits curated indication records. It only updates
raw official snapshots, section diffs, and a review queue for human verification.
"""
from __future__ import annotations

import difflib
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PAGE_URL = "https://www.nhi.gov.tw/ch/cp-7593-ad2a9-3397-1.html"
DATA_DIR = ROOT / "tools/nhi/data"
RAW_DIR = DATA_DIR / "raw"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
ASSET_DIR = ROOT / "tools/nhi/assets"
ALIAS_FILE = ROOT / "tools/nhi/config/cancer_aliases.json"
CURRENT_FILE = RAW_DIR / "current.json"
CHANGES_FILE = DATA_DIR / "changes.json"
COVERAGE_FILE = DATA_DIR / "coverage-report.json"
REVIEW_FILE = DATA_DIR / "review-queue.json"
STATUS_JS = ASSET_DIR / "nhi-status.js"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "clinicaltrialvghtpe NHI updater/1.0 (+GitHub Actions; clinical reference mirror)"})


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha(text_or_bytes) -> str:
    b = text_or_bytes if isinstance(text_or_bytes, bytes) else str(text_or_bytes).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def discover_sources() -> dict:
    r = SESSION.get(PAGE_URL, timeout=45)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    label = soup.find(string=re.compile(r"第九節\s*抗癌瘤藥物"))
    if not label:
        raise RuntimeError("Cannot find 第九節 抗癌瘤藥物 on NHI page")
    container = label.find_parent("li") or label.parent
    anchors = container.find_all("a", href=True) if container else []
    links = {}
    for a in anchors:
        href = urljoin(PAGE_URL, a.get("href", ""))
        text = a.get_text(" ", strip=True).lower()
        for ext in ("odt", "pdf", "doc"):
            if ext in text or re.search(rf"\.{ext}(?:\?|$)", href, re.I):
                links.setdefault(ext, href)
    # NHI HTML occasionally separates the title and download links. Fallback: score nearby anchors.
    if "odt" not in links:
        block = str(container or "")
        parent = (container.parent if container else None)
        candidates = (parent.find_all("a", href=True) if parent else soup.find_all("a", href=True))
        for a in candidates:
            href = urljoin(PAGE_URL, a.get("href", ""))
            if re.search(r"\.odt(?:\?|$)", href, re.I):
                nearby = a.parent.get_text(" ", strip=True) if a.parent else ""
                if "第九節" in nearby or "抗癌瘤藥物" in nearby:
                    links["odt"] = href
                    break
    if "odt" not in links:
        raise RuntimeError("Cannot discover chapter 9 ODT URL")
    label_text = str(label).strip()
    m = re.search(r"\((\d{3}[./]\d{1,2}[./]\d{1,2})更新\)", label_text)
    return {"page": PAGE_URL, "label": label_text, "source_update": m.group(1) if m else "", **links}


def download(url: str) -> bytes:
    r = SESSION.get(url, timeout=90)
    r.raise_for_status()
    if len(r.content) < 5000:
        raise RuntimeError(f"Downloaded file unexpectedly small: {len(r.content)} bytes")
    return r.content


def extract_odt_paragraphs(blob: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        xml = zf.read("content.xml")
    root = ET.fromstring(xml)
    paragraphs = []
    for elem in root.iter():
        if elem.tag.endswith("}p") or elem.tag.endswith("}h"):
            text = "".join(elem.itertext())
            text = re.sub(r"[\t\xa0 ]+", " ", text).strip()
            if text:
                paragraphs.append(text)
    if len(paragraphs) < 100:
        raise RuntimeError(f"ODT parse produced too few paragraphs: {len(paragraphs)}")
    return paragraphs


SECTION_RE = re.compile(r"^\s*(9\.\d{1,3})(?!\.\d)\s*(?:[.．、:：-]\s*)?(.*)$")


def split_sections(paragraphs: list[str]) -> dict:
    sections = {}
    current_id = None
    current_lines = []
    for p in paragraphs:
        m = SECTION_RE.match(p)
        if m:
            sid = m.group(1)
            # A real section heading starts at paragraph start and section IDs should be unique.
            if sid not in sections and sid != current_id:
                if current_id:
                    text = "\n".join(current_lines).strip()
                    sections[current_id] = {"text": text, "sha256": sha(text)}
                current_id = sid
                current_lines = [p]
                continue
        if current_id:
            current_lines.append(p)
    if current_id:
        text = "\n".join(current_lines).strip()
        sections[current_id] = {"text": text, "sha256": sha(text)}
    if len(sections) < 80:
        preview = ", ".join(list(sections)[:20])
        raise RuntimeError(f"Section parser found only {len(sections)} sections ({preview})")
    return sections


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def section_title(text: str) -> str:
    return (text.splitlines()[0] if text else "")[:180]


def make_diff(old_sections: dict, new_sections: dict, fetched_at: str) -> dict:
    changes = []
    old_keys, new_keys = set(old_sections), set(new_sections)
    for sid in sorted(new_keys - old_keys, key=lambda x: [int(n) for n in x.split(".")]):
        changes.append({"section_id": sid, "change_type": "added", "title": section_title(new_sections[sid]["text"])})
    for sid in sorted(old_keys - new_keys, key=lambda x: [int(n) for n in x.split(".")]):
        changes.append({"section_id": sid, "change_type": "removed", "title": section_title(old_sections[sid]["text"])})
    for sid in sorted(old_keys & new_keys, key=lambda x: [int(n) for n in x.split(".")]):
        if old_sections[sid].get("sha256") == new_sections[sid].get("sha256"):
            continue
        old_lines = old_sections[sid].get("text", "").splitlines()
        new_lines = new_sections[sid].get("text", "").splitlines()
        diff = list(difflib.unified_diff(old_lines, new_lines, fromfile="previous", tofile="current", lineterm=""))
        changes.append({
            "section_id": sid,
            "change_type": "modified",
            "title": section_title(new_sections[sid]["text"]),
            "diff": diff[:500],
            "diff_truncated": len(diff) > 500,
        })
    return {"status": "ok", "fetched_at": fetched_at, "change_count": len(changes), "changes": changes}


def alias_found(text: str, alias: str) -> bool:
    if not alias:
        return False
    if re.fullmatch(r"[A-Za-z0-9+\-/ ]+", alias):
        pattern = r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])"
        return re.search(pattern, text, re.I) is not None
    return alias in text


def cancer_candidates(text: str, aliases: dict) -> list[str]:
    return [cid for cid, cfg in aliases.items() if any(alias_found(text, a) for a in cfg.get("aliases", []))]


def load_curated_records() -> list[dict]:
    records = []
    for path in sorted(ASSET_DIR.glob("data-*.js")):
        if path.name in {"data-core.js"}:
            continue
        src = path.read_text(encoding="utf-8")
        m = re.search(r"push\(\.\.\.(\[[\s\S]*\])\s*\);", src)
        if not m:
            continue
        try:
            payload = json.loads(m.group(1))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Cannot parse curated JSON in {path}: {exc}") from exc
        for item in payload:
            if isinstance(item, dict):
                records.append(item)
    return records


def make_coverage(sections: dict, aliases: dict, fetched_at: str) -> tuple[dict, list[dict]]:
    records = load_curated_records()
    curated_pairs = {(str(r.get("section", "")).strip(), str(r.get("cancer", "")).strip()) for r in records}
    candidates = []
    missing = []
    for sid, section in sections.items():
        cancers = cancer_candidates(section.get("text", ""), aliases)
        if not cancers:
            continue
        candidates.append({"section_id": sid, "cancers": cancers})
        for cid in cancers:
            if (sid, cid) not in curated_pairs:
                missing.append({
                    "section_id": sid,
                    "cancer": cid,
                    "cancer_name": aliases.get(cid, {}).get("name", cid),
                    "title": section_title(section.get("text", "")),
                    "reason": "Official section mentions this cancer, but curated navigator has no matching section+cancer record.",
                })
    orphan = []
    for r in records:
        sid, cid = str(r.get("section", "")).strip(), str(r.get("cancer", "")).strip()
        if sid and sid not in sections:
            orphan.append({"id": r.get("id"), "section_id": sid, "cancer": cid, "reason": "Curated section not found in current official chapter 9."})
    coverage_by_cancer = []
    for cid, cfg in aliases.items():
        candidate_sections = sorted({x["section_id"] for x in candidates if cid in x["cancers"]})
        curated_sections = sorted({sid for sid, cancer in curated_pairs if cancer == cid})
        coverage_by_cancer.append({
            "cancer": cid,
            "name": cfg.get("name", cid),
            "group": cfg.get("group", "Other"),
            "candidate_sections": candidate_sections,
            "candidate_count": len(candidate_sections),
            "curated_sections": curated_sections,
            "curated_count": len(curated_sections),
            "missing_count": sum(1 for x in missing if x["cancer"] == cid),
        })
    report = {
        "status": "ok",
        "fetched_at": fetched_at,
        "official_section_count": len(sections),
        "curated_record_count": len(records),
        "candidate_pair_count": sum(len(x["cancers"]) for x in candidates),
        "missing_candidate_count": len(missing),
        "orphan_count": len(orphan),
        "by_cancer": coverage_by_cancer,
        "missing_candidates": missing,
        "orphans": orphan,
    }
    return report, records


def main():
    for d in (DATA_DIR, RAW_DIR, SNAPSHOT_DIR, ASSET_DIR):
        d.mkdir(parents=True, exist_ok=True)
    aliases = load_json(ALIAS_FILE, {})
    if len(aliases) < 20:
        raise RuntimeError("Cancer alias taxonomy looks incomplete")

    fetched_at = now_iso()
    sources = discover_sources()
    odt = download(sources["odt"])
    paragraphs = extract_odt_paragraphs(odt)
    sections = split_sections(paragraphs)
    previous = load_json(CURRENT_FILE, {})
    old_sections = previous.get("sections", {}) if isinstance(previous, dict) else {}

    current = {
        "schema_version": "nhi-ch9-source-v1",
        "fetched_at": fetched_at,
        "source": sources,
        "odt_sha256": sha(odt),
        "paragraph_count": len(paragraphs),
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

    source_changed = previous.get("odt_sha256") != current["odt_sha256"] if previous else True
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
        "source_update": sources.get("source_update"),
        "sections": len(sections),
        "changes": changes.get("change_count", 0),
        "coverage_gaps": coverage.get("missing_candidate_count", 0),
        "review_items": review.get("item_count", 0),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

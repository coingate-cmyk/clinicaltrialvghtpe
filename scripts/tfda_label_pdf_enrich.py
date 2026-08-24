#!/usr/bin/env python3
"""Conservatively enrich TFDA oncology mappings with indication-specific dose/frequency.

Safety rules:
1. Never search the whole insert for a nearby cancer word and call that a dose.
2. First isolate the official Dosage/Administration section.
3. For multi-indication licences, expose dose chips only from an explicit cancer-specific
   subsection inside that dosage section.
4. A general dosage section may be used only when the approved-indication text maps to one
   cancer category and that category matches the NHI record.
5. Otherwise keep the official permit/insert link but withhold dose/frequency instead of guessing.
"""
from __future__ import annotations

import io
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "tools/nhi/assets"
CONFIG_DIR = ROOT / "tools/nhi/config"
TFDA_JS = ASSET_DIR / "tfda-labels.js"
CANCER_ALIASES = CONFIG_DIR / "cancer_aliases.json"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36",
    "Accept": "application/pdf,text/html,*/*",
    "Referer": "https://mcp.fda.gov.tw/",
})

DOSE_RE = re.compile(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*(?:mcg|μg|ug|mg|g)(?:\s*/\s*(?:kg|m2|m²))?(?![A-Za-z0-9])", re.I)
FREQ_PATTERNS = [
    re.compile(r"每\s*[一二三四五六七八九十\d]+\s*(?:週|周|天|日|小時)\s*(?:一次|1次)?", re.I),
    re.compile(r"(?:每|一)\s*(?:日|天)\s*[一二三四五六七八九十\d]+\s*次", re.I),
    re.compile(r"一天\s*[一二三四五六七八九十\d]+\s*次", re.I),
    re.compile(r"\bq\s*\d+\s*(?:w|wk|week|weeks|d|day|days|h|hour|hours)\b", re.I),
    re.compile(r"every\s+\d+\s+(?:week|weeks|day|days|hour|hours)", re.I),
    re.compile(r"once\s+every\s+\d+\s+(?:week|weeks|day|days)", re.I),
]
DOSAGE_HEADINGS = [
    "用法及用量", "用法用量", "劑量與給藥方式", "劑量和給藥方式", "建議劑量",
    "dosage and administration", "dose and administration", "recommended dosage", "recommended dose",
]
STOP_HEADINGS = [
    "禁忌", "警語", "注意事項", "不良反應", "交互作用", "特殊族群", "藥物動力學",
    "contraindication", "warnings", "adverse reactions", "drug interactions", "use in specific populations",
]
PLACEHOLDER_DOSE_RE = re.compile(r"^(?:請)?(?:詳|參閱|請參閱).{0,12}(?:仿單|說明書).{0,8}$")


def norm_text(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s or "")).replace("\u00a0", " ")


def clean(s: str) -> str:
    return re.sub(r"[ \t]+", " ", norm_text(s)).strip()


def compact_key(s: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", norm_text(s).lower())


def load_tfda() -> dict:
    src = TFDA_JS.read_text(encoding="utf-8")
    m = re.match(r"\s*window\.TFDA_LABELS\s*=\s*(\{[\s\S]*\});\s*$", src)
    if not m:
        raise RuntimeError("Cannot parse TFDA_LABELS JS")
    return json.loads(m.group(1))


def save_tfda(data: dict) -> None:
    TFDA_JS.write_text("window.TFDA_LABELS = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_curated_cancers() -> dict[str, str]:
    out = {}
    for path in sorted(ASSET_DIR.glob("data-*.js")):
        if path.name == "data-core.js":
            continue
        src = path.read_text(encoding="utf-8")
        m = re.search(r"push\(\.\.\.(\[[\s\S]*\])\s*\);", src)
        if not m:
            continue
        try:
            rows = json.loads(m.group(1))
        except Exception:
            continue
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                out[str(row["id"])] = str(row.get("cancer", ""))
    return out


def split_urls(value: str) -> list[str]:
    value = clean(value)
    if not value:
        return []
    return [p.strip() for p in re.split(r";(?=https?://)", value) if p.strip().startswith("http")]


def fetch_pdf_text(urls: list[str]) -> tuple[str, str]:
    last_error = ""
    for url in urls:
        try:
            r = SESSION.get(url, timeout=60, allow_redirects=True)
            r.raise_for_status()
            blob = r.content
            if not blob.startswith(b"%PDF"):
                last_error = f"not-pdf:{r.headers.get('content-type','')}"
                continue
            reader = PdfReader(io.BytesIO(blob), strict=False)
            chunks = []
            for page in reader.pages:
                try:
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""
                if txt:
                    chunks.append(txt)
            text = "\n".join(chunks)
            if len(text.strip()) >= 200:
                return norm_text(text), url
            last_error = "pdf-no-text"
        except Exception as exc:
            last_error = type(exc).__name__
    return "", last_error


def uniq(values: list[str], limit=10) -> list[str]:
    out, seen = [], set()
    for v in values:
        v = clean(v)
        k = compact_key(v)
        if v and k and k not in seen:
            seen.add(k)
            out.append(v)
        if len(out) >= limit:
            break
    return out


def mentions(text: str) -> tuple[list[str], list[str]]:
    doses = uniq([m.group(0) for m in DOSE_RE.finditer(text)], 8)
    freqs = []
    for pat in FREQ_PATTERNS:
        freqs.extend(m.group(0) for m in pat.finditer(text))
    return doses, uniq(freqs, 8)


def alias_terms_for_cancer(cancer_id: str, aliases: dict) -> list[str]:
    cfg = aliases.get(cancer_id, {}) if isinstance(aliases, dict) else {}
    vals = []
    if isinstance(cfg, dict):
        vals.extend(cfg.get("aliases", []) or [])
        vals.append(cfg.get("name", ""))
    out = []
    for value in vals:
        value = clean(value)
        if len(value) < 2:
            continue
        # Avoid ultra-generic aliases as subsection headings.
        if compact_key(value) in {"cancer", "tumor", "tumour", "solidtumor", "solidtumour", "癌", "腫瘤"}:
            continue
        if value.lower() not in {x.lower() for x in out}:
            out.append(value)
    return sorted(out, key=len, reverse=True)


def all_heading_terms(aliases: dict) -> list[tuple[str, str]]:
    rows = []
    for cid in aliases:
        for term in alias_terms_for_cancer(cid, aliases):
            if len(term) >= 2:
                rows.append((cid, term))
    return sorted(rows, key=lambda x: len(x[1]), reverse=True)


def indication_cancer_ids(indication: str, aliases: dict) -> set[str]:
    low = norm_text(indication).lower()
    found = set()
    for cid in aliases:
        for term in alias_terms_for_cancer(cid, aliases):
            if term.lower() in low:
                found.add(cid)
                break
    return found


def dosage_section(text: str) -> str:
    low = text.lower()
    starts = []
    for heading in DOSAGE_HEADINGS:
        pos = low.find(heading.lower())
        if pos >= 0:
            starts.append(pos)
    if not starts:
        return ""
    start = min(starts)
    # Inserts may have long tables; allow a larger section but stop at the next major safety heading.
    end = min(len(text), start + 30000)
    tail_low = low[start + 80:end]
    stops = []
    for heading in STOP_HEADINGS:
        p = tail_low.find(heading.lower())
        if p >= 600:
            stops.append(start + 80 + p)
    if stops:
        end = min(stops)
    return text[start:end]


def looks_like_heading(line: str) -> bool:
    s = clean(line)
    if not s or len(s) > 180:
        return False
    if re.match(r"^\s*(?:\d+(?:\.\d+){1,3}|[一二三四五六七八九十]+[、.．])\s*", s):
        return True
    # A short line without sentence punctuation is commonly a PDF subsection heading.
    return len(s) <= 70 and not re.search(r"[。；;]", s)


def specific_dosage_subsection(section: str, target_cancer: str, aliases: dict) -> str:
    target_terms = alias_terms_for_cancer(target_cancer, aliases)
    if not target_terms:
        return ""
    lines = section.splitlines()
    starts = []
    for i, raw in enumerate(lines):
        line = clean(raw)
        low = line.lower()
        if not looks_like_heading(line):
            continue
        for term in target_terms:
            if term.lower() in low:
                score = 0
                if re.match(r"^\s*\d+(?:\.\d+){1,3}", line):
                    score += 3
                if compact_key(line) == compact_key(term):
                    score += 3
                if len(line) <= 90:
                    score += 1
                starts.append((score, i))
                break
    if not starts:
        return ""
    _, start_i = max(starts, key=lambda x: (x[0], -x[1]))

    heading_terms = all_heading_terms(aliases)
    end_i = min(len(lines), start_i + 80)
    start_line = clean(lines[start_i])
    num_match = re.match(r"^\s*(\d+)\.(\d+)", start_line)
    parent_major = num_match.group(1) if num_match else None
    current_minor = int(num_match.group(2)) if num_match else None

    for j in range(start_i + 1, min(len(lines), start_i + 100)):
        line = clean(lines[j])
        if not line:
            continue
        # Strongest stop: next sibling numbered subsection (e.g. 6.1 -> 6.2).
        nm = re.match(r"^\s*(\d+)\.(\d+)\b", line)
        if parent_major and nm and nm.group(1) == parent_major and int(nm.group(2)) > (current_minor or -1):
            end_i = j
            break
        # Also stop at another short cancer-specific heading.
        if looks_like_heading(line):
            low = line.lower()
            other = False
            for cid, term in heading_terms:
                if cid != target_cancer and term.lower() in low:
                    other = True
                    break
            if other:
                end_i = j
                break
    ctx = "\n".join(lines[start_i:end_i])
    return ctx[:6000]


def compact_excerpt(text: str, max_chars=2400) -> str:
    text = norm_text(text).replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:max_chars]


def clear_unsafe_dose(entry: dict, reason: str) -> None:
    entry["dose_mentions"] = []
    entry["frequency_mentions"] = []
    entry.pop("dosage_excerpt", None)
    entry.pop("dose_source_url", None)
    entry["dose_confidence"] = "withheld"
    entry["dose_withheld_reason"] = reason
    entry["dose_indication_specific"] = False


def enrich_entry(entry: dict, cancer_id: str, pdf_text: str, source_url: str, aliases: dict) -> bool:
    section = dosage_section(pdf_text) if pdf_text else ""
    licence_cancers = indication_cancer_ids(str(entry.get("indication", "")), aliases)

    # Multi-indication licences: only an explicit target-cancer subsection is safe enough.
    ctx = specific_dosage_subsection(section, cancer_id, aliases) if section else ""
    basis = "cancer-specific dosage subsection" if ctx else ""

    # Single-cancer licence: a general dosage section is still indication-specific by construction.
    if not ctx and section and licence_cancers == {cancer_id}:
        ctx = section[:8000]
        basis = "single-indication licence dosage section"

    if ctx:
        doses, freqs = mentions(ctx)
        # We need at least a dose. Frequency may be expressed as day numbers/cycles and not match regex.
        if doses:
            entry["dose_mentions"] = doses
            entry["frequency_mentions"] = freqs
            entry["dosage_excerpt"] = compact_excerpt(ctx)
            entry["dose_source"] = "TFDA 官方仿單 PDF"
            entry["dose_source_url"] = source_url
            entry["dose_indication_specific"] = True
            entry["dose_confidence"] = "high"
            entry["dose_match_basis"] = basis
            entry.pop("dose_withheld_reason", None)
            return True

    # Dataset-37 free-text dose can still be safe for a single-cancer licence.
    raw_dosage = clean(str(entry.get("dosage", "")))
    base_doses, base_freqs = mentions(raw_dosage)
    if licence_cancers == {cancer_id} and base_doses and not PLACEHOLDER_DOSE_RE.match(raw_dosage):
        entry["dose_mentions"] = base_doses
        entry["frequency_mentions"] = base_freqs
        entry["dose_source"] = "TFDA 未註銷藥品許可證資料集－用法用量"
        entry["dose_indication_specific"] = True
        entry["dose_confidence"] = "high"
        entry["dose_match_basis"] = "single-indication licence structured dosage"
        entry.pop("dose_withheld_reason", None)
        return True

    reason = "multi-indication licence without an explicit target-cancer dosage subsection"
    if not section:
        reason = "official insert PDF text unavailable or dosage section not machine-readable"
    elif licence_cancers == {cancer_id}:
        reason = "single-indication dosage section found but no reliable dose token was extracted"
    clear_unsafe_dose(entry, reason)
    return False


def main():
    data = load_tfda()
    aliases = load_json(CANCER_ALIASES, {})
    cancer_by_id = parse_curated_cancers()
    entries = data.get("byIndicationId", {})

    # Re-evaluate every visible mapping from scratch so a previous broad extraction cannot survive.
    permit_urls = {}
    for item_id, entry in entries.items():
        if not isinstance(entry, dict) or entry.get("status") not in {"matched", "generic-label"}:
            continue
        permit = str(entry.get("permit", ""))
        urls = split_urls(str(entry.get("label_url", "")))
        if permit and urls:
            permit_urls.setdefault(permit, urls)

    pdf_cache = {}
    attempted = len(permit_urls)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(fetch_pdf_text, urls): permit for permit, urls in permit_urls.items()}
        for fut in as_completed(futs):
            permit = futs[fut]
            try:
                pdf_cache[permit] = fut.result()
            except Exception as exc:
                pdf_cache[permit] = ("", type(exc).__name__)

    high_confidence = 0
    withheld = 0
    parsed_pdfs = sum(1 for text, _ in pdf_cache.values() if text)
    for item_id, entry in entries.items():
        if not isinstance(entry, dict) or entry.get("status") not in {"matched", "generic-label"}:
            continue
        permit = str(entry.get("permit", ""))
        text, source = pdf_cache.get(permit, ("", ""))
        if enrich_entry(entry, cancer_by_id.get(item_id, ""), text, source, aliases):
            high_confidence += 1
        else:
            withheld += 1

    meta = data.setdefault("meta", {})
    meta["package_insert_pdf_attempted_count"] = attempted
    meta["package_insert_pdf_parsed_count"] = parsed_pdfs
    meta["indication_dose_enriched_count"] = high_confidence
    meta["high_confidence_dose_count"] = high_confidence
    meta["dose_withheld_count"] = withheld
    meta["dose_extraction_note"] = (
        "Dose/frequency is shown only for an explicit cancer-specific dosage subsection or a single-indication licence. "
        "Multi-indication labels without a target-cancer dosage subsection are linked but dose is withheld."
    )
    save_tfda(data)
    print(json.dumps({
        "pdf_attempted": attempted,
        "pdf_parsed": parsed_pdfs,
        "high_confidence_dose": high_confidence,
        "dose_withheld": withheld,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

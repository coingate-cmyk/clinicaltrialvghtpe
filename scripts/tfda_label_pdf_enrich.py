#!/usr/bin/env python3
"""Enrich TFDA oncology mappings with dose/frequency extracted from official package-insert PDFs.

This is deliberately conservative: parsed dose chips are accepted only when they are found
near the relevant cancer/indication wording in the official insert, or when a clearly named
Dosage/Administration section yields an unambiguous general regimen. Scanned/unreadable PDFs
are left as '詳見仿單' rather than guessed.
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


def norm_text(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s or "")).replace("\u00a0", " ")


def clean(s: str) -> str:
    return re.sub(r"[ \t]+", " ", norm_text(s)).strip()


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
    # Dataset 39 occasionally concatenates multiple official insert PDFs with ';'.
    parts = re.split(r";(?=https?://)", value)
    return [p.strip() for p in parts if p.strip().startswith("http")]


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
    out = []
    seen = set()
    for v in values:
        v = clean(v)
        k = v.lower().replace(" ", "")
        if v and k not in seen:
            seen.add(k)
            out.append(v)
        if len(out) >= limit:
            break
    return out


def mentions(text: str) -> tuple[list[str], list[str]]:
    doses = uniq([m.group(0) for m in DOSE_RE.finditer(text)], 12)
    freqs = []
    for pat in FREQ_PATTERNS:
        freqs.extend(m.group(0) for m in pat.finditer(text))
    return doses, uniq(freqs, 12)


def cancer_terms(cancer_id: str, aliases: dict) -> list[str]:
    cfg = aliases.get(cancer_id, {}) if isinstance(aliases, dict) else {}
    vals = []
    if isinstance(cfg, dict):
        vals.extend(cfg.get("aliases", []) or [])
        vals.append(cfg.get("name", ""))
    terms = []
    for v in vals:
        v = clean(v)
        if len(v) >= 2 and v.lower() not in {x.lower() for x in terms}:
            terms.append(v)
    return sorted(terms, key=len, reverse=True)


def relevant_context(text: str, terms: list[str]) -> tuple[str, bool]:
    low = text.lower()
    windows = []
    for term in terms[:20]:
        t = term.lower()
        start = 0
        hits = 0
        while hits < 3:
            pos = low.find(t, start)
            if pos < 0:
                break
            a = max(0, pos - 1000)
            b = min(len(text), pos + len(term) + 1800)
            snippet = text[a:b]
            d, f = mentions(snippet)
            if d or f:
                windows.append(snippet)
            start = pos + len(t)
            hits += 1
        if windows:
            break
    if windows:
        return "\n…\n".join(windows[:3]), True
    return "", False


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
    end = min(len(text), start + 12000)
    tail_low = low[start + 40:end]
    stops = []
    for heading in STOP_HEADINGS:
        p = tail_low.find(heading.lower())
        if p >= 400:
            stops.append(start + 40 + p)
    if stops:
        end = min(stops)
    return text[start:end]


def compact_excerpt(text: str, max_chars=2200) -> str:
    text = re.sub(r"\n{3,}", "\n\n", clean(text.replace("\r", "\n")))
    return text[:max_chars].strip()


def enrich_entry(entry: dict, cancer_id: str, pdf_text: str, source_url: str, aliases: dict) -> bool:
    if not pdf_text:
        return False
    terms = cancer_terms(cancer_id, aliases)
    ctx, specific = relevant_context(pdf_text, terms)
    if not ctx:
        ctx = dosage_section(pdf_text)
        specific = False
    if not ctx:
        return False
    doses, freqs = mentions(ctx)
    if not (doses or freqs):
        return False
    # For a generic dosage section, require both a dose and a frequency before exposing chips.
    if not specific and not (doses and freqs):
        return False
    entry["dose_mentions"] = doses
    entry["frequency_mentions"] = freqs
    entry["dosage_excerpt"] = compact_excerpt(ctx)
    if re.fullmatch(r"請?(?:詳|參閱).{0,8}仿單.{0,8}", clean(entry.get("dosage", ""))):
        entry["dosage"] = entry["dosage_excerpt"]
    entry["dose_source"] = "TFDA 官方仿單 PDF"
    entry["dose_source_url"] = source_url
    entry["dose_indication_specific"] = specific
    return True


def main():
    data = load_tfda()
    aliases = load_json(CANCER_ALIASES, {})
    cancer_by_id = parse_curated_cancers()
    entries = data.get("byIndicationId", {})

    permit_urls = {}
    for item_id, entry in entries.items():
        if not isinstance(entry, dict) or entry.get("status") not in {"matched", "generic-label"}:
            continue
        if entry.get("dose_mentions") and entry.get("frequency_mentions"):
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

    enriched = 0
    parsed_pdfs = sum(1 for text, _ in pdf_cache.values() if text)
    for item_id, entry in entries.items():
        if not isinstance(entry, dict) or entry.get("status") not in {"matched", "generic-label"}:
            continue
        permit = str(entry.get("permit", ""))
        text, source = pdf_cache.get(permit, ("", ""))
        if enrich_entry(entry, cancer_by_id.get(item_id, ""), text, source, aliases):
            enriched += 1

    meta = data.setdefault("meta", {})
    meta["package_insert_pdf_attempted_count"] = attempted
    meta["package_insert_pdf_parsed_count"] = parsed_pdfs
    meta["indication_dose_enriched_count"] = enriched
    meta["dose_extraction_note"] = "Dose/frequency chips are extracted from official TFDA package-insert PDFs; indication-context matches are preferred, ambiguous/unreadable PDFs remain unparsed."
    save_tfda(data)
    print(json.dumps({"pdf_attempted": attempted, "pdf_parsed": parsed_pdfs, "indication_dose_enriched": enriched}, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build a compact TFDA label/dose index for curated NHI oncology indications.

Sources (official TFDA open data, refreshed every 7 days):
- Dataset 37: active (not cancelled) drug licences, including indication and dosage.
- Dataset 39: package-insert / outer-box links.

Safety rule: automatic matching may enrich the UI, but ambiguous matches are written to
review queue and are not surfaced as a definitive indication-specific dose.
"""
from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "tools/nhi/assets"
DATA_DIR = ROOT / "tools/nhi/data"
CONFIG_DIR = ROOT / "tools/nhi/config"
OUT_JS = ASSET_DIR / "tfda-labels.js"
REVIEW_FILE = DATA_DIR / "tfda-label-review.json"
ALIASES_FILE = CONFIG_DIR / "tfda_drug_aliases.json"
CANCER_ALIASES_FILE = CONFIG_DIR / "cancer_aliases.json"

ACTIVE_URL = "https://data.fda.gov.tw/data/opendata/export/37/json"
INSERT_URL = "https://data.fda.gov.tw/data/opendata/export/39/json"
DATASET_ACTIVE_PAGE = "https://data.gov.tw/dataset/9123"
DATASET_INSERT_PAGE = "https://data.gov.tw/dataset/9117"
MCP_BASE = "https://mcp.fda.gov.tw/im_detail_1/"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://data.fda.gov.tw/",
})

STOP_WORDS = {
    "acid", "sodium", "potassium", "hydrochloride", "hydrate", "dihydrate", "monohydrate",
    "mesylate", "maleate", "succinate", "phosphate", "citrate", "acetate", "besylate", "tartrate",
    "injection", "tablet", "tablets", "capsule", "capsules", "solution", "concentrate", "film", "coated",
    "therapy", "regimen", "and", "with", "plus", "the", "for", "oral", "iv", "sc",
}
GENERIC_CANCER_WORDS = ["癌", "腫瘤", "carcinoma", "cancer", "tumor", "tumour", "malignan", "neoplasm", "leukemia", "lymphoma", "myeloma"]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def norm(value: str) -> str:
    s = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", s)


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def decode_bytes(blob: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
        try:
            return blob.decode(enc)
        except UnicodeDecodeError:
            continue
    return blob.decode("utf-8", errors="replace")


def unpack_response(blob: bytes) -> tuple[str, str]:
    if zipfile.is_zipfile(io.BytesIO(blob)):
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            names = [n for n in zf.namelist() if not n.endswith("/")]
            preferred = sorted(names, key=lambda n: (0 if n.lower().endswith(".json") else 1 if n.lower().endswith(".csv") else 2, len(n)))
            if not preferred:
                raise RuntimeError("TFDA ZIP is empty")
            name = preferred[0]
            return decode_bytes(zf.read(name)), name
    return decode_bytes(blob), "response"


def fetch_rows(url: str) -> list[dict]:
    r = SESSION.get(url, timeout=180)
    r.raise_for_status()
    if len(r.content) < 100:
        raise RuntimeError(f"TFDA response unexpectedly small: {len(r.content)} bytes")
    text, name = unpack_response(r.content)
    stripped = text.lstrip("\ufeff \r\n\t")
    if stripped.startswith("[") or stripped.startswith("{"):
        payload = json.loads(stripped)
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict):
            for key in ("data", "result", "results", "records", "items"):
                if isinstance(payload.get(key), list):
                    return [x for x in payload[key] if isinstance(x, dict)]
            for value in payload.values():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    return value
        raise RuntimeError(f"Cannot locate row array in TFDA JSON ({name})")
    reader = csv.DictReader(io.StringIO(text))
    rows = [dict(r) for r in reader]
    if not rows:
        raise RuntimeError(f"No rows parsed from TFDA payload ({name})")
    return rows


def pick(row: dict, *names: str) -> str:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return clean(row[name])
    normalized = {norm(k): v for k, v in row.items()}
    for name in names:
        value = normalized.get(norm(name))
        if value not in (None, ""):
            return clean(value)
    return ""


def parse_curated_records() -> list[dict]:
    records = []
    for path in sorted(ASSET_DIR.glob("data-*.js")):
        if path.name == "data-core.js":
            continue
        src = path.read_text(encoding="utf-8")
        m = re.search(r"push\(\.\.\.(\[[\s\S]*\])\s*\);", src)
        if not m:
            continue
        try:
            payload = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        records.extend(x for x in payload if isinstance(x, dict) and x.get("id") and x.get("drug"))
    if len(records) < 20:
        raise RuntimeError(f"Curated NHI records unexpectedly small: {len(records)}")
    return records


def ascii_words(value: str) -> list[str]:
    value = re.sub(r"\([^)]*\)", " ", str(value or ""))
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", value)
    return [w.lower() for w in words if len(w) >= 4 and w.lower() not in STOP_WORDS]


def required_terms(drug: str, aliases: dict) -> list[str]:
    cfg = aliases.get(drug) or aliases.get(drug.lower())
    if isinstance(cfg, str):
        cfg = [cfg]
    if isinstance(cfg, list) and cfg:
        return [norm(x) for x in cfg if norm(x)]
    words = ascii_words(drug)
    return [norm(w) for w in words if norm(w)]


def indication_matches(indication: str, cancer_id: str, cancer_aliases: dict) -> bool:
    text = unicodedata.normalize("NFKC", indication or "").lower()
    cfg = cancer_aliases.get(cancer_id, {}) if isinstance(cancer_aliases, dict) else {}
    aliases = cfg.get("aliases", []) if isinstance(cfg, dict) else []
    for alias in aliases:
        a = unicodedata.normalize("NFKC", str(alias)).lower().strip()
        if len(a) >= 2 and a in text:
            return True
    name = str(cfg.get("name", "")) if isinstance(cfg, dict) else ""
    return bool(name and name.lower() in text)


def dosage_mentions(text: str) -> tuple[list[str], list[str]]:
    t = unicodedata.normalize("NFKC", text or "")
    doses = []
    freqs = []
    dose_re = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mcg|μg|ug|mg|g)(?:\s*/\s*(?:kg|m2|m²))?\b", re.I)
    freq_patterns = [
        r"每\s*[一二三四五六七八九十\d]+\s*(?:週|周|天|日|小時)\s*(?:一次|1次)?",
        r"(?:每|一)\s*(?:日|天)\s*[一二三四五六七八九十\d]+\s*次",
        r"一天\s*[一二三四五六七八九十\d]+\s*次",
        r"\bq\s*\d+\s*(?:w|wk|week|d|day|h)\b",
        r"每\s*[一二三四五六七八九十\d]+\s*週",
    ]
    for m in dose_re.findall(t):
        m = clean(m)
        if m not in doses:
            doses.append(m)
    for pat in freq_patterns:
        for m in re.findall(pat, t, re.I):
            m = clean(m)
            if m and m not in freqs:
                freqs.append(m)
    return doses[:8], freqs[:8]


def useful_dose(text: str) -> bool:
    t = clean(text)
    return bool(t and not re.fullmatch(r"詳如仿單[。.]?", t))


def permit_url(permit: str) -> str:
    return MCP_BASE + quote(permit, safe="")


def main():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    fetched_at = now_iso()
    aliases = load_json(ALIASES_FILE, {})
    cancer_aliases = load_json(CANCER_ALIASES_FILE, {})
    curated = parse_curated_records()

    active_rows = fetch_rows(ACTIVE_URL)
    insert_rows = fetch_rows(INSERT_URL)

    insert_by_permit = {}
    for row in insert_rows:
        permit = pick(row, "許可證字號", "許可證號")
        if not permit:
            continue
        insert_by_permit[norm(permit)] = {
            "label_url": pick(row, "仿單圖檔連結", "仿單連結", "仿單檔案連結"),
            "product_zh": pick(row, "中文品名"),
            "product_en": pick(row, "英文品名"),
        }

    licenses = []
    for row in active_rows:
        permit = pick(row, "許可證字號", "許可證號")
        if not permit:
            continue
        ingredient = pick(row, "主成分略述", "主成分")
        product_en = pick(row, "英文品名")
        indication = pick(row, "適應症")
        dosage = pick(row, "用法用量")
        ins = insert_by_permit.get(norm(permit), {})
        label_url = ins.get("label_url") or permit_url(permit)
        licenses.append({
            "permit": permit,
            "product_zh": pick(row, "中文品名") or ins.get("product_zh", ""),
            "product_en": product_en or ins.get("product_en", ""),
            "ingredient": ingredient,
            "indication": indication,
            "dosage": dosage,
            "applicant": pick(row, "申請商名稱"),
            "modified": pick(row, "異動日期"),
            "form": pick(row, "劑型"),
            "label_url": label_url,
            "match_blob": norm(ingredient + " " + product_en),
        })

    by_id = {}
    review_items = []
    matched_count = 0
    for item in curated:
        drug = clean(item.get("drug"))
        terms = required_terms(drug, aliases)
        if not terms:
            continue
        candidates = []
        for lic in licenses:
            if not all(term in lic["match_blob"] for term in terms):
                continue
            cancer_match = indication_matches(lic["indication"], str(item.get("cancer", "")), cancer_aliases)
            cancerish = any(w in (lic["indication"] or "").lower() for w in GENERIC_CANCER_WORDS)
            score = 10 + (8 if cancer_match else 0) + (2 if useful_dose(lic["dosage"]) else 0) + (1 if lic["label_url"] else 0)
            if cancerish:
                score += 1
            candidates.append((score, cancer_match, lic))

        if not candidates:
            by_id[item["id"]] = {"status": "not-found", "drug": drug}
            continue

        candidates.sort(key=lambda x: (x[0], x[2].get("modified", "")), reverse=True)
        cancer_specific = [x for x in candidates if x[1]]
        pool = cancer_specific or candidates
        top_score = pool[0][0]
        top = [x[2] for x in pool if x[0] >= top_score - 1][:8]

        dose_variants = []
        for lic in top:
            d = clean(lic["dosage"])
            if useful_dose(d) and norm(d) not in {norm(x) for x in dose_variants}:
                dose_variants.append(d)
        ambiguous_dose = len(dose_variants) > 1 and not cancer_specific

        best = top[0]
        doses, freqs = dosage_mentions(best["dosage"])
        status = "matched" if cancer_specific else "generic-label"
        if ambiguous_dose:
            status = "review"

        entry = {
            "status": status,
            "drug": drug,
            "permit": best["permit"],
            "product_zh": best["product_zh"],
            "product_en": best["product_en"],
            "applicant": best["applicant"],
            "form": best["form"],
            "indication": best["indication"],
            "dosage": best["dosage"] or "詳如仿單",
            "dose_mentions": doses,
            "frequency_mentions": freqs,
            "label_url": best["label_url"],
            "license_modified": best["modified"],
            "match_basis": "成分 + 癌種適應症" if cancer_specific else "成分（跨適應症仿單）",
            "candidate_count": len(candidates),
        }
        by_id[item["id"]] = entry

        if status in {"matched", "generic-label"}:
            matched_count += 1
        if status == "review":
            review_items.append({
                "id": item["id"], "cancer": item.get("cancer"), "drug": drug,
                "reason": "Multiple active licences have differing dosage text without a reliable cancer-specific winner.",
                "candidates": [
                    {"permit": lic["permit"], "product": lic["product_zh"] or lic["product_en"], "dosage": lic["dosage"], "indication": lic["indication"], "label_url": lic["label_url"]}
                    for lic in top[:5]
                ],
            })

    output = {
        "meta": {
            "schema_version": "tfda-oncology-label-v1",
            "fetched_at": fetched_at,
            "active_dataset": DATASET_ACTIVE_PAGE,
            "insert_dataset": DATASET_INSERT_PAGE,
            "active_row_count": len(active_rows),
            "insert_row_count": len(insert_rows),
            "curated_indication_count": len(curated),
            "matched_indication_count": matched_count,
            "review_count": len(review_items),
            "note": "Dose/interval is derived only from official TFDA licence dosage text. Ambiguous mappings are withheld for review.",
        },
        "byIndicationId": by_id,
    }
    OUT_JS.write_text("window.TFDA_LABELS = " + json.dumps(output, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    REVIEW_FILE.write_text(json.dumps({"status": "ok", "fetched_at": fetched_at, "item_count": len(review_items), "items": review_items}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "active_rows": len(active_rows), "insert_rows": len(insert_rows), "curated": len(curated),
        "matched": matched_count, "review": len(review_items), "output": str(OUT_JS.relative_to(ROOT)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

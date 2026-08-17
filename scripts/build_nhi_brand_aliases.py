#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

RESOURCE_ID = "A21030000I-E41001-001"
DATASTORE_URL = f"https://info.nhi.gov.tw/api/iode0010/v1/rest/datastore/{RESOURCE_ID}"
LEGACY_URL = f"https://info.nhi.gov.tw/api/iode0000s01/Dataset?rId={RESOURCE_ID}"
SOURCE_PAGE = "https://info.nhi.gov.tw/IODE0000/IODE0000S09?id=111"
OUT = Path("tools/nhi/assets/nhi-brand-aliases.js")
RAW = Path("tools/nhi/data/brands/current.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Accept": "application/json,text/csv,application/zip,application/octet-stream,*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
    "Referer": "https://info.nhi.gov.tw/",
}
EXPECTED = {"藥品代號", "藥品英文名稱", "藥品中文名稱", "成分"}


def decode_bytes(data: bytes) -> str:
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))]
            if not names:
                raise RuntimeError("NHI dataset ZIP contains no CSV/TXT")
            data = zf.read(names[0])
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip())


def normalize_row(row: dict) -> dict[str, str]:
    return {clean(k): clean(v) for k, v in row.items()}


def active_row(row: dict[str, str]) -> bool:
    end = clean(row.get("有效迄日"))
    if not end:
        return True
    digits = re.sub(r"\D", "", end)
    if not digits:
        return True
    try:
        if len(digits) == 7:
            y = int(digits[:3]) + 1911
            m, d = int(digits[3:5]), int(digits[5:7])
        elif len(digits) >= 8:
            y, m, d = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
        else:
            return True
        return datetime(y, m, d, tzinfo=timezone.utc).date() >= datetime.now(timezone.utc).date()
    except Exception:
        return True


def oncology_row(row: dict[str, str]) -> bool:
    chapter = clean(row.get("給付規定章節"))
    atc = clean(row.get("ATC代碼")).upper()
    category = clean(row.get("分類分組名稱")) + " " + clean(row.get("藥品分類"))
    return bool(re.search(r"(^|\D)9(?:\.|$)", chapter)) or atc.startswith(("L01", "L02")) or "抗癌" in category or "抗腫瘤" in category


def parse_csv(text: str) -> list[dict[str, str]]:
    sample = text[:10000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    rows = [normalize_row(r) for r in csv.DictReader(io.StringIO(text), dialect=dialect)]
    if not rows:
        raise RuntimeError("NHI drug dataset parsed zero rows")
    missing = EXPECTED - set(rows[0].keys())
    if missing:
        raise RuntimeError(f"NHI drug dataset missing expected columns: {sorted(missing)}; got {list(rows[0].keys())[:12]}")
    return rows


def find_record_list(obj):
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        keys = {clean(k) for k in obj[0].keys()}
        if len(EXPECTED & keys) >= 2:
            return obj
    if isinstance(obj, dict):
        for key in ("records", "data", "result", "items"):
            if key in obj:
                hit = find_record_list(obj[key])
                if hit is not None:
                    return hit
        for value in obj.values():
            hit = find_record_list(value)
            if hit is not None:
                return hit
    return None


def fetch_datastore_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    limit = 5000
    offset = 0
    while True:
        r = requests.get(DATASTORE_URL, params={"limit": limit, "offset": offset}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        payload = r.json()
        batch = find_record_list(payload)
        if batch is None:
            raise RuntimeError(f"Cannot locate record list in NHI datastore response; top keys={list(payload)[:10] if isinstance(payload, dict) else type(payload)}")
        norm_batch = [normalize_row(x) for x in batch]
        if norm_batch:
            missing = EXPECTED - set(norm_batch[0].keys())
            if missing:
                raise RuntimeError(f"NHI datastore missing expected columns: {sorted(missing)}; got {list(norm_batch[0].keys())[:12]}")
        rows.extend(norm_batch)
        print(f"Fetched NHI datastore rows: {len(rows)}", flush=True)
        if len(batch) < limit:
            break
        offset += len(batch)
        if offset > 100000:
            raise RuntimeError("NHI datastore pagination exceeded safety limit")
    if not rows:
        raise RuntimeError("NHI datastore returned zero rows")
    return rows


def fetch_rows() -> tuple[list[dict[str, str]], str]:
    try:
        return fetch_datastore_rows(), DATASTORE_URL
    except Exception as exc:
        print(f"Modern NHI datastore fetch failed: {exc}; trying legacy CSV endpoint", file=sys.stderr, flush=True)
    r = requests.get(LEGACY_URL, headers=HEADERS, timeout=35)
    r.raise_for_status()
    return parse_csv(decode_bytes(r.content)), LEGACY_URL


def build(rows: list[dict[str, str]], transport: str) -> dict:
    products = []
    seen = set()
    for r in rows:
        if not active_row(r) or not oncology_row(r):
            continue
        item = {
            "code": clean(r.get("藥品代號")),
            "brand_en": clean(r.get("藥品英文名稱")),
            "brand_zh": clean(r.get("藥品中文名稱")),
            "ingredient": clean(r.get("成分")),
            "company": clean(r.get("藥商")),
            "manufacturer": clean(r.get("製造廠名稱")),
            "atc": clean(r.get("ATC代碼")),
            "chapter": clean(r.get("給付規定章節")),
            "price": clean(r.get("支付價")),
            "effective_from": clean(r.get("有效起日")),
            "effective_to": clean(r.get("有效迄日")),
        }
        if not (item["brand_en"] or item["brand_zh"]) or not item["ingredient"]:
            continue
        key = (item["code"], item["brand_en"], item["brand_zh"], item["ingredient"])
        if key in seen:
            continue
        seen.add(key)
        products.append(item)

    products.sort(key=lambda x: (x["ingredient"].lower(), x["brand_en"].lower(), x["brand_zh"]))
    ingredients = sorted({p["ingredient"] for p in products if p["ingredient"]}, key=str.lower)
    return {
        "meta": {
            "source": SOURCE_PAGE,
            "transport": transport,
            "resource_id": RESOURCE_ID,
            "dataset": "健保用藥品項查詢項目檔",
            "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "scope": "active oncology-related NHI listed products; Chapter 9 and oncology ATC/category filters",
            "product_count": len(products),
            "ingredient_count": len(ingredients),
            "classification_note": "Official NHI dataset does not reliably label originator vs generic; products are indexed as NHI-listed brand names. Known originator brand aliases remain separately curated in the UI.",
        },
        "products": products,
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    RAW.parent.mkdir(parents=True, exist_ok=True)
    rows, transport = fetch_rows()
    payload = build(rows, transport)
    if payload["meta"]["product_count"] < 50:
        raise RuntimeError(f"Suspiciously small oncology brand index: {payload['meta']['product_count']}")
    RAW.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT.write_text("window.NHI_BRAND_INDEX = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"NHI brand index OK: {payload['meta']['product_count']} products / {payload['meta']['ingredient_count']} ingredients; transport={transport}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

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

SOURCE_URL = "https://info.nhi.gov.tw/api/iode0000s01/Dataset?rId=A21030000I-E41001-001"
OUT = Path("tools/nhi/assets/nhi-brand-aliases.js")
RAW = Path("tools/nhi/data/brands/current.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Accept": "text/csv,application/zip,application/octet-stream,*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
    "Referer": "https://info.nhi.gov.tw/",
}


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
    return re.sub(r"\s+", " ", (s or "").strip())


def active_row(row: dict[str, str]) -> bool:
    end = clean(row.get("有效迄日"))
    if not end:
        return True
    digits = re.sub(r"\D", "", end)
    if not digits:
        return True
    # ROC yyyMMdd or Gregorian yyyyMMdd. Keep future/current rows; old rows are not useful aliases.
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
    # Chapter 9 is the primary source; ATC L01/L02 catches oncology items whose chapter field is blank/oddly formatted.
    return bool(re.search(r"(^|\D)9(?:\.|$)", chapter)) or atc.startswith(("L01", "L02")) or "抗癌" in category or "抗腫瘤" in category


def parse_csv(text: str) -> list[dict[str, str]]:
    # The official file is CSV; sniff defensively because older exports have varied quoting/delimiters.
    sample = text[:10000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    if not rows:
        raise RuntimeError("NHI drug dataset parsed zero rows")
    expected = {"藥品代號", "藥品英文名稱", "藥品中文名稱", "成分"}
    missing = expected - set(rows[0].keys())
    if missing:
        raise RuntimeError(f"NHI drug dataset missing expected columns: {sorted(missing)}; got {list(rows[0].keys())[:12]}")
    return rows


def build(rows: list[dict[str, str]]) -> dict:
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
            "source": SOURCE_URL,
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
    r = requests.get(SOURCE_URL, headers=HEADERS, timeout=90)
    r.raise_for_status()
    text = decode_bytes(r.content)
    rows = parse_csv(text)
    payload = build(rows)
    if payload["meta"]["product_count"] < 50:
        raise RuntimeError(f"Suspiciously small oncology brand index: {payload['meta']['product_count']}")
    RAW.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT.write_text("window.NHI_BRAND_INDEX = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"NHI brand index OK: {payload['meta']['product_count']} products / {payload['meta']['ingredient_count']} ingredients")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

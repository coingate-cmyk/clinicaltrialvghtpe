#!/usr/bin/env python3
"""Extract the embedded INITIAL_TRIALS array without changing its bytes.

Usage:
    python scripts/extract_initial_trials.py index.html --in-place
    python scripts/extract_initial_trials.py index.html --output index.phase2.html
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PREFIX = "const INITIAL_TRIALS = "
REACT_DOM_TAG = '    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>\n'
DATA_TAG = '    <script src="./data/initial-trials.js"></script>\n'


def find_array_end(source: str, start: int) -> int:
    if start >= len(source) or source[start] != "[":
        raise ValueError("INITIAL_TRIALS does not start with an array")

    depth = 0
    quote: str | None = None
    escaped = False

    for index in range(start, len(source)):
        char = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in {'"', "'"}:
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index

    raise ValueError("Could not find the end of INITIAL_TRIALS")


def extract(source: str) -> tuple[str, str, int, str]:
    declaration_start = source.find(PREFIX)
    if declaration_start < 0:
        raise ValueError("INITIAL_TRIALS declaration was not found")
    if source.find(PREFIX, declaration_start + 1) >= 0:
        raise ValueError("More than one INITIAL_TRIALS declaration was found")

    array_start = declaration_start + len(PREFIX)
    array_end = find_array_end(source, array_start)
    if source[array_end + 1 : array_end + 2] != ";":
        raise ValueError("INITIAL_TRIALS declaration does not end with a semicolon")

    array_text = source[array_start : array_end + 1]
    trials = json.loads(array_text)
    if not isinstance(trials, list):
        raise ValueError("INITIAL_TRIALS is not a list")

    declaration_end = array_end + 2
    data_javascript = f"{PREFIX}{array_text};\n"
    digest = hashlib.sha256(array_text.encode("utf-8")).hexdigest()

    if source.count(REACT_DOM_TAG) != 1:
        raise ValueError("Expected ReactDOM script tag was not found exactly once")

    updated = source.replace(REACT_DOM_TAG, REACT_DOM_TAG + DATA_TAG, 1)
    inserted_length = len(DATA_TAG)
    declaration_start += inserted_length
    declaration_end += inserted_length
    updated = updated[:declaration_start] + updated[declaration_end:]

    if PREFIX in updated:
        raise ValueError("Embedded INITIAL_TRIALS remains in the generated index")
    if updated.count(DATA_TAG) != 1:
        raise ValueError("External INITIAL_TRIALS script tag was not inserted exactly once")

    return updated, data_javascript, len(trials), digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--in-place", action="store_true")
    destination.add_argument("--output", type=Path)
    args = parser.parse_args()

    source = args.index.read_text(encoding="utf-8")
    updated, data_javascript, count, digest = extract(source)

    data_path = args.index.parent / "data" / "initial-trials.js"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(data_javascript, encoding="utf-8")

    output_path = args.index if args.in_place else args.output
    assert output_path is not None
    output_path.write_text(updated, encoding="utf-8")

    print(f"trial_count={count}")
    print(f"array_sha256={digest}")
    print(f"index_output={output_path}")
    print(f"data_output={data_path}")


if __name__ == "__main__":
    main()

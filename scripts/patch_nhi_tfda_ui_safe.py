#!/usr/bin/env python3
"""Run the TFDA/NHI UI patch safely when the TFDA script tag has a cache-busting query string.

The legacy patch is intentionally kept untouched because it also patches app.js/style.css.
This wrapper makes its index.html check idempotent for both:
  assets/tfda-labels.js
  assets/tfda-labels.js?v=...
It restores the original cache-busting tag after the patch completes.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "tools/nhi/index.html"
PATCH = ROOT / "scripts/patch_nhi_tfda_ui.py"

SCRIPT_RE = re.compile(
    r'<script\s+src=["\']assets/tfda-labels\.js(?P<query>\?[^"\']*)?["\']\s*></script>',
    re.I,
)
CANONICAL = '<script src="assets/tfda-labels.js"></script>'


def main():
    index = INDEX.read_text(encoding="utf-8")
    match = SCRIPT_RE.search(index)
    original_tag = match.group(0) if match else None

    # The legacy patch recognizes only the unversioned canonical tag.
    # Normalize only for the duration of that patch, then restore the exact
    # original versioned tag so browser cache-busting remains intact.
    if match and match.group("query"):
        index = index[: match.start()] + CANONICAL + index[match.end() :]
        INDEX.write_text(index, encoding="utf-8")

    try:
        subprocess.run([sys.executable, str(PATCH)], cwd=ROOT, check=True)
    finally:
        if original_tag and original_tag != CANONICAL:
            current = INDEX.read_text(encoding="utf-8")
            if CANONICAL in current:
                current = current.replace(CANONICAL, original_tag, 1)
                INDEX.write_text(current, encoding="utf-8")

    # Guard against accidental duplicate TFDA tags.
    final = INDEX.read_text(encoding="utf-8")
    tags = SCRIPT_RE.findall(final)
    if len(tags) != 1:
        raise SystemExit(f"Expected exactly one TFDA label script tag, found {len(tags)}")

    print("Safe TFDA UI patch completed; cache-busting tag preserved.")


if __name__ == "__main__":
    main()

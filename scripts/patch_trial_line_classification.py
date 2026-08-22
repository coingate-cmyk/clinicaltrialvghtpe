from pathlib import Path

# The classification repairs are already present in index.html. Reuse this existing,
# authorized workflow entrypoint to apply the 2026-08-22 Study Status + PDF import patch.
patch = Path('scripts/patch_study_status_20260822.py')
if not patch.exists():
    raise SystemExit(f'Missing patch script: {patch}')
exec(compile(patch.read_text(encoding='utf-8'), str(patch), 'exec'))

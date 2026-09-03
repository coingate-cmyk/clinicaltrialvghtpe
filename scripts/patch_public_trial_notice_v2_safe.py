from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'scripts' / 'patch_public_trial_notice_v2.py'
INDEX = ROOT / 'index.html'

spec = importlib.util.spec_from_file_location('public_notice_base', BASE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.main()

text = INDEX.read_text(encoding='utf-8')
# re.sub replacement strings interpret backslash escapes. Normalize the affected
# JavaScript regex back to a literal \\n escape before syntax validation.
bad = "split(/[、,，;/；\n]+/)"
good = "split(/[、,，;/；\\n]+/)"
if bad in text:
    text = text.replace(bad, good)
INDEX.write_text(text, encoding='utf-8')
print('normalized public notice JS escapes')

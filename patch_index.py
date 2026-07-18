from pathlib import Path
from datetime import datetime
import sys

ROOT = Path(__file__).resolve().parent
# Allow running from repo root or from this patch folder.
index_candidates = [Path.cwd() / "index.html", ROOT / "index.html"]
index_path = next((p for p in index_candidates if p.exists()), None)
if index_path is None:
    print("找不到 index.html。請把 patch_index.py 放在 clinicaltrialvghtpe 專案根目錄後再執行。")
    sys.exit(1)

snippet_path = ROOT / "tools_launcher_snippet.html"
if not snippet_path.exists():
    print("找不到 tools_launcher_snippet.html。請確認它和 patch_index.py 在同一個資料夾。")
    sys.exit(1)

html = index_path.read_text(encoding="utf-8")
snippet = snippet_path.read_text(encoding="utf-8").strip()

if "id=\"clinical-tools-launcher\"" in html or "id='clinical-tools-launcher'" in html:
    print("index.html 裡已經有 clinical tools launcher，未重複插入。")
    sys.exit(0)

if "</body>" not in html:
    print("index.html 找不到 </body>，為避免破壞檔案，未修改。")
    sys.exit(1)

backup = index_path.with_name(f"index.backup.before_tools_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
backup.write_text(html, encoding="utf-8")

patched = html.replace("</body>", "\n" + snippet + "\n</body>", 1)
index_path.write_text(patched, encoding="utf-8")

print(f"完成：已插入臨床工具入口。")
print(f"備份檔：{backup.name}")
print("請確認 tools/renal.html 與 tools/staging.html 已放在專案根目錄的 tools/ 底下。")

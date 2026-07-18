# Clinical tools launcher patch

用途：在 `clinicaltrialvghtpe/index.html` 右下角加入「臨床工具」浮動入口，連到：

- `./tools/renal.html`
- `./tools/staging.html`
- `./tools/index.html`

## 使用方式

1. 先確認專案根目錄有：
   - `index.html`
   - `tools/renal.html`
   - `tools/staging.html`
2. 把本資料夾內的 `patch_index.py`、`tools_launcher_snippet.html`、`PATCH_ROOT_INDEX.bat` 放到專案根目錄。
3. Windows 可直接雙擊 `PATCH_ROOT_INDEX.bat`。
4. 執行後會自動備份原始檔，例如：
   - `index.backup.before_tools_YYYYMMDD_HHMMSS.html`
5. 它只會在 `</body>` 前插入 launcher，不會改 Firebase、密碼、trial import/export 邏輯。

## 還原方式

若要還原，將備份檔改名回 `index.html` 即可。

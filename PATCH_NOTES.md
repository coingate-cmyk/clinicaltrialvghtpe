# v4.1.4 - 仍能收案篩選顯示與判斷加強

- 將「只顯示仍能收案」改為更醒目的綠色篩選 checkbox，避免上傳後看起來沒有變化。
- 勾選後會在結果數旁顯示「已篩選仍能收案」。
- 除了狀態欄的名額已滿/暫停/停止/結束，也會用目標收案與目前已收案判斷是否已滿。
- 保留 v4.1.3 的個別 cancer-line closedLines 判斷。

# v4.1.4 - 仍能收案篩選（2026-06-25）

- 篩選區新增「只顯示仍能收案」checkbox。
- 若整個 trial 狀態為暫停收案、名額已滿、停止收案、試驗結束、預備中/未 SIV 等，勾選後會自動篩掉。
- 若 trial 仍進行中，但某個癌種/線數在管理員畫面被標記為收滿/暫停，勾選後只會顯示仍有至少一個開放癌種/線數的 trial。
- 當同時選擇癌別或治療線數時，會檢查該癌別/該線數本身是否仍開放，避免同一 trial 其他 cohort 開放造成誤判。
- HER2 關鍵字邏輯暫不修改；陽性/陰性精準篩選先保留未來規劃，避免破壞目前全文搜尋。

# v4.1.2 - prior-line / PD-L1 / Exclusion parser 修正（2026-06-18）

- 修正 `PD-L1`、`anti-PD-L1` 中的 `1L` 被誤判為「一線」的問題。
- 補強英文前治療語句：`one prior line of standard therapy`、`1 prior line`、`prior 1 line`、`1L setting and disease progression` 會轉為目前 trial 的「二線」。
- 修正 MK-3475-06B 這類「接受過一線標準治療後」被顯示為一線的問題，現在會判斷為食道癌二線。
- 新增 `exclusion / Exclusion Criteria / 排除條件` 欄位 alias。
- 若 inclusion 欄內同時含 Inclusion + Exclusion Criteria，會自動拆成「收案條件」與「排除條件」，避免排除條件被塞在收案條件裡或顯示不出來。
- 重新匯入時保留既有核心功能與 v4.1.0 的個別癌種/線數 closedLines 狀態。

# v4.1.0 - 單一癌種/線數收滿或暫停標示（2026-06-16）

- 管理員編輯畫面：每個癌種底下的每個治療線數，新增「收滿/暫停」checkbox。
- 首頁 trial 標籤：被勾選的癌種/線數會以灰色、打叉與刪除線顯示，代表該線數目前未收案或暫停等待安監結果。
- 資料結構：在 cancerTypes 內以 closedLines 儲存個別線數狀態，保留舊資料相容性。
- 例：同一 trial 可以「胃癌二線收滿」，但「胰臟癌三線仍開放」。
- Excel/CSV/PDF 匯入仍不改原 parser；例行重新匯入時會盡量保留已手動勾選的 closedLines。

# Patch notes: stable 7af50be2 + import fixes

Base: clinicaltrialvghtpe commit `7af50be2f94ca21b4496a34d9d4afb13b612490b`.

Changes made in `index.html` and mirrored to `404.html`:

1. Excel / CSV import preservation
   - Kept the existing Excel (`parseExcelFile`) and CSV (`parseStudyStatusCsv`) import flow.
   - Added normalization after parsed rows are produced, rather than replacing the original parser.

2. Cancer type correction
   - Added cancer-type inference from row text for GI cancer categories.
   - ESCC / 食道鱗狀上皮癌 is normalized to 食道癌.
   - EAC / 食道腺癌 / GEJ adenocarcinoma is normalized to 胃癌類.
   - This fixes the common merged-cell / carry-forward problem where a row with 食道鱗癌 / ESCC text can remain mislabeled as the previous cancer type such as 胰臟癌.

3. Treatment-line normalization
   - Normalizes Arabic or English line expressions into Chinese searchable labels.
   - Examples: `1` -> `一線`; `2` -> `二線`; `2、3、4` -> `二線、三線、四線`; `4L+` -> `四線以上`.
   - Search filters now recognize combined lines such as `二、三線` and later lines such as `四線以上` under 多線.

4. PDF import added independently
   - Added PDF.js loader and `parsePdfFile()` / `pdfTextItemsToRows()`.
   - PDF import extracts text/table rows from PDF and then uses the same code-based upsert path.
   - Excel/CSV upload branches remain separate from PDF upload branch.

5. GitHub Pages fallback
   - `404.html` was mirrored to `index.html` so direct route / fallback loads the same app.

Validation done here:
- JavaScript syntax check using `node --check` passed.
- Parser smoke test passed for:
  - `2、3、4` -> `二線、三線、四線`
  - `二、三線` matches both 第二線 and 第三線 filters
  - a blank cancer cell after 胰臟癌 with `ESCC / 食道鱗狀細胞癌` text is corrected to 食道癌
  - `EAC / 食道腺癌 / GEJ adenocarcinoma` is normalized to 胃癌

Caveat:
- The uploaded stable app currently uses Firebase Firestore (`firebase-firestore-compat.js`), not Realtime Database. This patch preserves the stable app's existing Firebase behavior and does not migrate database architecture.


## 2026-06-16 multi-indication parser patch

- Added independent multi-indication extraction from title / inclusion / notes / nurse / enrollment text.
- Supports examples such as `胰臟癌二、三線 + 胃癌二線 + 膽管癌一線`.
- Supports cohort-style English examples such as `2L Gastric/GEJ/EAC`, `2L ESCC`, `1L ESCC`, `4L+ CRC`.
- Keeps Excel / CSV parser intact; extraction runs as a post-import normalization layer.
- Cancer + line filtering is now paired: selecting `膽道癌 + 二線` will not match a trial that only has `膽道癌一線` plus another cancer's 二線.


## v4.0.7 - Prior-therapy line logic 修正
- 修正「已接受至少 1-2 線之標準療法」這類 eligibility 語句：此處的 1-2 線代表已接受過的前治療，不是目前試驗線數。
- 轉換規則：已接受一線 → 目前二線；已接受二線 → 目前三線；已接受一至二線 / 1-2 lines → 目前二線、三線。
- 保留「作為第一線/第二線治療」、「1L/2L cohort」為目前線數，不往後推。
- 加入英文 prior therapy 語句支援：prior/previously treated/received/progressed after/failed after + line(s)。

## v4.0.8 - 版本顯示修正
- 修正 index.html / 404.html 頁面標題仍顯示 v4.0.5 的問題。
- 保留 v4.0.7 prior-therapy line logic：已接受 1-2 線標準療法 → 目前 trial 為二線、三線。


## v4.1.1 - 修正窗口分工誤判為收案線數
- 修正「膽管癌(一線) 找姵妤」這類護理師/窗口分工語句被誤判為「膽道癌一線」的問題。
- 保留正式收案描述，例如「收膽管癌正二.三線及胰臟癌二線、大腸癌二線」仍會正確解析。
- 維持 v4.1.0 個別癌種/線數收滿或暫停 checkbox 功能。


## v4.1.5 - Excel/PDF 匯入保守修正

- 修正 PDF 橫向表格匯入時，把 cohort/arm 附件頁與斷行文字誤拆成多筆試驗的問題。
- 匯入時新增 protocol code 驗證，避免把「一線 + 試驗名稱」、Phase、Sponsor 或電話誤當成試驗代號。
- PDF 只優先解析含 Study title / 代號 / 主要收案條件主表表頭的頁面；第二頁藥物 arm 說明不再參與匯入。
- 若 PDF 主表因版面斷裂無法形成完整列，會用唯一 protocol code 的保守 fallback 只建立一筆試驗。
- Excel 匯入改成自動選擇含主表表頭且可解析筆數最多的工作表，避免附件工作表干擾。

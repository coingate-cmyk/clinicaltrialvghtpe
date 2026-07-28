# v4.2.8 known status repair

Purpose: fix MK-3475-06C and MK-3475-06F being stuck as 試驗終了 due to older PDF/status import records in Firestore/localStorage.

Changes:
- Added one-time known-open status repair map for MK-3475-06C and MK-3475-06F.
- Repairs bad stored statuses even if older records were incorrectly stamped statusManuallyTouched/manual.
- Writes repaired records back to Firestore automatically when Firebase is enabled.
- Adds an admin button: 修復06C/06F狀態.
- Adds statusRepairVersion and statusOverrideConfirmedAt so future manual closures after this repair are respected.

QA: STATUS_v4_2_8_known_status_repair_QA.csv, 9/9 PASS.

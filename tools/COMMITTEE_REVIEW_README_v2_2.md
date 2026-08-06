AJCC pan-cancer v2.2 clean reset
Generated: 2026-08-06

Purpose
- Formal quick-staging tool is reset to verified/protected rows only.
- Pan-cancer site registry/search/grouping remains available.
- PDF auto-extraction outputs are kept as committee review candidates and are NOT loaded by the live staging tool.

Formal live tool data
- tools/staging_rules_7.csv: 280 rows (verified/protected v0.8.2 baseline)
- tools/staging_rules_8.csv: 264 rows (verified/protected v0.8.2 baseline)
- tools/staging_category_definitions.csv: 635 rows (verified/protected v0.8.2 baseline)
- tools/staging_site_registry_all_ajcc8_v0_9_0.csv: 99 pan-cancer registry sites for search/display

Review-only candidate data
- committee_stage_rule_candidates_PREFILLED_v2_2.csv: 765 prefilled candidate stage rows
- committee_TNM_definition_candidates_PREFILLED_v2_2.csv: 2186 prefilled candidate TNM definition rows
- staging_source_blocks_by_site_v2_1.csv: source blocks extracted from uploaded AJCC manuals

Hard rule in this version
- No surrogate AJCC8 rows are used by the live tool.
- No generic fallback definitions are used by the live tool.
- Candidate extraction files are for committee review only. Accepted rows should be copied into staging_rules_7/8.csv or staging_category_definitions.csv only after review.

Deployment
Upload/overwrite the tools/ folder contents. Browser cache may need Ctrl+F5 or ?v=2.2.

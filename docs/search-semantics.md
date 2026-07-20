# Search semantics

## Why plain keyword search is insufficient

A biomarker name can appear in eligibility, exclusion, treatment history, drug names, or descriptive text. Therefore a text hit does not automatically mean that the biomarker status is eligible for enrollment.

## HER2 query behavior

| Query | Meaning |
|---|---|
| `HER2` | Any mention of HER2, regardless of status or context |
| `HER2+`, `HER2 positive`, `HER2陽性` | Explicit HER2-positive eligible population |
| `HER2-`, `HER2 negative`, `HER2陰性` | Explicit HER2-negative eligible population |
| `HER2 low` | Explicit HER2-low eligible population |
| `HER2 non-positive`, `HER2非陽性` | Explicit negative/low population or a protocol that excludes HER2-positive disease |

A positive filter must not match:

- `HER2-negative`
- `HER2-low` unless positive disease is also explicitly eligible
- `Exclusion: HER2-positive/amplified tumor`
- a line that only says prior anti-HER2 therapy is excluded
- an ambiguous phrase such as `HER2 expression`
- a protocol that states HER2 status is unrestricted

## Context model

Each detected mention records:

- marker and status
- source field
- role: eligibility, exclusion, treatment history, or descriptive
- matching evidence
- rule identifier and confidence

This derived classification is initially calculated at runtime. It should not replace the original imported text.

## User interface direction

The search box should recognize structured phrases. When the user types bare `HER2`, the UI should offer status chips:

- 全部提及
- 陽性
- 陰性
- Low
- 非陽性／排除陽性
- 不限 HER2 狀態

Results should show a compact explanation such as `HER2陽性：IHC 3+ or ISH+`, `HER2-low：IHC 1+ or IHC 2+/ISH-`, or `排除HER2陽性`, so the user can verify why a trial matched.

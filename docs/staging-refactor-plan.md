# Staging Refactor Plan

## Branches

- Production: `main`
- Production backup: `stable-2026-07-20-recist`
- Refactor workspace: `staging-refactor`
- Baseline: `0c50cfee8956494c31efe0493ee080b592ba6bf2`

## Rules

1. Do not refactor directly on `main`.
2. Do not use GitHub Actions to patch `index.html`.
3. Keep standalone clinical tools independent from the main application.
4. Preserve current behavior and UI during the first extraction.
5. One logical change per commit; every step must be reversible.
6. Do not change Firebase collections, localStorage keys, trial fields, or import behavior during extraction.
7. Do not introduce npm, Vite, Webpack, JSX compilation, or another build system in the initial refactor.

## Target structure

```text
index.html
css/common.css
js/firebase.js
js/trials.js
js/import-export.js
js/ui.js
data/initial-trials.js
data/staging_rules_7.csv
tools/
docs/
```

Use one browser namespace during extraction:

```javascript
window.ClinicalTrialApp = window.ClinicalTrialApp || {};
```

## File ownership

- `index.html`: document shell, CDN dependencies, mount point, ordered script references, bootstrap.
- `data/initial-trials.js`: existing `INITIAL_TRIALS`, moved without data edits.
- `js/trials.js`: normalization, sorting, filtering, status rules, sanitization, deduplication, upsert, local cache.
- `js/firebase.js`: initialization, subscriptions, trial/subject writes, seeding, collection operations, unsubscribe handling.
- `js/import-export.js`: XLSX/PDF parsing, import analysis, JSON import/export, CSV output, print output.
- `js/ui.js`: React components, state, event handlers, modals, and render tree.
- `css/common.css`: existing common and print styles only.

## Phases

### 0. Baseline freeze

Create backup and staging branches from the same production commit. Add planning and regression documents only.

### 1. Baseline verification

Confirm staging matches production: login, admin login, trial count, filters, import/export, local cache, Firebase sync, and all standalone tools.

### 2. Extract initial data

Move `INITIAL_TRIALS` to `data/initial-trials.js`. Do not reformat or normalize records. Confirm identical counts and seed behavior.

### 3. Extract trial logic

Move normalization, filtering, sorting, sanitization, deduplication, and local-data helpers to `js/trials.js`. Confirm all search and filter results are unchanged.

### 4. Extract Firebase logic

Move Firebase functions to `js/firebase.js`. Confirm subscriptions, writes, subjects, local mode, seeding, and cleanup are unchanged.

### 5A. Extract exports

Move JSON, CSV/Excel-compatible, and print output code. Confirm fields and formatting are unchanged.

### 5B. Extract imports

Move JSON, XLSX, and PDF import code. Confirm known fixture counts, add/update/skip counts, duplicate handling, and protocol-code detection.

### 6. Extract UI

Move React components and `App` to `js/ui.js`. Preserve labels, button order, class names, layout, and modal behavior.

### 7. Extract CSS

Move existing common and print styles only. Do not redesign the site.

### 8. Move staging data

First copy `tools/staging_rules_7.csv` to `data/`, then update the staging tool path, verify the deployed path, and remove the old copy only in a later commit.

## Production promotion

A phase may be proposed for production only after the regression checklist passes and the diff contains one reversible logical change. Promotion must use a reviewed pull request. Never force-update `main` and never reintroduce an Actions patch workflow.
# Refactor Regression Checklist

Complete this checklist before accepting each extraction phase.

## Baseline record

- [ ] Record production commit SHA.
- [ ] Record total visible trial count.
- [ ] Record open-enrollment filtered count.
- [ ] Record archived-trial behavior.
- [ ] Record current standalone tool links and order.
- [ ] Confirm RECIST appears after CTCAE and before the tools index.
- [ ] Confirm no workflow patches `index.html`.

## Access and application start

- [ ] Correct access password opens the application.
- [ ] Incorrect access password is rejected.
- [ ] Administrator login succeeds with the existing behavior.
- [ ] Administrator logout returns to non-admin mode.
- [ ] Initial loading state completes without console errors.
- [ ] Reloading the page preserves expected local behavior.

## Trial list and filters

- [ ] Initial trial count matches baseline.
- [ ] Trial cards display the same fields and text.
- [ ] Search by trial code matches baseline.
- [ ] Search by title matches baseline.
- [ ] Search by PI matches baseline.
- [ ] Cancer-type filter matches baseline.
- [ ] Treatment-line filter matches baseline.
- [ ] Cancer sorting matches baseline.
- [ ] Treatment-line sorting matches baseline.
- [ ] Archived-trial toggle matches baseline.
- [ ] Open-enrollment-only toggle matches baseline.
- [ ] Combined search and filters match baseline.

## Trial management

- [ ] Add trial works in the test environment.
- [ ] Edit trial preserves all fields.
- [ ] Same-code import/update does not create an unintended duplicate.
- [ ] Delete trial follows the existing confirmation and persistence behavior.
- [ ] Subject list opens for the selected trial.
- [ ] Adding a subject follows the existing behavior.

## Local data

- [ ] Existing localStorage keys are unchanged.
- [ ] Existing encrypted trial cache loads successfully.
- [ ] Existing encrypted subject cache loads successfully.
- [ ] Saving trials updates the local cache.
- [ ] Saving subjects updates the local cache.
- [ ] Invalid or unreadable cached data fails safely.

## Firebase test environment

- [ ] Firebase initialization completes.
- [ ] Trial subscription receives data.
- [ ] Subject subscription receives data.
- [ ] Trial create/update synchronizes.
- [ ] Trial delete synchronizes.
- [ ] Subject changes synchronize.
- [ ] Initial seed does not create duplicates.
- [ ] Disabling Firebase returns to local mode.
- [ ] Listener cleanup/unsubscribe still occurs.
- [ ] Destructive collection tests are performed only in a controlled test environment.

## Import fixtures

For each known fixture, record expected and actual values.

| Fixture | Expected parsed | Expected added | Expected updated | Expected skipped | Actual/result |
|---|---:|---:|---:|---:|---|
| ABBVIE STUDY.xlsx | 8 | 1 | 7 | 0 | |
| ABBVIE STUDY.pdf | | | | | |
| Study status PDF | | | | | |
| Single-trial PDF | 1 | | | | |
| Wide single-trial PDF | 1 | | | | |

Additional checks:

- [ ] XLSX import count matches baseline.
- [ ] Standard table PDF count matches baseline.
- [ ] Wide-page fallback matches baseline.
- [ ] Single-record fallback matches baseline.
- [ ] Duplicate protocol codes consolidate as before.
- [ ] Known false-positive codes remain excluded.
- [ ] Leading zeroes in valid identifiers are preserved where required.
- [ ] Cancer type and treatment line extraction match baseline.
- [ ] PI and nurse field cleanup match baseline.
- [ ] Add/update/skip summary matches baseline.

## JSON, CSV, and print output

- [ ] JSON export contains trials, subjects, and update time.
- [ ] Exported JSON can be imported again.
- [ ] JSON import merges by trial code as before.
- [ ] CSV column order is unchanged.
- [ ] CSV opens with readable Traditional Chinese text.
- [ ] Exported filenames follow the existing behavior.
- [ ] Print/PDF view opens.
- [ ] Print table contains the same fields and trial count.

## Standalone tools

- [ ] `tools/index.html` opens.
- [ ] `tools/renal.html` opens and calculates.
- [ ] `tools/quick-staging.html` opens and loads rules.
- [ ] `tools/ctcae.html` opens and searches.
- [ ] `tools/recist.html` opens and calculates.
- [ ] Tool links back to the tools index work.
- [ ] Tool links back to the main system work.
- [ ] Standalone tools do not initialize Firebase.
- [ ] Standalone tools do not alter the main application's storage keys.
- [ ] RECIST JSON export/import remains functional.

## Visual parity

- [ ] Main title and version text are unchanged.
- [ ] Button labels and order are unchanged.
- [ ] Search and filter placement are unchanged.
- [ ] Trial-card layout is unchanged.
- [ ] Modal layout and behavior are unchanged.
- [ ] Responsive behavior is not visibly worse.
- [ ] Print styling is unchanged.
- [ ] No unrequested UI redesign is included.

## Browser checks

- [ ] Chrome desktop.
- [ ] Edge desktop.
- [ ] Mobile-width responsive view.
- [ ] No new JavaScript errors in the console.
- [ ] No missing script, CSS, CSV, worker, or source-map requests that affect function.

## Rollback readiness

- [ ] The phase is contained in one logical commit or a clearly identified short series.
- [ ] The parent commit is recorded.
- [ ] Reverting the phase restores the previous working staging version.
- [ ] `main` is unchanged.
- [ ] `stable-2026-07-20-recist` is unchanged.
- [ ] No GitHub Actions patch workflow was added.
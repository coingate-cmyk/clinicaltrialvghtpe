from pathlib import Path

# The classification repairs are already present in index.html. Reuse this existing,
# authorized workflow entrypoint to apply the 2026-08-22 Study Status + PDF import patch.
patch = Path('scripts/patch_study_status_20260822.py')
if not patch.exists():
    raise SystemExit(f'Missing patch script: {patch}')
exec(compile(patch.read_text(encoding='utf-8'), str(patch), 'exec'))

index_path = Path('index.html')
html = index_path.read_text(encoding='utf-8')

# Keep line-classification provenance in the data, but hide it from the normal user view.
# Admin login still shows the provenance badge/tooltip and the legend for review/editing.
old_title = "title: (closed ? '此癌種 / 線數目前收滿或暫停收案；' : '') + '線別來源：' + getLineSourceLabel(lineSource),"
new_title = "title: (closed ? '此癌種 / 線數目前收滿或暫停收案；' : '') + (props.isLoggedIn ? '線別來源：' + getLineSourceLabel(lineSource) : ''),"
if old_title in html:
    html = html.replace(old_title, new_title, 1)
elif new_title not in html:
    raise SystemExit('Could not locate TrialCard line-source tooltip')

old_badge = "e('span', {className: 'px-1.5 py-0.5 rounded-full border text-[10px] leading-none no-underline ' + getLineSourceBadgeClass(lineSource)}, getLineSourceLabel(lineSource))"
new_badge = "props.isLoggedIn ? e('span', {className: 'px-1.5 py-0.5 rounded-full border text-[10px] leading-none no-underline ' + getLineSourceBadgeClass(lineSource)}, getLineSourceLabel(lineSource)) : null"
if old_badge in html:
    html = html.replace(old_badge, new_badge, 1)
elif new_badge not in html:
    raise SystemExit('Could not locate TrialCard line-source badge')

old_legend = "e('div', {className: 'mb-4 flex flex-wrap items-center gap-2 text-xs text-slate-600'},\n                e('span', {className: 'font-semibold'}, '線別來源標記：'),"
new_legend = "isAdmin && e('div', {className: 'mb-4 flex flex-wrap items-center gap-2 text-xs text-slate-600'},\n                e('span', {className: 'font-semibold'}, '線別來源標記：'),"
if old_legend in html:
    html = html.replace(old_legend, new_legend, 1)
elif new_legend not in html:
    raise SystemExit('Could not locate line-source legend')

# Mobile layout optimization (v4.3.5-mobile-layout-20260822).
# Main goals: remove accidental horizontal overflow, reduce edge padding on phones,
# and let long protocol codes / metadata wrap instead of widening the viewport.
def replace_once(old, new, label):
    global html
    if old in html:
        html = html.replace(old, new, 1)
    elif new not in html:
        raise SystemExit(f'Could not locate mobile-layout target: {label}')

replace_once(
    '<body class="bg-gradient-to-br from-slate-50 to-blue-50">',
    '<body class="bg-gradient-to-br from-slate-50 to-blue-50 overflow-x-hidden">',
    'body horizontal overflow guard'
)
replace_once(
    "e('div', {className: 'max-w-7xl mx-auto px-4 py-4'},",
    "e('div', {className: 'max-w-7xl mx-auto px-3 sm:px-4 py-3 sm:py-4'},",
    'mobile header padding'
)
replace_once(
    "e('h1', {className: 'text-2xl font-bold text-slate-800'}, '臨床試驗管理系統 v4.3.4 Firebase版'),",
    "e('h1', {className: 'min-w-0 text-lg sm:text-2xl font-bold leading-tight text-slate-800'}, '臨床試驗管理系統 v4.3.4 Firebase版'),",
    'mobile header title'
)
replace_once(
    "className: 'px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700'",
    "className: 'shrink-0 ml-3 px-3 sm:px-6 py-2 text-sm sm:text-base bg-blue-600 text-white rounded-lg hover:bg-blue-700'",
    'mobile admin button'
)
replace_once(
    "e('div', {className: 'max-w-7xl mx-auto px-4 py-8'},",
    "e('div', {className: 'max-w-7xl mx-auto px-2 sm:px-4 py-4 sm:py-8'},",
    'mobile page padding'
)
replace_once(
    "e('div', {className: 'grid grid-cols-2 gap-4'},\n                    e('select', {\n                        value: cancerType,",
    "e('div', {className: 'grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-4'},\n                    e('select', {\n                        value: cancerType,",
    'mobile filter grid'
)

# Restrict card-specific edits to TrialCard so forms/modals keep their desktop grids.
card_start = html.find('function TrialCard(props) {')
card_end = html.find('function SubjectFormModal(props) {', card_start)
if card_start < 0 or card_end < 0:
    raise SystemExit('Could not isolate TrialCard for mobile optimization')
card = html[card_start:card_end]

card_pairs = [
    (
        "return e('div', {className: 'bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow'},",
        "return e('div', {className: 'min-w-0 bg-white rounded-xl shadow-md p-4 sm:p-6 hover:shadow-lg transition-shadow'},"
    ),
    (
        "e('div', {className: 'flex justify-between items-start mb-4'},\n            e('div', null,",
        "e('div', {className: 'flex justify-between items-start gap-3 min-w-0 mb-4'},\n            e('div', {className: 'min-w-0 flex-1'},"
    ),
    (
        "e('h3', {className: 'text-xl font-bold text-gray-800'}, trial.code),",
        "e('h3', {className: 'text-lg sm:text-xl font-bold leading-tight text-gray-800 break-all'}, trial.code),"
    ),
    (
        ": 'text-gray-600 mt-1'",
        ": 'text-gray-600 mt-1 break-words'"
    ),
    (
        "e('div', {className: 'flex items-center gap-2'},\n                e('span', {\n                    className: getTrialStatusBadgeClass(trial)",
        "e('div', {className: 'flex items-center gap-2 shrink-0'},\n                e('span', {\n                    className: getTrialStatusBadgeClass(trial)"
    ),
    (
        "e('div', {className: 'grid grid-cols-3 gap-4 text-sm'},",
        "e('div', {className: 'grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-4 text-sm'},"
    ),
]
for old, new in card_pairs:
    if old in card:
        card = card.replace(old, new, 1)
    elif new not in card:
        raise SystemExit(f'Could not locate TrialCard mobile target: {old[:70]}')

# Expanded trial details should stack on phones, but remain two columns on larger screens.
card = card.replace(
    "e('div', {className: 'grid grid-cols-2 gap-4'},",
    "e('div', {className: 'grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-4'},"
)

html = html[:card_start] + card + html[card_end:]

marker = '// v4.3.5-mobile-layout-20260822'
if marker not in html:
    anchor = 'const {useState, useEffect, useMemo, useRef} = React;'
    if anchor not in html:
        raise SystemExit('Could not place mobile layout version marker')
    html = html.replace(anchor, anchor + '\n' + marker, 1)

index_path.write_text(html, encoding='utf-8')
print('Line-source provenance preserved for admin; mobile layout optimized.')

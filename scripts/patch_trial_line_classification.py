from pathlib import Path

# The classification repairs are already present in index.html. Reuse this existing,
# authorized workflow entrypoint to apply the 2026-08-22 Study Status + PDF import patch.
patch = Path('scripts/patch_study_status_20260822.py')
if not patch.exists():
    raise SystemExit(f'Missing patch script: {patch}')
exec(compile(patch.read_text(encoding='utf-8'), str(patch), 'exec'))

# Keep line-classification provenance in the data, but hide it from the normal user view.
# Admin login still shows the provenance badge/tooltip and the legend for review/editing.
index_path = Path('index.html')
html = index_path.read_text(encoding='utf-8')

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

index_path.write_text(html, encoding='utf-8')
print('Line-source provenance hidden from normal view; admin view preserved.')

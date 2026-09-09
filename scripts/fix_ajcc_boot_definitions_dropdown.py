from pathlib import Path
import csv, json, re

HTML = Path('tools/quick-staging.html')
RULE7 = Path('tools/staging_rules_7.csv')
RULE8 = Path('tools/staging_rules_8.csv')
DEFS = Path('tools/staging_category_definitions.csv')
RULE_COLS = ['site','edition','classification','t','n','m','grade','location','stage','note']
DEF_COLS = ['site','edition','classification','category_type','category','short_definition','detail_note','verification_status']


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def compact(rows, cols):
    return json.dumps(
        [{c: (r.get(c, '') or '').strip() for c in cols} for r in rows],
        ensure_ascii=False,
        separators=(',', ':')
    )


def replace_array(html, name, payload):
    pat = rf'const\s+{re.escape(name)}\s*=\s*\[[\s\S]*?\];'
    repl = f'const {name}={payload};'
    new, n = re.subn(pat, repl, html, count=1)
    if n != 1:
        raise SystemExit(f'Could not replace {name}: matches={n}')
    return new


def main():
    html = HTML.read_text(encoding='utf-8')
    r7 = read_csv(RULE7)
    r8 = read_csv(RULE8)
    defs = read_csv(DEFS)

    # Single source of truth: embedded runtime packs are rebuilt from canonical CSV files.
    html = replace_array(html, 'EMBEDDED_RULES_7', compact(r7, RULE_COLS))
    html = replace_array(html, 'EMBEDDED_RULES_8', compact(r8, RULE_COLS))
    html = replace_array(html, 'EMBEDDED_DEFINITIONS', compact(defs, DEF_COLS))

    # Critical regression fix: core repair accidentally converted the mutable runtime
    # rule store to const. boot() reassigns it, so the whole UI initialization stopped.
    pat_static = r'(?:const|let)\s+staticRules\s*=\s*\[[\s\S]*?\];'
    html, n = re.subn(pat_static, 'let staticRules=[];', html, count=1)
    if n != 1:
        raise SystemExit(f'Could not normalize staticRules declaration: matches={n}')

    # Keep runtime definition/coverage stores mutable because boot() assigns embedded packs.
    html = re.sub(r'(?:const|let)\s+staticDefinitions\s*=\s*\[[\s\S]*?\];', 'let staticDefinitions=[];', html, count=1)
    html = re.sub(r'(?:const|let)\s+staticCoverage\s*=\s*\[[\s\S]*?\];', 'let staticCoverage=[];', html, count=1)

    # Organ-system dropdown: do not rebuild its own <option> list inside its change event.
    old_refresh = """function refreshSites(){
 const allVals=sortSitesForDisplay(uniq(baseSites.concat(allRules().map(r=>r.site),allDefinitions().map(d=>d.site))));
 refreshSiteGroupFilter(allVals);
 const q=(typeof siteSearch!=='undefined'&&siteSearch)?siteSearch.value:'';
 const groupEl=document.getElementById('siteGroupFilter');
 const groupFilter=groupEl?(groupEl.value||'全部'):'全部';"""
    new_refresh = """function refreshSites(options={}){
 const allVals=sortSitesForDisplay(uniq(baseSites.concat(allRules().map(r=>r.site),allDefinitions().map(d=>d.site))));
 if(options.rebuildGroups)refreshSiteGroupFilter(allVals);
 const searchEl=document.getElementById('siteSearch');
 const q=searchEl?searchEl.value:'';
 const groupEl=document.getElementById('siteGroupFilter');
 const groupFilter=groupEl?(groupEl.value||'全部'):'全部';"""
    if old_refresh in html:
        html = html.replace(old_refresh, new_refresh, 1)
    elif new_refresh not in html:
        raise SystemExit('Could not patch refreshSites dropdown behavior')

    old_events = """site.onchange=()=>changed('site');if(typeof siteSearch!=='undefined'&&siteSearch){siteSearch.oninput=()=>{refreshSites();changed('site')}}if(typeof siteGroupFilter!=='undefined'&&siteGroupFilter){siteGroupFilter.onchange=()=>{refreshSites();changed('site')}}mode.onchange=()=>changed('mode');"""
    new_events = """site.onchange=()=>changed('site');const siteSearchEl=document.getElementById('siteSearch');const siteGroupFilterEl=document.getElementById('siteGroupFilter');if(siteSearchEl){siteSearchEl.addEventListener('input',()=>{refreshSites({rebuildGroups:false});changed('site')})}if(siteGroupFilterEl){siteGroupFilterEl.addEventListener('change',()=>{refreshSites({rebuildGroups:false});changed('site')})}mode.onchange=()=>changed('mode');"""
    if old_events in html:
        html = html.replace(old_events, new_events, 1)
    elif new_events not in html:
        raise SystemExit('Could not patch organ-system/search event handlers')

    # Rebuild groups only when the data source changes or on boot.
    html = html.replace("function importCSV(){const incoming=parseCSV(csvbox.value);localStorage.setItem(USER_RULES_KEY,JSON.stringify(incoming));refreshSites();setInfo();refreshCascade('site');lookup()}",
                        "function importCSV(){const incoming=parseCSV(csvbox.value);localStorage.setItem(USER_RULES_KEY,JSON.stringify(incoming));refreshSites({rebuildGroups:true});setInfo();refreshCascade('site');lookup()}")
    html = html.replace("function clearRules(){localStorage.removeItem(USER_RULES_KEY);refreshSites();setInfo();refreshCascade('site');lookup()}",
                        "function clearRules(){localStorage.removeItem(USER_RULES_KEY);refreshSites({rebuildGroups:true});setInfo();refreshCascade('site');lookup()}")
    html = html.replace("refreshSites();setInfo();refreshCascade('site');lookup();", "refreshSites({rebuildGroups:true});setInfo();refreshCascade('site');lookup();", 1)

    HTML.write_text(html, encoding='utf-8')
    print(f'Fixed AJCC boot; embedded AJCC7={len(r7)}, AJCC8={len(r8)}, definitions={len(defs)}.')


if __name__ == '__main__':
    main()

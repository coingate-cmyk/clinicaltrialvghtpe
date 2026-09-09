from pathlib import Path
import csv
import json
import re

RULE7 = Path('tools/staging_rules_7.csv')
RULE8 = Path('tools/staging_rules_8.csv')
HTML = Path('tools/quick-staging.html')
COLS = ['site','edition','classification','t','n','m','grade','location','stage','note']

# Breast quick mode deliberately exposes ANATOMIC stage only. AJCC8 prognostic stage
# depends on grade/ER/PR/HER2 (and selected multigene information) and must not be
# collapsed into a TNM-only table.
BREAST_ANATOMIC = [
    ('Tis','N0','M0','0'),
    ('T1','N0','M0','IA'),
    ('T0|T1','N1mi','M0','IB'),
    ('T0|T1','N1','M0','IIA'),
    ('T2','N0','M0','IIA'),
    ('T2','N1','M0','IIB'),
    ('T3','N0','M0','IIB'),
    ('T0|T1|T2','N2','M0','IIIA'),
    ('T3','N1|N2','M0','IIIA'),
    ('T4','N0|N1|N2','M0','IIIB'),
    ('Any','N3','M0','IIIC'),
    ('Any','Any','M1','IV'),
]

def read_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write_rows(path, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: (r.get(c,'') or '').strip() for c in COLS})

def clean_breast(path, edition):
    rows = [r for r in read_rows(path) if (r.get('site') or '').strip() != 'Breast']
    note = (f'Breast {edition} ANATOMIC stage group only. Quick mode intentionally does not '
            'calculate AJCC prognostic stage from hidden grade/ER/PR/HER2 or multigene factors.')
    breast = []
    for t,n,m,stage in BREAST_ANATOMIC:
        breast.append({
            'site':'Breast','edition':edition,'classification':'any',
            't':t,'n':n,'m':m,'grade':'Any','location':'Any','stage':stage,'note':note
        })
    write_rows(path, rows + breast)
    return len(rows), len(breast)

def patch_html():
    html = HTML.read_text(encoding='utf-8')

    # Make stage basis an explicit user choice. This prevents a pathological TNM from
    # silently being interpreted through the clinical table (especially important in Stomach).
    old_select = ('<select id="classification" class="mt-1 w-full border rounded p-2">'
                  '<option value="clinical" selected>Clinical / cTNM</option>'
                  '<option value="pathological">Pathological / pTNM</option>'
                  '<option value="yp">Post-neoadjuvant / ypTNM</option>'
                  '<option value="recurrence">Recurrence / rTNM</option></select>')
    new_select = ('<select id="classification" class="mt-1 w-full border rounded p-2">'
                  '<option value="" selected>請先選擇 / Select basis</option>'
                  '<option value="clinical">Clinical / cTNM</option>'
                  '<option value="pathological">Pathological / pTNM</option>'
                  '<option value="yp">Post-neoadjuvant / ypTNM</option>'
                  '<option value="recurrence">Recurrence / rTNM</option></select>')
    if old_select in html:
        html = html.replace(old_select, new_select, 1)
    elif 'value="" selected>請先選擇 / Select basis' not in html:
        raise SystemExit('Could not patch Stage basis selector')

    # Parent matching: T1mi belongs to T1 family; T4d belongs to T4 family.
    old_prefix = "function categoryPrefix(v){return String(v||'').replace(/[abc]$/i,'')}"
    new_prefix = "function categoryPrefix(v){const s=String(v||'');if(/^T1mi$/i.test(s))return'T1';return s.replace(/[a-d]$/i,'')}"
    if old_prefix in html:
        html = html.replace(old_prefix, new_prefix, 1)
    elif new_prefix not in html:
        raise SystemExit('Could not patch categoryPrefix')

    # Give a truthful Breast note: anatomic stage is supported; prognostic stage is not guessed.
    old_breast_note = ('"Breast": "Smart-form needed before validated release.；Required extra inputs: '
                       'grade/G; ER/PR/HER2; Oncotype/multigene；Stage table metadata only; rule rows require separate validation."')
    new_breast_note = ('"Breast": "Quick mode 僅顯示 AJCC anatomic stage group（TNM）；不以隱藏的 grade/ER/PR/HER2 或 multigene 資料推算 prognostic stage。若要 prognostic stage，需另用完整乳癌 smart-form。"')
    if old_breast_note in html:
        html = html.replace(old_breast_note, new_breast_note, 1)
    elif new_breast_note not in html:
        raise SystemExit('Could not patch Breast site note')

    # When basis is blank, tell the user what to do instead of saying the cancer has no rules.
    old_hint = "if(!rs.length){setOptions(t,ORD.t,'t');setOptions(n,ORD.n,'n');setOptions(m,ORD.m,'m');setOptions(grade,ORD.grade,'grade');setOptions(location,ORD.location,'location');hint.textContent='此癌種 / stage basis 目前沒有可用規則；可匯入補充 CSV。'}"
    new_hint = "if(!rs.length){setOptions(t,ORD.t,'t');setOptions(n,ORD.n,'n');setOptions(m,ORD.m,'m');setOptions(grade,ORD.grade,'grade');setOptions(location,ORD.location,'location');hint.textContent=(mode.value!=='MATRIX'&&!classification.value)?'請先選擇 Stage basis（Clinical / Pathological / ypTNM）。胃癌等癌種的 cStage 與 pStage 本來就不同。':'此癌種 / stage basis 目前沒有可用規則；可匯入補充 CSV。'}"
    if old_hint in html:
        html = html.replace(old_hint, new_hint, 1)
    elif new_hint not in html:
        raise SystemExit('Could not patch no-rule hint')

    # Block lookup until basis is explicit (Matrix mode already defines both bases itself).
    old_lookup = "function lookup(){const eds=selectedEditions();if(mode.value==='MATRIX'){"
    new_lookup = "function lookup(){if(mode.value!=='MATRIX'&&!classification.value){window.lastResults=[];result.innerHTML='<div class=\"rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-900\"><b>請先選擇 Stage basis。</b><br><span class=\"text-sm\">Clinical / cTNM、Pathological / pTNM 與 ypTNM 可能有不同 stage group；系統不再替你默認其中一種。</span></div>';return}const eds=selectedEditions();if(mode.value==='MATRIX'){"
    if old_lookup in html:
        html = html.replace(old_lookup, new_lookup, 1)
    elif new_lookup not in html:
        raise SystemExit('Could not patch lookup basis guard')

    # Re-embed canonical rules after cleaning CSVs.
    allrows = read_rows(RULE7) + read_rows(RULE8)
    payload = json.dumps([{c:(r.get(c,'') or '').strip() for c in COLS} for r in allrows], ensure_ascii=False, separators=(',',':'))
    patterns = [r'const staticRules\s*=\s*\[[\s\S]*?\];', r'let staticRules\s*=\s*\[[\s\S]*?\];']
    for pat in patterns:
        if re.search(pat, html):
            html = re.sub(pat, 'const staticRules='+payload+';', html, count=1)
            break
    else:
        raise SystemExit('Could not locate embedded staticRules')

    HTML.write_text(html, encoding='utf-8')

if __name__ == '__main__':
    n7,b7 = clean_breast(RULE7, 'AJCC7')
    n8,b8 = clean_breast(RULE8, 'AJCC8')
    patch_html()
    print(f'AJCC core repair complete: AJCC7 non-Breast {n7}+{b7}; AJCC8 non-Breast {n8}+{b8}.')

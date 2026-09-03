from pathlib import Path

PATH = Path('tools/chemo-dose.html')
text = PATH.read_text(encoding='utf-8')

if 'id="bsaMode"' in text and 'id="manualBsa"' in text and 'bsaMode' in text:
    print('manual BSA patch already applied')
    raise SystemExit(0)

old_ui = '''          <div class="grid grid-cols-2 gap-3 min-w-0">
            <label class="block text-sm min-w-0">性別
'''
new_ui = '''          <div class="mb-4 rounded-xl border bg-slate-50 p-3">
            <label class="block text-sm font-semibold">BSA 輸入方式
              <select id="bsaMode" class="mt-1 w-full min-w-0 border bg-white rounded-lg p-2.5 font-normal">
                <option value="calculated">由身高＋體重計算（Mosteller）</option>
                <option value="manual">直接輸入 BSA</option>
              </select>
            </label>
            <label id="manualBsaWrap" class="hidden block text-sm mt-3">BSA m²
              <input id="manualBsa" type="number" min="0.3" max="4.0" step="0.01" value="1.80" inputmode="decimal" class="mt-1 w-full min-w-0 border bg-white rounded-lg p-2.5">
              <span class="block mt-1 text-xs text-slate-500">直接使用已知 BSA 計算 mg/m² 劑量；不需要重新輸入身高與體重。</span>
            </label>
          </div>
          <div class="grid grid-cols-2 gap-3 min-w-0">
            <label class="block text-sm min-w-0">性別
'''
if old_ui not in text:
    raise SystemExit('UI anchor not found')
text = text.replace(old_ui, new_ui, 1)

old_get = '''function getPatient(){
  const sex = val('sex'), age = num('age'), h = num('height'), w = num('weight'), scr = num('scr');
  const IBW = ibw(sex, h);
  const AdjBW = adjustedBw(w, IBW);
  const BSA = bsa(h, w);
  const AdjBSA = bsa(h, AdjBW);
'''
new_get = '''function getPatient(){
  const sex = val('sex'), age = num('age'), h = num('height'), w = num('weight'), scr = num('scr');
  const bsaMode = val('bsaMode');
  const manualBSA = num('manualBsa');
  const calculatedBSA = bsa(h, w);
  const BSA = bsaMode === 'manual' ? manualBSA : calculatedBSA;
  const IBW = ibw(sex, h);
  const AdjBW = adjustedBw(w, IBW);
  const AdjBSA = bsa(h, AdjBW);
'''
if old_get not in text:
    raise SystemExit('getPatient anchor not found')
text = text.replace(old_get, new_get, 1)

old_return = '''  return {sex, age, h, w, scr, IBW, AdjBW, BSA, AdjBSA, BMI, CG, CKD, CKDde, renal, renalSource};
}'''
new_return = '''  return {sex, age, h, w, scr, bsaMode, manualBSA, calculatedBSA, IBW, AdjBW, BSA, AdjBSA, BMI, CG, CKD, CKDde, renal, renalSource};
}'''
if old_return not in text:
    raise SystemExit('return anchor not found')
text = text.replace(old_return, new_return, 1)

old_render_start = '''function renderPatient(){
  const p = getPatient();
  $('bodyResults').innerHTML = `
    <div class="rounded-lg bg-slate-100 p-3 min-w-0"><div class="text-xs text-slate-500">Actual BSA</div><div class="font-bold text-lg">${fmt(p.BSA,2)} m²</div></div>
'''
new_render_start = '''function renderPatient(){
  const p = getPatient();
  $('manualBsaWrap').classList.toggle('hidden', p.bsaMode !== 'manual');
  const bsaLabel = p.bsaMode === 'manual' ? 'Dosing BSA（manual）' : 'Actual BSA（Mosteller）';
  const calculatedBsaNote = p.bsaMode === 'manual'
    ? `<div class="rounded-lg bg-blue-50 p-3 col-span-2 min-w-0"><div class="text-xs text-blue-700">Mosteller BSA（reference only）</div><div class="font-bold text-blue-950">${fmt(p.calculatedBSA,2)} m²</div></div>`
    : '';
  $('bodyResults').innerHTML = `
    <div class="rounded-lg bg-slate-100 p-3 min-w-0"><div class="text-xs text-slate-500">${bsaLabel}</div><div class="font-bold text-lg">${fmt(p.BSA,2)} m²</div></div>
'''
if old_render_start not in text:
    raise SystemExit('renderPatient anchor not found')
text = text.replace(old_render_start, new_render_start, 1)

old_render_end = '''    <div class="rounded-lg bg-amber-50 p-3 col-span-2 min-w-0"><div class="text-xs text-amber-700">AdjBW-based BSA（reference）</div><div class="font-bold text-amber-950">${fmt(p.AdjBSA,2)} m²</div></div>`;
'''
new_render_end = '''    <div class="rounded-lg bg-amber-50 p-3 col-span-2 min-w-0"><div class="text-xs text-amber-700">AdjBW-based BSA（reference）</div><div class="font-bold text-amber-950">${fmt(p.AdjBSA,2)} m²</div></div>
    ${calculatedBsaNote}`;
'''
if old_render_end not in text:
    raise SystemExit('renderPatient end anchor not found')
text = text.replace(old_render_end, new_render_end, 1)

old_summary = '''function summaryText(){
  const p = getPatient();
  const lines = [`Height ${fmt(p.h,1)} cm / Weight ${fmt(p.w,1)} kg / BSA ${fmt(p.BSA,2)} m² / AdjBW ${fmt(p.AdjBW,1)} kg / AdjBW-BSA ${fmt(p.AdjBSA,2)} m²`];
'''
new_summary = '''function summaryText(){
  const p = getPatient();
  const bodySummary = p.bsaMode === 'manual'
    ? `BSA ${fmt(p.BSA,2)} m² (manual input)`
    : `Height ${fmt(p.h,1)} cm / Weight ${fmt(p.w,1)} kg / BSA ${fmt(p.BSA,2)} m² / AdjBW ${fmt(p.AdjBW,1)} kg / AdjBW-BSA ${fmt(p.AdjBSA,2)} m²`;
  const lines = [bodySummary];
'''
if old_summary not in text:
    raise SystemExit('summary anchor not found')
text = text.replace(old_summary, new_summary, 1)

old_listeners = '''['sex','age','height','weight','scr','cgWeight','renalSource','manualGfr'].forEach(id => {'''
new_listeners = '''['bsaMode','manualBsa','sex','age','height','weight','scr','cgWeight','renalSource','manualGfr'].forEach(id => {'''
if old_listeners not in text:
    raise SystemExit('listener anchor not found')
text = text.replace(old_listeners, new_listeners, 1)

old_default_logic = '''          <b>預設邏輯：</b>mg/m² 使用 actual-weight BSA；mg/kg 使用 actual BW。AdjBW / AdjBW-BSA 只有在你主動選擇時才套用。Dose reduction 先乘比例，再套 max dose，最後才做 rounding。'''
new_default_logic = '''          <b>預設邏輯：</b>mg/m² 預設使用 Mosteller actual-weight BSA；若切換為「直接輸入 BSA」，mg/m² 與相關 BSA-based 計算改用手動 BSA。mg/kg 仍使用 actual BW。AdjBW / AdjBW-BSA 只有在你主動選擇時才套用。Dose reduction 先乘比例，再套 max dose，最後才做 rounding。'''
if old_default_logic not in text:
    raise SystemExit('default logic anchor not found')
text = text.replace(old_default_logic, new_default_logic, 1)

PATH.write_text(text, encoding='utf-8')
print('manual BSA patch applied')

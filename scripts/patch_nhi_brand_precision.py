#!/usr/bin/env python3
from pathlib import Path

p=Path('tools/nhi/assets/clinical-map.js')
s=p.read_text(encoding='utf-8')
old="""  function brandsForRecord(x) {
    if (!officialBrandProducts.length) return [];
    const hay = directDrugHay(x);
    const rows = officialBrandProducts.filter(p => ingredientTerms(p.ingredient).some(t => t.length >= 4 && hay.includes(t)));
    const seen = new Set();
    return rows.filter(p => {
      const name = productName(p);
      const k = norm(name);
      if (!name || seen.has(k)) return false;
      seen.add(k);
      return true;
    }).sort((a,b)=>productName(a).localeCompare(productName(b),'zh-Hant',{sensitivity:'base'}));
  }
"""
new="""  function brandsForRecord(x) {
    if (!officialBrandProducts.length) return [];
    const matchIngredient = hay => officialBrandProducts.filter(p => ingredientTerms(p.ingredient).some(t => t.length >= 4 && hay.includes(t)));
    // Prefer the reimbursed drug field. Only fall back to the regimen when the record's drug label is a class/combination label.
    let rows = matchIngredient(norm(x.drug || ''));
    if (!rows.length) rows = matchIngredient(norm(x.regimen || ''));
    const seen = new Set();
    return rows.filter(p => {
      const name = productName(p);
      const k = norm(name);
      if (!name || seen.has(k)) return false;
      seen.add(k);
      return true;
    }).sort((a,b)=>productName(a).localeCompare(productName(b),'zh-Hant',{sensitivity:'base'}));
  }
"""
if new in s:
    print('Brand precision patch already applied')
elif old in s:
    p.write_text(s.replace(old,new,1),encoding='utf-8')
    print('Brand precision patch applied')
else:
    raise SystemExit('brandsForRecord anchor missing')

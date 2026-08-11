window.NHI_DATA = {
  "meta": {
    "title": "Taiwan Oncology NHI Navigator",
    "source_name": "衛生福利部中央健康保險署－第九節 抗癌瘤藥物",
    "source_update": "115/7/23",
    "verified_on": "2026-08-11",
    "source_url": "https://www.nhi.gov.tw/ch/dl-55685-99c675b771ab4b2789c891bc8db447ce-1.pdf",
    "scope": "GI beta：胃癌、食道癌、大腸直腸癌、肝細胞癌、膽道癌、胰臟癌",
    "note": "V0.2：修正治療線別正規化；HCC 的 sorafenib/lenvatinib 均明確歸入 1L。正式申報仍應以健保署最新公告原文為準。",
    "version": "0.2"
  },
  "cancers": [
    {"id":"gastric","name":"胃癌 / GEJ","en":"Gastric / GEJ","icon":"胃","description":"胃腺癌與胃食道接合處腺癌"},
    {"id":"esophageal","name":"食道癌","en":"Esophageal","icon":"食","description":"目前 beta 先整理食道鱗狀細胞癌"},
    {"id":"colorectal","name":"大腸直腸癌","en":"Colorectal","icon":"腸","description":"mCRC、RAS / BRAF / MSI-dMMR 導向"},
    {"id":"hcc","name":"肝細胞癌","en":"HCC","icon":"肝","description":"晚期 HCC 一線與後線健保選項"},
    {"id":"biliary","name":"膽道癌","en":"Biliary tract","icon":"膽","description":"BTC / intrahepatic cholangiocarcinoma"},
    {"id":"pancreatic","name":"胰臟癌","en":"Pancreatic","icon":"胰","description":"轉移性胰臟癌與標靶例外情境"}
  ],
  "indications": []
};

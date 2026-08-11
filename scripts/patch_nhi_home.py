from pathlib import Path

NHI_CARD = """                    e('a', {href: './tools/nhi/index.html', target: '_blank', rel: 'noopener', className: toolButtonClass},
                        e('div', {className: 'font-semibold text-teal-800'}, '抗癌藥物健保給付 Navigator BETA'),
                        e('div', {className: 'text-xs text-gray-500 mt-1'}, '依癌種、治療線別與 biomarker 查詢健保抗癌藥物給付')
                    ),
"""

ANCHOR = """                    e('a', {href: './tools/index.html', target: '_blank', rel: 'noopener', className: toolButtonClass},
                        e('div', {className: 'font-semibold text-gray-900'}, '工具首頁'),
                        e('div', {className: 'text-xs text-gray-500 mt-1'}, '所有 standalone clinical tools')
                    )
"""

OLD_HINT = '提示：工具頁皆為 standalone clinical tools；目前包含 renal/BSA、腫瘤分期、CTCAE 副作用速查與 RECIST/TLS 計算。'
NEW_HINT = '提示：工具頁皆為 standalone clinical tools；目前包含 renal/BSA、腫瘤分期、CTCAE、RECIST/TLS 與抗癌藥物健保給付查詢。'


def patch(path: Path, required: bool = False) -> bool:
    if not path.exists():
        if required:
            raise RuntimeError(f'required homepage missing: {path}')
        return False
    text = path.read_text(encoding='utf-8')
    original = text
    if "./tools/nhi/index.html" not in text:
        if ANCHOR not in text:
            if required:
                raise RuntimeError(f'homepage tool anchor not found in {path}')
            print(f'skip {path}: different template / anchor not present')
            return False
        text = text.replace(ANCHOR, NHI_CARD + ANCHOR, 1)
    text = text.replace(OLD_HINT, NEW_HINT)
    if text != original:
        path.write_text(text, encoding='utf-8')
        return True
    return False


changed = []
if patch(Path('index.html'), required=True):
    changed.append('index.html')
if patch(Path('404.html'), required=False):
    changed.append('404.html')
print('patched:', ', '.join(changed) if changed else 'already current')

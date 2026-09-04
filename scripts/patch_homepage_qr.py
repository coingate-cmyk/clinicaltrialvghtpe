from pathlib import Path
from io import BytesIO
import base64
import qrcode
import qrcode.image.svg

INDEX = Path('index.html')
MARKER = 'homepage-qr-20260904'
TARGET_URL = 'https://coingate-cmyk.github.io/clinicaltrialvghtpe/'


def make_qr_data_uri():
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(TARGET_URL)
    qr.make(fit=True)
    img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    buf = BytesIO()
    img.save(buf)
    encoded = base64.b64encode(buf.getvalue()).decode('ascii')
    return 'data:image/svg+xml;base64,' + encoded


def main():
    html = INDEX.read_text(encoding='utf-8')
    if MARKER in html:
        print('Homepage QR already present.')
        return

    header_marker = "e('div', {className: 'bg-white shadow-lg mt-16 sticky top-0 z-50'},"
    header_pos = html.find(header_marker)
    if header_pos < 0:
        raise SystemExit('Cannot locate main sticky header')

    main_marker = "        e('div', {className: 'max-w-7xl mx-auto px-2 sm:px-4 py-4 sm:py-8'},"
    main_pos = html.find(main_marker, header_pos)
    if main_pos < 0:
        raise SystemExit('Cannot locate main content container after header')

    qr_src = make_qr_data_uri()
    block = f"""        // {MARKER}\n        e('div', {{className: 'max-w-7xl mx-auto px-2 sm:px-4 pt-4 sm:pt-5'}},\n            e('div', {{className: 'bg-white border border-blue-100 rounded-xl shadow-sm px-3 sm:px-4 py-3 flex items-center gap-3 sm:gap-4'}},\n                e('a', {{href: '{TARGET_URL}', target: '_blank', rel: 'noopener noreferrer', className: 'shrink-0 bg-white p-1.5 sm:p-2 rounded-lg border border-slate-200 hover:border-blue-300 transition-colors', title: '掃描或點擊開啟臨床試驗管理系統'}},\n                    e('img', {{src: '{qr_src}', alt: '臨床試驗管理系統 QR Code', className: 'w-24 h-24 sm:w-28 sm:h-28'}})\n                ),\n                e('div', {{className: 'min-w-0'}},\n                    e('div', {{className: 'text-sm sm:text-base font-bold text-slate-800'}}, '手機掃描開啟系統'),\n                    e('div', {{className: 'mt-1 text-xs sm:text-sm leading-relaxed text-slate-600'}}, '用手機相機掃描 QR Code，即可開啟臨床試驗管理系統。'),\n                    e('a', {{href: '{TARGET_URL}', target: '_blank', rel: 'noopener noreferrer', className: 'mt-2 inline-block text-[11px] sm:text-xs text-blue-700 hover:underline break-all'}}, 'coingate-cmyk.github.io/clinicaltrialvghtpe/')\n                )\n            )\n        ),\n"""
    html = html[:main_pos] + block + html[main_pos:]
    INDEX.write_text(html, encoding='utf-8')
    print('Homepage QR card added.')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Kerning proof: each pair without and with kerning, and Cyrillic set beside Latin and punctuation.

    kernsheet.py FONT OUT.html [--wght 400 900]
"""
import argparse
import html
from pathlib import Path

PAIRS = ['ГА', 'ТА', 'ЛА', 'ДА', 'Ту', 'Гу', 'Та', 'Го', 'Ґа', 'Ул', 'УА', 'ФА', 'ХО', 'ЬТ', 'ЪТ', 'ЬУ', 'Р.', 'Г.',
         'Г,', 'Т:', 'У.', '«Г»', '«Т»', '«У»', '(Г)', 'Г-', 'Г—', 'гл', 'гд', 'тл', 'ял', 'ьт', 'ъу', 'ку', 'кч',
         'ҚА', 'ҒА', 'ҮА', 'ҰА', 'ӘТ', 'TА', 'АT', 'VА', 'ГO', 'Ty']
LINES = ['ТОВ «ГРУПА ТАЙГА», р/р 2600 · ГРН. · Гуртом. Тут. Уява.',
         'Аванс: Товари «Рута» — 1 200,00 ₴; Улянa; «Ґрунт» — ТАК',
         'Latin → Кирилиця: Taxi «Таксі», Volta «Вольта», Yoga «Йога», AT «АТ»',
         'ЬТ ЪТ ЛЛ ДД АУА ГАГ ТАТ «ЛАТЕ»  гладь, тягти, льон, Українa, Київ',
         'Қазақстан Республикасы — ТӨЛЕМ: 12 500 ₸ · ҰЛТТЫҚ ҚОР']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('font')
    ap.add_argument('out')
    ap.add_argument('--wght', nargs='+', type=float, default=[400, 900])
    ap.add_argument('--title', default='Allo Cyrillic · kerning')
    a = ap.parse_args()
    e = html.escape
    parts = []
    for w in a.wght:
        st = f"font-family:'V'; font-variation-settings:'opsz' 14, 'wght' {w:g}, 'ROND' 50"
        cells = ''.join(f'<div class="p"><span style="{st}; font-kerning:none">{e(p)}</span>'
                        f'<span style="{st}">{e(p)}</span></div>' for p in PAIRS)
        lines = ''.join(f'<div class="l" style="{st}">{e(t)}</div>' for t in LINES)
        parts.append(f'<h2>wght {w:g} · each pair: without kerning, with</h2><div class="grid">{cells}</div>{lines}')
    Path(a.out).write_text(f'''<!doctype html><meta charset="utf-8"><title>{e(a.title)}</title><style>
@font-face {{ font-family: 'V'; src: url('{Path(a.font).resolve().as_uri()}'); }}
body {{ margin: 0; padding: 24px 32px; background: #fff; color: #111; font: 12px -apple-system, sans-serif; }}
h1 {{ font-size: 16px; margin: 0 0 8px; }} h2 {{ font-size: 12px; color: #888; font-weight: 500; margin: 18px 0 6px; }}
.grid {{ display: flex; flex-wrap: wrap; gap: 6px 22px; }}
.p {{ font-size: 46px; display: flex; gap: 12px; }} .p span:first-child {{ color: #bbb; }}
.l {{ font-size: 30px; margin: 6px 0; white-space: nowrap; }}
</style><h1>{e(a.title)}</h1>{"".join(parts)}''')


if __name__ == '__main__':
    main()

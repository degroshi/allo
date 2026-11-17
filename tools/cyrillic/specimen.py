#!/usr/bin/env python3
"""A specimen page for checking Allo's Cyrillic against its Latin.

    specimen.py OUT.html --font LABEL=PATH[@settings] ... [--title TEXT] [--note TEXT]

Each --font is one row set: a static font, or a variable font with CSS font-variation-settings after '@'
("AlloVariable.ttf@'wght' 900, 'ROND' 0, 'opsz' 32"). Render the page with a headless browser.
"""
import argparse
import html
from pathlib import Path

LATIN_UP = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
LATIN_LO = 'abcdefghijklmnopqrstuvwxyz'
CYR_UP = 'АБВГҐДЕЄЁЖЗИІЇЙКЛМНОПРСТУЎФХЦЧШЩЪЫЬЭЮЯ'
CYR_LO = 'абвгґдеєёжзиіїйклмнопрстуўфхцчшщъыьэюя'
KZ = 'ӘәҒғҚқҢңӨөҰұҮүҺһ'
DETAIL = ('HЖКЛДУЦЄҐҚҢ₾', 'nжклдуцєґқңу')
APP = ['Витрачено 12 611,40 ₴', 'Надійшло', 'Операції', 'Перевір перед імпортом',
       'Ґанок, їжак, єнот, ящірка', 'Қазақстан, Өскемен, Ұлытау, Әлем', '₸ ₾ ₴ € $ №']
LATIN_APP = ['Spent $12,611.40', 'Received', 'Transactions', 'Check before importing',
             'Porch, hedgehog, raccoon, lizard', 'Kazakhstan, Oskemen, Ulytau, World', '₸ ₾ ₴ € $ #']
PANGRAMS = [
    ('uk', 'Чуєш їх, доцю, га? Кумедна ж ти, прощайся без ґольфів!'),
    ('kk', 'Әсем Ғалия Қарағандыдан Өскеменге жаңа ұшақпен үш күнде келді, һәм қуанды.'),
    ('ru', 'Съешь же ещё этих мягких французских булок, да выпей чаю.'),
    ('be', 'У рудога вераб’я ў сховішчы пад фатэлем ляжаць нейкія гаючыя зёлкі.'),
    ('en', 'The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs.'),
]
PARA_UK = ('Перевір перед імпортом: банк надіслав 248 операцій за жовтень. Витрачено 12 611,40 ₴, '
           'надійшло 18 300,00 ₴. Найбільші витрати — продукти, транспорт і кав’ярні; '
           'щомісячні підписки зросли на 4%. «Ґанок» і «Їжак» — нові категорії.')
PARA_EN = ('Check before importing: the bank sent 248 transactions for October. Spent $12,611.40, '
           'received $18,300.00. The largest expenses were groceries, transport and cafés; '
           'monthly subscriptions grew by 4%. “Porch” and “Hedgehog” are new categories.')

CSS = '''
:root { --ink: #111; --mute: #8a8a8a; --rule: #e6e6e6; --bg: #fff; }
* { box-sizing: border-box; }
body { margin: 0; padding: 32px 40px 48px; background: var(--bg); color: var(--ink);
       font: 13px/1.4 -apple-system, BlinkMacSystemFont, sans-serif; }
h1 { font-size: 18px; margin: 0 0 4px; }
.note { color: var(--mute); margin: 0 0 24px; max-width: 1100px; }
section { border-top: 1px solid var(--rule); padding: 18px 0 8px; }
.tag { color: var(--mute); font-size: 11px; letter-spacing: .04em; text-transform: uppercase; margin-bottom: 8px; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
.s { white-space: nowrap; overflow: hidden; }
.w { display: flex; gap: 24px; align-items: baseline; }
.w .lab { width: 44px; color: var(--mute); font-size: 11px; flex: none; text-align: right; }
.para { max-width: 560px; }
'''


def font_face(i, label, path, settings):
    return f'@font-face {{ font-family: "S{i}"; src: url("{Path(path).resolve().as_uri()}"); }}'


def block(i, label, settings, sizes=(46, 28, 16)):
    st = f"font-family: 'S{i}', monospace; font-variation-settings: {html.escape(settings or 'normal')};"
    e = html.escape
    out = [f'<section><div class="tag">{e(label)}</div>']
    out.append(f'<div class="s" style="{st} font-size:150px; line-height:1.1">{e(DETAIL[0])}</div>')
    out.append(f'<div class="s" style="{st} font-size:150px; line-height:1.15; margin-bottom:8px">{e(DETAIL[1])}</div>')
    for t in (LATIN_UP, CYR_UP, LATIN_LO, CYR_LO + ' ' + KZ[1::2]):
        out.append(f'<div class="s" style="{st} font-size:{sizes[0]}px; line-height:1.15">{e(t)}</div>')
    out.append(f'<div class="pair" style="{st}; margin-top:12px">')
    out.append('<div>' + ''.join(f'<div class="s" style="font-size:{sizes[1]}px">{e(t)}</div>' for t in LATIN_APP) + '</div>')
    out.append('<div>' + ''.join(f'<div class="s" style="font-size:{sizes[1]}px">{e(t)}</div>' for t in APP) + '</div>')
    out.append('</div>')
    out.append(f'<div class="pair" style="{st}; margin-top:14px; font-size:{sizes[2]}px">'
               f'<div class="para">{e(PARA_EN)}</div><div class="para">{e(PARA_UK)}</div></div>')
    out.append('</section>')
    return '\n'.join(out)


def waterfall(i, label, settings):
    st = f"font-family: 'S{i}', monospace; font-variation-settings: {html.escape(settings or 'normal')};"
    e = html.escape
    out = [f'<section><div class="tag">{e(label)} · waterfall</div>']
    for px in (11, 12, 14, 16, 20, 28, 40):
        out.append(f'<div class="w"><span class="lab">{px}px</span><span class="s" style="{st} font-size:{px}px">'
                   f'{e(APP[0])} · {e(APP[1])} · {e(APP[2])} · {e(APP[3])} · Received · {e(APP[5])}</span></div>')
    out.append('<div style="margin-top:10px">')
    for lang, t in PANGRAMS:
        out.append(f'<div class="w"><span class="lab">{lang}</span><span class="s" style="{st} font-size:20px">{e(t)}</span></div>')
    out.append('</div></section>')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--font', action='append', required=True, help='LABEL=PATH[@settings]')
    ap.add_argument('--title', default='Allo Cyrillic')
    ap.add_argument('--note', default='')
    ap.add_argument('--waterfall', action='append', default=[], help='label of a font to show as a waterfall')
    args = ap.parse_args()
    fonts = []
    for f in args.font:
        label, rest = f.split('=', 1)
        path, _, settings = rest.partition('@')
        fonts.append((label, path, settings))
    faces = '\n'.join(font_face(i, *f) for i, f in enumerate(fonts))
    body = [f'<h1>{html.escape(args.title)}</h1><p class="note">{html.escape(args.note)}</p>']
    for i, (label, path, settings) in enumerate(fonts):
        body.append(block(i, label, settings))
    for i, (label, path, settings) in enumerate(fonts):
        if label in args.waterfall:
            body.append(waterfall(i, label, settings))
    Path(args.out).write_text(f'<!doctype html><meta charset="utf-8"><title>{html.escape(args.title)}</title>'
                              f'<style>{faces}\n{CSS}</style><body>{"".join(body)}</body>')


if __name__ == '__main__':
    main()

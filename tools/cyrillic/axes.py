#!/usr/bin/env python3
"""A sheet of the variable font across its axes, Latin beside Cyrillic, for checking that the Cyrillic
keeps the Latin's colour, rhythm and rounding everywhere and interpolates without kinks.

    axes.py FONT OUT.html [--opsz 14 32] [--wght 100 400 580 900] [--rond 0 50 100] [--text ...]
"""
import argparse
import html
from pathlib import Path

TEXT = ['HОНПЖКЛДУЦЄҐҚҢЯ', 'nонпжклдуцєґқңя', 'Витрачено 12 611,40 ₴ · Spent $12,611.40',
        'Ґанок, їжак, єнот · Қазақстан, Өскемен, Ұлытау, Әлем']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('font')
    ap.add_argument('out')
    ap.add_argument('--opsz', nargs='+', type=float, default=[14])
    ap.add_argument('--wght', nargs='+', type=float, default=[100, 400, 580, 900])
    ap.add_argument('--rond', nargs='+', type=float, default=[0, 50, 100])
    ap.add_argument('--text', nargs='+', default=TEXT)
    ap.add_argument('--size', type=float, default=34)
    ap.add_argument('--title', default='Allo Cyrillic across the axes')
    a = ap.parse_args()
    e = html.escape
    rows = []
    for o in a.opsz:
        for w in a.wght:
            for r in a.rond:
                st = f"font-family:'V'; font-variation-settings:'opsz' {o:g}, 'wght' {w:g}, 'ROND' {r:g}; font-optical-sizing:none"
                cells = ''.join(f'<div class="t" style="{st}; font-size:{a.size * (1 if i < 2 else 0.62):.0f}px">{e(t)}</div>'
                                for i, t in enumerate(a.text))
                rows.append(f'<div class="row"><div class="lab">opsz {o:g}<br>wght {w:g}<br>ROND {r:g}</div><div>{cells}</div></div>')
    page = f'''<!doctype html><meta charset="utf-8"><title>{e(a.title)}</title><style>
@font-face {{ font-family: 'V'; src: url('{Path(a.font).resolve().as_uri()}'); }}
body {{ margin: 0; padding: 24px 32px; background: #fff; color: #111; font: 12px -apple-system, sans-serif; }}
h1 {{ font-size: 16px; margin: 0 0 12px; }}
.row {{ display: flex; gap: 20px; border-top: 1px solid #eee; padding: 6px 0; }}
.lab {{ width: 70px; flex: none; color: #888; font-size: 11px; line-height: 1.3; padding-top: 6px; }}
.t {{ white-space: nowrap; line-height: 1.2; }}
</style><h1>{e(a.title)}</h1>{''.join(rows)}'''
    Path(a.out).write_text(page)


if __name__ == '__main__':
    main()

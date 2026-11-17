#!/usr/bin/env python3
"""Check rounding.py against Allo's own Latin: take a glyph's ROND 0 outline, take its rounding off,
round it again with rounding.py for ROND 0, 50 and 100, and compare with Allo's masters point by point.

    validate_rounding.py OPSZ WGHT [GLYPH ...]

Prints the largest distance (units) per ROND for every glyph that misses by more than half a unit.
"""
import math
import sys
from pathlib import Path

import ufoLib2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from allo import radius, stem, ufo_path  # noqa: E402
from rounding import plan_glyph, round_glyph, straighten_spurs, to_cubic, unround  # noqa: E402

LETTERS = ('A B C D E F G H I J K L M N O P Q R S T U V W X Y Z a b c d f g h k l m n o p q r t u v w x y z '
           'zero two three four five six seven eight nine germandbls thorn Thorn AE OE oe Eth Lslash Tbar '
           'dcroat hbar kgreenlandic idotless I.1 l.ss02 a.1').split()


def points(font, name):
    return [[(p.x, p.y, p.type) for p in c.points] for c in font[name].contours]


def best_error(mine, ref):
    """Largest point distance, over the start point that lines the contours up best (None: incompatible)."""
    if len(mine) != len(ref):
        return None
    best = None
    for r in range(len(ref)):
        rr = ref[r:] + ref[:r]
        if [p[2] is None for p in rr] != [p[2] is None for p in mine]:
            continue
        e = max(math.dist(p[:2], q[:2]) for p, q in zip(mine, rr))
        best = e if best is None else min(best, e)
    return best


def main():
    opsz, wght = int(sys.argv[1]), int(sys.argv[2])
    names = sys.argv[3:] or LETTERS
    fonts = {r: ufoLib2.Font.open(ufo_path(opsz, wght, r)) for r in (0, 50, 100)}
    R = radius(fonts[0], fonts[50])
    st = stem(fonts[0])
    print(f'opsz {opsz} wght {wght}: R {R:.3f}, stem {st:.1f}')
    exact = 0
    for name in names:
        if name not in fonts[0] or not fonts[0][name].contours or fonts[0][name].components:
            continue
        sharp = [straighten_spurs(to_cubic(unround(c)), 0.3 * st) for c in points(fonts[0], name)]
        plans = plan_glyph(sharp, st)
        row = []
        for r in (0, 50, 100):
            mine = round_glyph(sharp, plans, R, r, st)
            ref = [to_cubic(c) for c in points(fonts[r], name)]
            errs = [best_error(a, b) for a, b in zip(mine, ref)] if len(mine) == len(ref) else [None]
            row.append(None if None in errs else max(errs))
        if all(e is not None and e <= 0.5 for e in row):
            exact += 1
        else:
            print(f'  {name:14} ' + '  '.join(f'R{r}: {"n/a" if e is None else f"{e:.1f}"}' for r, e in zip((0, 50, 100), row)))
    print(f'{exact} glyphs within half a unit')


if __name__ == '__main__':
    main()

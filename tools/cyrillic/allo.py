"""Allo's masters: where they are, their radius R and stems."""
import math
from pathlib import Path

from fontTools.designspaceLib import DesignSpaceDocument

ROOT = Path(__file__).resolve().parents[2]
DS = ROOT / 'sources/Allo.designspace'


def masters():
    """[(opsz, wght, rond, path, layer)] for every source in the designspace (layer None = default)."""
    ds = DesignSpaceDocument.fromfile(DS)
    out = []
    for s in ds.sources:
        loc = s.location
        out.append((int(loc['Optical size']), int(loc['Weight']), int(loc['Roundness']), Path(s.path), s.layerName))
    return out


def ufo_path(opsz, wght, rond):
    return ROOT / f'sources/masters/Allo-opsz{opsz}-wght{wght}-ROND{rond}.ufo'


def radius(r0, r50):
    """R of a master pair: how far ROND 50 moves the fillet ends of H's bottom-left corner."""
    a = [(p.x, p.y) for p in r0['H'].contours[0].points]
    b = [(p.x, p.y) for p in r50['H'].contours[0].points]
    corner = (a[0][0], a[1][1])  # the corner (170, 0) at 14/400: x of the first off-curve, y of the second
    return math.dist(corner, b[2])


def stem(font, glyph='H'):
    """H's stem in a ROND 0 master (its fillets taken off first)."""
    from rounding import unround
    c = unround([(p.x, p.y, p.type) for p in font[glyph].contours[0].points])
    xs = sorted({round(x) for x, y, t in c if t is not None})
    return xs[1] - xs[0]

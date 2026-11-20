#!/usr/bin/env python3
"""Add Cyrillic to Allo's masters.

For every master (opsz, wght, ROND) the Cyrillic glyphs are made one of these ways:

* ref     a component of Allo's own glyph where the letter is the Latin one (А = A, і = i, Ё = Edieresis),
          plus marks placed on anchors (Й = И + breve);
* mirror  / rotate: Allo's glyph turned (И = mirrored N, Я = mirrored R, ә = rotated e), rounding and all;
* inter   Inter's drawing at a weight calibrated to Allo's stems, overlaps removed, sidebearings moved by
          as much as Allo moved its Latin reference letters, then rounded with Allo's own rules
          (rounding.py) for the master's ROND;
* custom  as inter, with Allo's own changes to the Latin carried over (У gets y's straight tail).

The outlines are sharp first; every ROND master is rounded from the same sharp outline and the same
corner plan, so all masters interpolate.

    build_cyrillic.py [--masters opsz,wght,rond ...] [--out DIR]
"""
import argparse
import copy
import math
import re
import shutil
import sys
from pathlib import Path

import ufoLib2
from ufoLib2.objects import Anchor, Component, Contour, Glyph, Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
from allo import ROOT, masters as designspace_masters, radius  # noqa: E402
import drawn  # noqa: E402
import kerning  # noqa: E402
from inter import Inter, reverse_contour  # noqa: E402
from outline import align, find_crotches, point_crotches, union  # noqa: E402
from rounding import (ink_sign, plan_glyph, round_glyph, straighten_spurs, to_cubic, unround,  # noqa: E402
                      line_intersection, sub, unit)

REF = (14, 400)  # the master whose geometry decides corner plans and contour order

# ------------------------------------------------------------------------------------------ recipes
# name: (unicode, kind, args, options)   options: sb=(left ref, right ref) for spacing, union=bool
R = {}


def ref(name, uni, base, marks=(), **kw):
    R[name] = dict(uni=uni, kind='ref', base=base, marks=list(marks), **kw)


def inter(name, uni, source, sb, **kw):
    R[name] = dict(uni=uni, kind='inter', source=source, sb=sb, **kw)


def turned(name, uni, kind, base, **kw):
    R[name] = dict(uni=uni, kind=kind, base=base, **kw)


def bar(name, uni, base, source, mirror=False, **kw):
    """Allo's glyph with a bar from Inter's drawing of the letter (Є = C + bar, Ө = O + bar)."""
    R[name] = dict(uni=uni, kind='bar', base=base, source=source, mirror=mirror, **kw)


# capitals
ref('uni0410', 0x0410, 'A')
inter('uni0411', 0x0411, 'afii10018', ('H', 'B'))
ref('uni0412', 0x0412, 'B')
inter('uni0413', 0x0413, 'Ge-cy', ('H', 'T'))
inter('uni0414', 0x0414, 'afii10021', ('H', 'H'))
ref('uni0415', 0x0415, 'E')
inter('uni0416', 0x0416, 'Zhe-cy', ('X', 'X'))
ref('uni0417', 0x0417, 'three')
turned('uni0418', 0x0418, 'mirror', 'N')
ref('uni0419', 0x0419, 'uni0418', [('brevecomb', 'top')])
inter('uni041A', 0x041A, 'Kacyr', ('H', 'K'))
inter('uni041B', 0x041B, 'afii10029', ('A', 'H'))
ref('uni041C', 0x041C, 'M')
ref('uni041D', 0x041D, 'H')
ref('uni041E', 0x041E, 'O')
inter('uni041F', 0x041F, 'Pi', ('H', 'H'))
ref('uni0420', 0x0420, 'P')
ref('uni0421', 0x0421, 'C')
ref('uni0422', 0x0422, 'T')
R['uni0423'] = dict(uni=0x0423, kind='custom', source='U-cy', sb=('Y', 'Y'), make='straight_u')
inter('uni0424', 0x0424, 'afii10038', ('O', 'O'), union=False)
ref('uni0425', 0x0425, 'X')
inter('uni0426', 0x0426, 'afii10040', ('H', 'H'))
inter('uni0427', 0x0427, 'Che-cy', ('H', 'H'))
inter('uni0428', 0x0428, 'Sha-cy', ('H', 'H'))
inter('uni0429', 0x0429, 'Shcha-cy', ('H', 'H'))
inter('uni042A', 0x042A, 'afii10044', ('T', 'B'))
inter('uni042C', 0x042C, 'Softsign-cy', ('H', 'B'))
R['uni042B'] = dict(uni=0x042B, kind='pair', parts=('uni042C', 'I'), source='afii10045')
bar('uni042D', 0x042D, 'C', 'afii10047', mirror=True)
R['uni042E'] = dict(uni=0x042E, kind='yu', parts=('I', 'O'), source='afii10048')
turned('uni042F', 0x042F, 'mirror', 'R')
ref('uni0401', 0x0401, 'Edieresis')
bar('uni0404', 0x0404, 'C', 'afii10053')
ref('uni0405', 0x0405, 'S')
ref('uni0406', 0x0406, 'I')
ref('uni0407', 0x0407, 'Idieresis')
ref('uni0408', 0x0408, 'J')
ref('uni040E', 0x040E, 'uni0423', [('brevecomb', 'top')])
inter('uni0490', 0x0490, 'afii10050', ('H', 'T'), make='upturn')
ref('uni0492', 0x0492, 'uni0413', [('crossbar.uc', 'stroke')])
inter('uni049A', 0x049A, 'Kadescendercyrillic', ('H', 'K'))
inter('uni04A2', 0x04A2, 'Endescendercyrillic', ('H', 'H'))
ref('uni04AE', 0x04AE, 'Y')
ref('uni04B0', 0x04B0, 'Y', [('crossbar.uc', 'stroke')])
turned('uni04BA', 0x04BA, 'rotate', 'uni0427')
inter('uni04D8', 0x04D8, 'Schwacyrillic', ('O', 'O'))
bar('uni04E8', 0x04E8, 'O', 'afii10147')
# Serbian and Macedonian
ref('uni0400', 0x0400, 'Egrave')
inter('uni0402', 0x0402, 'afii10051', ('T', 'B'), make='join')
ref('uni0403', 0x0403, 'uni0413', [('acutecomb', 'top')])
inter('uni0409', 0x0409, 'afii10058', ('A', 'B'))
inter('uni040A', 0x040A, 'afii10059', ('H', 'B'))
inter('uni040B', 0x040B, 'Tshe-cy', ('T', 'H'))
ref('uni040C', 0x040C, 'uni041A', [('acutecomb', 'top')])
ref('uni040D', 0x040D, 'uni0418', [('gravecomb', 'top')])
inter('uni040F', 0x040F, 'afii10145', ('H', 'H'))
# lowercase
ref('uni0430', 0x0430, 'a')
inter('uni0431', 0x0431, 'becyrillic', ('o', 'o'), bend_cap=True, make='flag')  # its thin flag at Black
inter('uni0432', 0x0432, 'vecyrillic', ('n', 's'))
inter('uni0433', 0x0433, 'ge-cy', ('n', 'r'))
inter('uni0434', 0x0434, 'decyrillic', ('n', 'n'))
ref('uni0435', 0x0435, 'e')
inter('uni0436', 0x0436, 'zhecyrillic', ('x', 'x'))
inter('uni0437', 0x0437, 'zecyrillic', ('o', 'o'))
inter('uni0438', 0x0438, 'iicyrillic', ('n', 'n'))
ref('uni0439', 0x0439, 'uni0438', [('brevecomb', 'top')])
inter('uni043A', 0x043A, 'kacyrillic', ('n', 'k'))
inter('uni043B', 0x043B, 'elcyrillic', ('n', 'n'))
inter('uni043C', 0x043C, 'emcyrillic', ('n', 'n'))
inter('uni043D', 0x043D, 'encyrillic', ('n', 'n'))
ref('uni043E', 0x043E, 'o')
inter('uni043F', 0x043F, 'pecyrillic', ('n', 'n'))
ref('uni0440', 0x0440, 'p')
ref('uni0441', 0x0441, 'c')
inter('uni0442', 0x0442, 'tecyrillic', ('T', 'T'))
ref('uni0443', 0x0443, 'y')
inter('uni0444', 0x0444, 'efcyrillic', ('o', 'o'), union=False, make=('ascender', 'descender'))
ref('uni0445', 0x0445, 'x')
inter('uni0446', 0x0446, 'tsecyrillic', ('n', 'n'))
inter('uni0447', 0x0447, 'checyrillic', ('n', 'n'))
inter('uni0448', 0x0448, 'shacyrillic', ('n', 'n'))
inter('uni0449', 0x0449, 'shchacyrillic', ('n', 'n'))
inter('uni044A', 0x044A, 'hardsigncyrillic', ('T', 'o'))
inter('uni044C', 0x044C, 'softsigncyrillic', ('n', 'o'))
R['uni044B'] = dict(uni=0x044B, kind='pair', parts=('uni044C', 'idotless'), source='yericyrillic')
bar('uni044D', 0x044D, 'c', 'ereversedcyrillic', mirror=True)
R['uni044E'] = dict(uni=0x044E, kind='yu', parts=('idotless', 'o'), source='iucyrillic')
inter('uni044F', 0x044F, 'iacyrillic', ('o', 'n'), union=False)
ref('uni0451', 0x0451, 'edieresis')
bar('uni0454', 0x0454, 'c', 'ecyrillic')
ref('uni0455', 0x0455, 's')
ref('uni0456', 0x0456, 'i')
ref('uni0457', 0x0457, 'idieresis')
ref('uni0458', 0x0458, 'j')
ref('uni045E', 0x045E, 'y', [('brevecomb', 'top')])
inter('uni0491', 0x0491, 'gheupturncyrillic', ('n', 'r'))
ref('uni0493', 0x0493, 'uni0433', [('crossbar', 'stroke')])
inter('uni049B', 0x049B, 'kadescendercyrillic', ('n', 'k'))
inter('uni04A3', 0x04A3, 'endescendercyrillic', ('n', 'n'))
inter('uni04AF', 0x04AF, 'ustraightcyrillic', ('v', 'v'), make='descender')
ref('uni04B1', 0x04B1, 'uni04AF', [('crossbar', 'stroke')])
ref('uni04BB', 0x04BB, 'h')
turned('uni04D9', 0x04D9, 'rotate', 'e', lower=True)
bar('uni04E9', 0x04E9, 'o', 'obarredcyrillic')
# Serbian and Macedonian
ref('uni0450', 0x0450, 'egrave')
inter('uni0452', 0x0452, 'djecyrillic', ('hbar', 'hbar'), make=('join', 'ascender'))
ref('uni0453', 0x0453, 'uni0433', [('acutecomb', 'top')])
inter('uni0459', 0x0459, 'ljecyrillic', ('n', 'o'), make='lje')
inter('uni045A', 0x045A, 'njecyrillic', ('n', 'o'))
ref('uni045B', 0x045B, 'hbar')
ref('uni045C', 0x045C, 'uni043A', [('acutecomb', 'top')])
ref('uni045D', 0x045D, 'uni0438', [('gravecomb', 'top')])
inter('uni045F', 0x045F, 'dzhecyrillic', ('u', 'u'))
# currency
inter('tenge', 0x20B8, 'tenge', ('T', 'T'))
inter('lari', 0x20BE, 'lari', ('O', 'O'))
# Degroshi's extras (branch degroshi, not in the Cyrillic PR): ₮ for USDT, Σ for «ΣНакл»
inter('tugrik', 0x20AE, 'tugrik', ('T', 'T'))
inter('Sigma', 0x03A3, 'Sigma', ('E', 'E'))
# Degroshi's currency signs: Inter's drawings, and ֏ ৳ ៛, which Inter lacks, built from Inter's parts (drawn.py)
inter('manat', 0x20BC, 'manat', ('n', 'n'), make='plumb')
bar('cedi', 0x20B5, 'C', 'cedi')
bar('coloncurrency', 0x20A1, 'C', 'coloncurrency')
bar('guarani', 0x20B2, 'G', 'guarani')
inter('kip', 0x20AD, 'kip', ('K', 'K'), union=False)
R['rupee'] = dict(uni=0x20A8, kind='pair', parts=('R', 's'), source='rupee', inter_parts=('R', 's'))
inter('Xi', 0x039E, 'Xi', ('E', 'E'))
inter('dram', 0x058F, drawn.dram, ('U', 'hryvnia'))
inter('taka', 0x09F3, drawn.taka, ('hryvnia', 'hryvnia'), make='unflat', bend_cap=True)
inter('riel', 0x17DB, drawn.riel, ('J', 'o'), bend_cap=True)
# alternates
ref('uni0406.1', None, 'I.1')
ref('uni0407.1', None, 'Idieresis.1')
ref('uni0430.1', None, 'a.1')

ORDER = list(R)
POSTSCRIPT = {'tenge': 'uni20B8', 'lari': 'uni20BE', 'tugrik': 'uni20AE', 'manat': 'uni20BC', 'cedi': 'uni20B5',
              'coloncurrency': 'colonmonetary', 'guarani': 'uni20B2', 'kip': 'uni20AD', 'rupee': 'uni20A8',
              'dram': 'uni058F', 'taka': 'uni09F3', 'riel': 'uni17DB'}


# ------------------------------------------------------------------------------------- geometry

def bbox(contours):
    xs = [p[0] for c in contours for p in c]
    ys = [p[1] for c in contours for p in c]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)


def shift(contours, dx, dy=0):
    return [[(x + dx, y + dy, t) for x, y, t in c] for c in contours]


def mirror(contours, width):
    return [reverse_contour([(width - x, y, t) for x, y, t in c]) for c in contours]


def rotate(contours, width, height):
    return [[(width - x, height - y, t) for x, y, t in c] for c in contours]


def ufo_glyph_contours(font, name, decompose=True):
    g = font[name]
    out = [[(p.x, p.y, p.type) for p in c.points] for c in g.contours]
    if decompose:
        for comp in g.components:
            xx, xy, yx, yy, dx, dy = comp.transformation
            for c in ufo_glyph_contours(font, comp.baseGlyph):
                moved = [(xx * x + yx * y + dx, xy * x + yy * y + dy, t) for x, y, t in c]
                if xx * yy - xy * yx < 0:
                    moved = reverse_contour(moved)
                out.append(moved)
    return out


def stem_at(contours, y, x_from=None):
    """Width of the first dark run crossed by the horizontal line at y (polygon approximation)."""
    from fontTools.pens.recordingPen import RecordingPen  # noqa: F401
    xs = []
    for c in to_cubic_all(contours):
        pts = sample(c)
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            if (y1 - y) * (y2 - y) < 0:
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    xs.sort()
    if x_from is not None:
        xs = [x for x in xs if x >= x_from]
    return xs[1] - xs[0] if len(xs) > 1 else 0


def to_cubic_all(contours):
    return [to_cubic(c) for c in contours]


def sample(contour, n=12):
    from rounding import segments, cubic_point
    segs, _ = segments(contour)
    pts = []
    for kind, p in segs:
        if kind == 'curve':
            for k in range(n):
                pts.append(cubic_point(p, k / n))
        else:
            pts.append(p[0])
    return pts


# ---------------------------------------------------------------------------------------- masters

class Master:
    """One (opsz, wght) of Allo: its ROND 0 font (sharp reference) and its R, stems and Inter location."""

    def __init__(self, inter, opsz, wght, fonts, sparse=None):
        self.inter, self.opsz, self.wght = inter, opsz, wght
        self.fonts = fonts  # {rond: ufoLib2.Font} for ROND 0, 50, 100
        self.sparse = sparse or {}  # {rond: layer name in the ROND 50 font} (ROND 10 and 30 at heavy weights)
        self.R = radius(fonts[0], fonts[50])
        self.xheight = fonts[0].info.xHeight
        self.cap = fonts[0].info.capHeight
        self.stem = self.allo_stem()
        self.loc = {'opsz': min(max(opsz, 14), 32), 'wght': self.calibrate()}
        self._delta = {}

    def source(self, r):
        """Where this master's glyphs at ROND r live: a font, or a sparse layer of the ROND 50 font."""
        if r in self.fonts:
            return self.fonts[r]
        return self.fonts[50].layers[self.sparse[r]]

    def sharp(self, name):
        """Allo's glyph without its rounding (ROND 0's fillets collapsed, spurs as lines)."""
        f = self.fonts[0]
        return [straighten_spurs(to_cubic(unround(c)), 0.3 * self.stem) for c in ufo_glyph_contours(f, name)]

    def allo_stem(self):
        f = self.fonts[0]
        return (stem_at(ufo_glyph_contours(f, 'H'), self.cap / 4) + stem_at(ufo_glyph_contours(f, 'n'), self.xheight / 2)) / 2

    def inter_stem(self, wght):
        loc = {'opsz': min(max(self.opsz, 14), 32), 'wght': wght}
        h = stem_at(self.inter.decomposed_at('H', loc)['contours'], self.cap / 4)
        n = stem_at(self.inter.decomposed_at('n', loc)['contours'], self.xheight / 2)
        return (h + n) / 2

    def calibrate(self):
        """Inter's weight whose H and n stems match this master's."""
        lo, hi = max(100, self.wght - 60), min(900, self.wght + 60)
        target = self.stem
        if self.inter_stem(lo) >= target:
            return lo
        if self.inter_stem(hi) <= target:
            return hi
        for _ in range(30):
            mid = (lo + hi) / 2
            if self.inter_stem(mid) < target:
                lo = mid
            else:
                hi = mid
        return round((lo + hi) / 2, 3)

    def delta(self, ref):
        """(dLSB, dRSB): how far Allo moved this glyph's sides from Inter's."""
        if ref not in self._delta:
            f = self.fonts[0]
            a = ufo_glyph_contours(f, ref)
            ig = self.inter.decomposed_at(ref, self.loc)
            ax0, _, ax1, _ = bbox(a)
            ix0, _, ix1, _ = bbox(ig['contours'])
            self._delta[ref] = (ax0 - ix0, (f[ref].width - ax1) - (ig['width'] - ix1))
        return self._delta[ref]

    def inter_parts(self, source):
        g = source(self.inter, self.loc) if callable(source) else self.inter.decomposed_at(source, self.loc)
        return [to_cubic(c) for c in g['contours']], g['width'], dict(g['anchors'])

    def heights(self):
        """Allo's ascenders are 50 units taller than Inter's and its descenders 28 shorter (h, p):
        ((Inter's ascender, Allo's), (Inter's descender, Allo's)) at this master."""
        if not hasattr(self, '_heights'):
            out = []
            for name, k in (('h', 3), ('p', 1)):
                i = bbox(self.inter.decomposed_at(name, self.loc)['contours'])[k]
                a = bbox(ufo_glyph_contours(self.fonts[0], name))[k]
                out.append((i, a))
            self._heights = tuple(out)
        return self._heights


# ------------------------------------------------------------------------------------- make sharp

def straight_u(m, contours, width):
    """Inter's У with Allo's y tail: the right arm runs straight on to the baseline, as wide as at
    the top, and ends flat (Allo's y does the same below the baseline)."""
    (c,) = contours
    P = [p for p in c]
    on = [(i, p) for i, p in enumerate(P) if p[2] is not None]
    # Inter's points (see the notes): 4 arm start above the hook, 5 top right outer, 6 top right inner,
    # 16 top left outer, 17 the left arm's outer end at the tail
    def pt(k):
        return P[k][:2]
    p4, p5, p6, p16, p17 = pt(4), pt(5), pt(6), pt(16), pt(17)
    d = unit(sub(p5, p4))
    b2 = line_intersection(p4, d, (0, 0), (1, 0))
    b1 = (b2[0] - (p5[0] - p6[0]), 0.0)
    j = line_intersection(p16, unit(sub(p17, p16)), b1, d)
    keep = P[5:17]  # top right outer ... top left outer, with the crotch between
    new = [(b1[0], b1[1], 'line'), (b2[0], b2[1], 'line')] + keep + [(j[0], j[1], 'line')]
    # the first kept point (5) now arrives by a line from b2
    new[2] = (new[2][0], new[2][1], 'line')
    return [new], width


def upturn(m, contours, width):
    """Ґ: Inter's upturn stands on the end of Г's bar; at some masters Inter leaves the bar a few
    units past it. Here its outer side and foot are flush with the bar's end and underside."""
    up = min(contours, key=len)
    rest = [c for c in contours if c is not up]
    x0, y0, x1, y1 = bbox([up])
    # the bar: the topmost horizontal run of the rest, reaching furthest right
    bx1 = max(p[0] for c in rest for p in c)
    under = min(p[1] for c in rest for p in c if abs(p[0] - bx1) < 1)
    fixed = [((bx1 if abs(x - x1) < abs(x - x0) else x), (under if abs(y - y0) < abs(y - y1) else y), t)
             for x, y, t in up]
    return rest + [fixed], width


def stem_edges(contour):
    """The vertical line edges of a contour: [(x, y0, y1)]."""
    on = [p for p in contour if p[2] is not None]
    out = []
    for (x0, y0, t0), (x1, y1, t1) in zip(on, on[1:] + on[:1]):
        if t1 == 'line' and abs(x0 - x1) < 0.01 and abs(y0 - y1) > 50:
            out.append((x0, min(y0, y1), max(y0, y1)))
    return out


def join(m, contours, width, tol=6):
    """Parts laid on a stem (Ђ's hook on T, ђ's hook on ћ's leg) as Inter draws them stop a few units
    short of the stem's edge at some weights and not at others, which would give the joined outline a
    step there at some masters only. Each part's sides within `tol` of an edge of the first contour
    (the letter the part is laid on) are moved onto it, off-curve points with them."""
    edges = stem_edges(contours[0])
    out = [contours[0]]
    for c in contours[1:]:
        moves = {}
        for x, y, t in c:
            if t is None:
                continue
            for ex, y0, y1 in edges:
                if 0 < abs(x - ex) <= tol and y0 - tol <= y <= y1 + tol:
                    moves[x] = ex
        out.append(unflatten([(moves.get(x, x), y, t) for x, y, t in c]))
    return out, width


def unflatten(c):
    """A curve drawn dead straight at one master (the end of ђ's hook at Thin) comes out of overlap
    removal as a line, where the other masters keep a curve. Its handles move 1 unit off the line,
    so it stays a curve."""
    n = len(c)
    out = list(c)
    for i in range(n):
        if c[i][2] != 'curve':
            continue
        h1, h2, p0 = c[i - 1], c[i - 2], c[i - 3]
        if h1[2] is not None or h2[2] is not None or p0[2] is None:
            continue
        p1 = c[i]
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        length = math.hypot(dx, dy)
        if length < 1:
            continue
        off = [abs((h[0] - p0[0]) * dy - (h[1] - p0[1]) * dx) / length for h in (h1, h2)]
        if max(off) < 0.5:
            nx, ny = -dy / length, dx / length
            for k in (i - 1, i - 2):
                x, y, t = out[k]
                out[k] = (x + nx, y + ny, t)
    return out


def lje(m, contours, width):
    """љ: Inter sets ь beside л, their stems overlapping by a different amount at each weight (at Thin
    not at all). Here ь's stem is laid on л's right stem, one stem as in њ and Љ, and the letter
    narrows by as much."""
    el, *soft = contours
    l_edges = sorted(e[0] for e in stem_edges(el) if e[1] < 1)  # л's stem edges standing on the baseline
    s_edges = sorted(e[0] for c in soft for e in stem_edges(c) if e[1] < 1)
    dx = l_edges[-2] - s_edges[0]  # ь's stem, left side on л's right stem's left side
    soft = shift(soft, dx)
    contours, width = join(m, [el] + soft, width + dx, tol=3)
    return contours, width


def ascender(m, contours, width):
    """Stems that reach Inter's ascender (ђ, ф) reach Allo's, as Allo's b d h do."""
    (i, a), _ = m.heights()
    return [[(x, y + (a - i) if abs(y - i) < 1 else y, t) for x, y, t in c] for c in contours], width


def descender(m, contours, width):
    """Stems that reach Inter's descender (ф, ү) stop at Allo's, as Allo's p and y do."""
    _, (i, a) = m.heights()
    return [[(x, y + (a - i) if abs(y - i) < 1 else y, t) for x, y, t in c] for c in contours], width


def flag(m, contours, width):
    """б: its flag reaches Allo's ascender, as b does. The flag moves up whole, so its stroke keeps its
    thickness, and the stroke that rises to it from the bowl's top stretches to meet it."""
    (i, a), _ = m.heights()
    # Inter's outer contour, on-curve points: bottom, right, bowl top, the join (2), the flag's
    # underside, the terminal (2, at the ascender), the flag's top, the left side (2)
    on = [p for p in max(contours, key=len) if p[2] is not None]
    assert len(on) == 11 and abs(on[6][1] - i) < 1 and abs(on[7][1] - i) < 1, 'not Inter\'s б'
    top_bowl, lo_flag = on[2][1], on[5][1]
    def lift(y):
        return y + (a - i) * min(max((y - top_bowl) / (lo_flag - top_bowl), 0), 1)
    return [[(x, lift(y), t) for x, y, t in c] for c in contours], width


def plumb(m, contours, width):
    """Lines within 2 units of vertical made vertical (Inter's ₼ leans its inner right edge 1 unit)."""
    out = []
    for c in contours:
        c = list(c)
        for i, (x, y, t) in enumerate(c):
            if t != 'line':
                continue
            px, py, pt = c[i - 1]
            if pt is not None and 0 < abs(x - px) <= 2 and abs(y - py) > 50:
                c[i] = (px, y, t)
        out.append(c)
    return out, width


def unflat(m, contours, width):
    """unflatten on every contour (f's flat-ended hook at opsz 32, in ৳)."""
    return [unflatten(c) for c in contours], width


MAKERS = {'straight_u': straight_u, 'upturn': upturn, 'join': join, 'lje': lje,
          'ascender': ascender, 'descender': descender, 'flag': flag, 'unflat': unflat, 'plumb': plumb}


def sharp_inter(m, spec):
    contours, width, anchors = m.inter_parts(spec['source'])
    make = spec.get('make') or ()
    for k in ([make] if isinstance(make, str) else make):
        contours, width = MAKERS[k](m, contours, width)
    if spec.get('union', True) and len(contours) > 1:
        contours = union(contours)
    dl, _ = m.delta(spec['sb'][0])
    _, dr = m.delta(spec['sb'][1])
    contours = shift(contours, dl)
    anchors = {k: (round(x + dl), round(y)) for k, (x, y) in anchors.items()}
    return contours, round(width + dl + dr), anchors


def grid(contours):
    """Sharp outlines on whole units, as Allo's own (only its fillets leave the grid)."""
    return [[(round(x), round(y), t) for x, y, t in c] for c in contours]


# ------------------------------------------------------------------------------------------ build

def to_glyph(name, spec, contours, width, anchors, components=(), overlap=False):
    g = Glyph(name)
    if overlap or spec.get('union') is False:
        g.lib['public.truetype.overlap'] = True  # contours overlap: rasterisers should know
    g.width = round(width, 3) if width % 1 else int(width)
    if spec.get('uni'):
        g.unicodes = [spec['uni']]
    for c in contours:
        pts = [Point(x, y, t if t else None) for x, y, t in c]
        g.contours.append(Contour(points=pts))
    for base, (dx, dy) in components:
        g.components.append(Component(base, (1, 0, 0, 1, dx, dy)))
    for k, (x, y) in sorted(anchors.items()):
        g.anchors.append(Anchor(x, y, k))
    return g


def inside(contours, pt):
    from fontTools.pens.pointInsidePen import PointInsidePen
    from fontTools.pens.pointPen import PointToSegmentPen

    class G:
        def drawPoints(self, pen):
            for c in contours:
                pen.beginPath()
                for x, y, t in c:
                    pen.addPoint((x, y), t)
                pen.endPath()
    pen = PointInsidePen(None, pt)
    G().drawPoints(PointToSegmentPen(pen))
    return pen.getResult()


def hide(plans, contours, ink):
    """No fillets on the corners of a part that lie inside the letter it is laid on (a bar's ends in a
    stem or bowl): rounded, they would show as nicks where the bar leaves the stroke."""
    from rounding import segments
    for plan, c in zip(plans, contours):
        segs, _ = segments(to_cubic(c))
        for i, (kind, pts) in enumerate(segs):
            if plan['vertex'][i] and inside(ink, pts[0]):
                plan['vertex'][i] = None
        n = len(plan['vertex'])
        for i in range(n):
            if not (plan['vertex'][i] and plan['vertex'][(i + 1) % n]):
                plan['terminal'][i] = False
    return plans


class Builder:
    def __init__(self, masters):
        self.masters = masters  # {(opsz, wght): Master}
        self.ref = masters[REF] if REF in masters else next(iter(masters.values()))
        self.plans = {}
        self.ref_sharp = {}
        self.flats = {}
        self.made = {}  # (opsz, wght) -> {name: {rond: Glyph}}

    def sharp(self, m, name, spec):
        """Sharp contours, width and anchors of an inter/custom glyph in master m, aligned to the
        reference master's contour order."""
        contours, width, anchors = sharp_inter(m, spec)
        if name not in self.ref_sharp:
            ref = contours if m is self.ref else sharp_inter(self.ref, spec)[0]
            self.ref_sharp[name] = ref
            self.flats[name] = find_crotches(ref, self.ref.stem, ink_sign(ref))
        try:
            contours = align(contours, self.ref_sharp[name])
        except ValueError as e:
            raise ValueError(f'{name} in {m.opsz}/{m.wght}: {e}')
        return grid(point_crotches(contours, self.flats[name])), width, anchors

    def plan(self, name, spec):
        if name not in self.plans:
            ref_contours = self.sharp(self.ref, name, spec)[0]
            self.plans[name] = plan_glyph(ref_contours, self.ref.stem)
            for p in self.plans[name]:
                p['bend_cap'] = spec.get('bend_cap', False)
            if spec.get('union') is False:  # overlapping parts: no fillets where one is inside another
                for i, (p, c) in enumerate(zip(self.plans[name], ref_contours)):
                    hide([p], [c], [d for j, d in enumerate(ref_contours) if j != i])
        return self.plans[name]

    def build_master(self, m, ronds):
        """{name: {rond: Glyph}}. ROND 10 and 30 (sparse layers) only for glyphs that need them: those
        whose rounding trims curves, which interpolate between ROND 0 and 50 only roughly."""
        out = {}
        sparse = [r for r in ronds if r in m.sparse]
        ronds = [r for r in ronds if r not in m.sparse]
        for name in ORDER:
            spec = R[name]
            kind = spec['kind']
            out[name] = {}
            if kind in ('inter', 'custom'):
                contours, width, anchors = self.sharp(m, name, spec)
                plan = self.plan(name, spec)
                for r in ronds + sparse:
                    rc = round_glyph(contours, plan, m.R, r, m.stem)
                    out[name][r] = to_glyph(name, spec, rc, width, anchors)
                if sparse:
                    lo = round_glyph(contours, plan, m.R, 0, m.stem)
                    hi = round_glyph(contours, plan, m.R, 50, m.stem)
                    for r in sparse:
                        k = r / 50
                        rc = [[(p.x, p.y) for p in c.points] for c in out[name][r].contours]
                        miss = max((math.dist(q, (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
                                    for c0, c1, cr in zip(lo, hi, rc) for a, b, q in zip(c0, c1, cr)), default=0)
                        if miss <= 0.25:
                            del out[name][r]
            elif kind == 'ref':
                for r in ronds:
                    f = m.fonts[r]
                    base = spec['base']
                    bg = out[base][r] if base in out else f[base]
                    comps = [(base, (0, 0))]
                    anchors = {a.name: (a.x, a.y) for a in bg.anchors}
                    for mark, how in spec['marks']:
                        mg = f[mark]
                        ma = {a.name: (a.x, a.y) for a in mg.anchors}
                        if how == 'top':
                            bx, by = anchors['top']
                            mx, my = ma['_top']
                            comps.append((mark, (round(bx - mx), round(by - my))))
                        else:  # a stroke across the stem, placed as Allo places it on T (Tbar) / h (hbar)
                            comps.append((mark, self.stroke_offset(m, r, name, base, mark, out)))
                    if spec['marks'] and spec['marks'][0][1] == 'top':
                        mk = spec['marks'][0][0]
                        top = {a.name: (a.x, a.y) for a in m.fonts[r][mk].anchors}.get('top')
                        if top:
                            dx, dy = comps[1][1]
                            anchors['top'] = (top[0] + dx, top[1] + dy)
                    out[name][r] = to_glyph(name, spec, [], bg.width, anchors, comps)
            elif kind in ('mirror', 'rotate'):
                base = spec['base']
                for r in ronds + sparse:
                    f = m.source(r)
                    if base in out:
                        if r not in out[base]:
                            continue
                        src = out[base][r]
                    elif base in f:
                        src = f[base]
                    else:
                        continue
                    contours = [[(p.x, p.y, p.type) for p in c.points] for c in src.contours]
                    if src.components:
                        contours = ufo_glyph_contours(f, base)
                    anchors = {a.name: (a.x, a.y) for a in src.anchors}
                    if kind == 'mirror':
                        contours = mirror(contours, src.width)
                        anchors = {k: (src.width - x, y) for k, (x, y) in anchors.items()}
                    else:
                        h = m.xheight if spec.get('lower') else m.cap
                        contours = rotate(contours, src.width, h)
                        anchors = {'top': (src.width / 2, h), 'bottom': (src.width / 2, 0)}
                    out[name][r] = to_glyph(name, spec, contours, src.width, anchors)
            elif kind == 'bar':
                self.build_bar(m, name, spec, ronds + [r for r in sparse if spec['base'] in m.source(r)], out)
            elif kind == 'pair':
                self.build_pair(m, name, spec, ronds, out)
            elif kind == 'yu':
                self.build_yu(m, name, spec, ronds, out)
        self.anchor(m, out)
        return out

    def anchor(self, m, out):
        """Every Cyrillic letter takes marks: where a recipe gave it no top or bottom anchor, they go
        over the middle of its outline, at the x-height or cap height and on the baseline; over an
        ascender's top (б ђ ф) at cap height, as Allo's h and l have them. They are measured on the
        ROND 0 outline, so every ROND has the same anchors."""
        for name, by_rond in out.items():
            spec = R.get(name)
            if not spec or not spec.get('uni') or not chr(spec['uni']).isalpha():
                continue
            r0 = 0 if 0 in by_rond else min(by_rond)
            contours = self.decompose(m, r0, by_rond[r0], out)
            x0, _, x1, y1 = bbox(contours)
            x = round((x0 + x1) / 2)
            if chr(spec['uni']).isupper():
                top = (x, m.cap)
            elif y1 > m.xheight + 200:
                tops = [p[0] for c in contours for p in c if p[2] is not None and p[1] > y1 - 1]
                top = (round((min(tops) + max(tops)) / 2), m.cap)
            else:
                top = (x, m.xheight)
            for r, g in by_rond.items():
                have = {a.name for a in g.anchors}
                if 'top' not in have:
                    g.anchors.append(Anchor(*top, 'top'))
                if 'bottom' not in have:
                    g.anchors.append(Anchor(x, 0, 'bottom'))

    def decompose(self, m, r, g, out):
        contours = [[(p.x, p.y, p.type) for p in c.points] for c in g.contours]
        for comp in g.components:
            dx, dy = comp.transformation[4], comp.transformation[5]
            base = out[comp.baseGlyph][r] if comp.baseGlyph in out and r in out[comp.baseGlyph] else m.source(r)[comp.baseGlyph]
            contours += shift(self.decompose(m, r, base, out), dx, dy)
        return contours

    # -- glyphs from Allo's glyph plus parts of Inter's drawing ----------------------------------

    def part_map(self, m, base, mirror_=False):
        """x mapping from Inter's drawing of `base` to Allo's (box to box, horizontally)."""
        f = m.fonts[0]
        a = ufo_glyph_contours(f, base)
        ig = m.inter.decomposed_at(base, m.loc)
        ax0, _, ax1, _ = bbox(a)
        ix0, _, ix1, _ = bbox(ig['contours'])
        k = (ax1 - ax0) / (ix1 - ix0)
        if mirror_:
            wa, wi = f[base].width, ig['width']
            return lambda x: wa - (ax0 + ((wi - x) - ix0) * k)
        return lambda x: ax0 + (x - ix0) * k

    def extra_parts(self, m, spec, known):
        """Inter's contours of spec['source'] that are not part of the base letter (the bar of Є)."""
        contours, width, anchors = m.inter_parts(spec['source'])
        return [c for c in contours if len(c) not in known], width, anchors

    def build_bar(self, m, name, spec, ronds, out):
        """Є = C + bar, є = c + bar, Ө = O + bar, ө = o + bar: Allo's letter as a component and the bar
        (from Inter's drawing, rounded here) as a second one, overlapping as Allo's dcroat and Tbar do.
        Э and э turn C and c round, which a component can't: they are outlines, overlaps marked."""
        base = spec['base']
        base_counts = {len(to_cubic(c)) for c in m.inter.decomposed_at(base, m.loc)['contours']}
        bars, iw, ianchors = self.extra_parts(m, spec, base_counts)
        fx = self.part_map(m, base, spec['mirror'])
        bars = grid([[(fx(x), y, t) for x, y, t in c] for c in bars])
        if name not in self.plans:  # the reference master comes first
            ink = m.sharp(base)
            if spec['mirror']:
                ink = mirror(ink, m.fonts[0][base].width)
            self.plans[name] = hide(plan_glyph(bars, self.ref.stem), bars, ink)
        bar_plan = self.plans[name]
        anchors = {k: (round(fx(x)), round(y)) for k, (x, y) in ianchors.items()}
        part = name + '.bar'
        for r in ronds:
            f = m.source(r)
            width = f[base].width
            rb = round_glyph(bars, bar_plan, m.R, r, m.stem)
            if spec['mirror']:
                src = mirror([[(p.x, p.y, p.type) for p in c.points] for c in f[base].contours], width)
                out[name][r] = to_glyph(name, spec, src + rb, width, anchors, overlap=True)
            elif r in m.fonts:
                out.setdefault(part, {})[r] = to_glyph(part, {}, rb, width, {})
                out[name][r] = to_glyph(name, spec, [], width, anchors, [(base, (0, 0)), (part, (0, 0))])

    def build_pair(self, m, name, spec, ronds, out):
        """Ы = Ь + I (₨ = R + s) as components, the gap between them Inter's, Allo's spacing on the outer
        sides."""
        left, right = spec['parts']
        ig = m.inter.glyph_at(spec['source'], m.loc)
        offs = dict((c[0], c[1][4]) for c in ig['components'])
        ileft, iright = spec.get('inter_parts') or (
            'Softsign-cy' if left == 'uni042C' else 'softsigncyrillic', 'I' if right == 'I' else 'idotless')
        il = m.inter.decomposed_at(ileft, m.loc)
        ir = m.inter.decomposed_at(iright, m.loc)
        gap = (offs[iright] + bbox(ir['contours'])[0]) - bbox(il['contours'])[2]
        # measured on the ROND 0 outlines, so the advance is the same at every ROND (rounding R's leg
        # would move its right edge, and text would reflow as ROND changes)
        f0 = m.fonts[0]
        lc = ([[(p.x, p.y, p.type) for p in c.points] for c in out[left][0].contours] if left in out
              else ufo_glyph_contours(f0, left))
        x = round(bbox(lc)[2] + gap - bbox(ufo_glyph_contours(f0, right))[0])
        for r in ronds:
            f = m.fonts[r]
            width = x + f[right].width
            anchors = {}
            out[name][r] = to_glyph(name, spec, [], width, anchors, [(left, (0, 0)), (right, (x, 0))])

    def build_yu(self, m, name, spec, ronds, out):
        """Ю = I + O + bar, ю = ı + o + bar: Allo's letters as components at Inter's gap, and the bar
        (rounded here) as a third component."""
        left, right = spec['parts']
        ig = m.inter.glyph_at(spec['source'], m.loc)
        comps = dict((c[0], c[1][4]) for c in ig['components'])
        own = [to_cubic(c) for c in ig['contours']]  # Inter's own rectangles: the bar (and ю's stem)
        ro = m.inter.decomposed_at(right, m.loc)
        o_x0 = comps[right] + bbox(ro['contours'])[0]
        f0 = m.fonts[0]
        a_left = ufo_glyph_contours(f0, left)
        a_right = ufo_glyph_contours(f0, right)
        if left in comps:  # Ю: Inter's I is a component too
            il = m.inter.decomposed_at(left, m.loc)
            stem_x0 = comps[left] + bbox(il['contours'])[0]
            stem_x1 = comps[left] + bbox(il['contours'])[2]
        else:  # ю: Inter draws the stem as a rectangle (the taller of its own two)
            tall = max(own, key=lambda c: bbox([c])[3] - bbox([c])[1])
            stem_x0, stem_x1 = bbox([tall])[0], bbox([tall])[2]
            own = [c for c in own if c is not tall]
        dl, _ = m.delta('H' if left == 'I' else 'n')
        x_l = round(stem_x0 + dl - bbox(a_left)[0])  # Allo's stem where Inter's (respaced) is
        a_left_x1 = x_l + bbox(a_left)[2]
        x_o = round(a_left_x1 + (o_x0 - stem_x1) - bbox(a_right)[0])
        bars = []
        for c in own:  # the bar keeps its overlap into the stem and into the bowl
            x0, y0, x1, y1 = bbox([c])
            nx0 = a_left_x1 - (stem_x1 - x0)
            nx1 = x_o + bbox(a_right)[0] + (x1 - o_x0)
            bars.append([(nx0 if abs(x - x0) < abs(x - x1) else nx1, y, t) for x, y, t in c])
        bars = grid(bars)
        if name not in self.plans:  # the reference master comes first
            ink = shift(m.sharp(left), x_l) + shift(m.sharp(right), x_o)
            self.plans[name] = hide(plan_glyph(bars, self.ref.stem), bars, ink)
        bar_plan = self.plans[name]
        part = name + '.bar'
        for r in ronds:
            f = m.fonts[r]
            width = x_o + f[right].width
            out.setdefault(part, {})[r] = to_glyph(part, {}, round_glyph(bars, bar_plan, m.R, r, m.stem), width, {})
            out[name][r] = to_glyph(name, spec, [], width, {}, [(left, (x_l, 0)), (right, (x_o, 0)), (part, (0, 0))])

    def stroke_offset(self, m, r, name, base, mark, out):
        """Where Allo would put a crossbar on this letter: Inter's offset, moved with the stem."""
        src = {'uni0492': ('Ghestrokecyrillic', 'Ge-cy', 'H'), 'uni0493': ('ghestrokecyrillic', 'ge-cy', 'n'),
               'uni04B0': ('Ustraightstrokecyrillic', 'Y', None), 'uni04B1': ('ustraightstrokecyrillic', 'gamma', 'v')}[name]
        ig = m.inter.glyph_at(src[0], m.loc)
        offs = {c[0]: c[1] for c in ig['components']}
        dx, dy = round(offs[mark][4]), round(offs[mark][5])
        # the stem moved by the base's left delta (Allo's own base for Y)
        if src[2] is None:
            ax0 = bbox(ufo_glyph_contours(m.fonts[0], base))[0]
            ix0 = bbox(m.inter.decomposed_at(src[1], m.loc)['contours'])[0]
            fx = self.part_map(m, base)
            # place the bar's centre where the stem's centre maps
            bar = m.inter.decomposed_at(mark, m.loc)
            bx0, _, bx1, _ = bbox(bar['contours'])
            centre = dx + (bx0 + bx1) / 2
            return (round(fx(centre) - (bx0 + bx1) / 2), dy)
        dl, _ = m.delta(src[2])
        return (round(dx + dl), dy)


# -------------------------------------------------------------------------------------------- main

def load_masters(inter, wanted, root):
    """Masters to build ({(opsz, wght): Master}) and the opsz 9 fonts to fill from opsz 14
    ({(wght, rond): path})."""
    by_pair, sparse, small = {}, {}, {}
    for opsz, wght, rond, path, layer in designspace_masters():
        path = root / path.relative_to(ROOT)
        if layer is not None:
            sparse.setdefault((opsz, wght), {})[rond] = layer
        elif opsz == 9:
            small[(wght, rond)] = path
        else:
            by_pair.setdefault((opsz, wght), {})[rond] = path
    masters = {}
    for (opsz, wght), paths in by_pair.items():
        if wanted and not any((o, w) == (opsz, wght) or (o == 9 and opsz == 14 and w == wght) for o, w, r in wanted):
            continue
        fonts = {r: ufoLib2.Font.open(p) for r, p in paths.items()}
        masters[(opsz, wght)] = Master(inter, opsz, wght, fonts, sparse.get((opsz, wght)))
    return masters, small


def shifted(g, d, widths):
    """A glyph of opsz 14 as opsz 9 has it: everything d units right, d wider each side; marks
    (zero-width components) move with it, other components already do (release.json "smallShift")."""
    n = copy.deepcopy(g)
    if not n.width:
        return n
    for c in n.contours:
        for p in c.points:
            p.x += d
    for a in n.anchors:
        a.x += d
    for comp in n.components:
        if not widths.get(comp.baseGlyph):
            xx, xy, yx, yy, dx, dy = comp.transformation
            comp.transformation = (xx, xy, yx, yy, dx + d, dy)
    n.width += 2 * d
    return n


OURS = re.compile(r'^(uni04[0-9A-F]{2}|tenge|lari|tugrik|Sigma|manat|cedi|coloncurrency|guarani|kip|rupee|Xi|'
                  r'dram|taka|riel)(\..+)?$')


def write(font, glyphs, order_after='eth'):
    """Put the Cyrillic glyphs in a font (any from an earlier run go first), after `order_after` in its
    glyph order: each letter, then its parts."""
    for name in [n for n in font.keys() if OURS.match(n)]:
        del font[name]
    for name, g in glyphs.items():
        font.layers.defaultLayer.insertGlyph(g, name=name)
    def key(n):
        base = n.split('.')[0]
        return (R[base]['uni'] if R.get(base, {}).get('uni') else int(base[3:], 16), n)
    letters = sorted((n for n in glyphs if n not in POSTSCRIPT), key=key)
    money = sorted((n for n in glyphs if n in POSTSCRIPT), key=key)
    go = [n for n in font.lib['public.glyphOrder'] if not OURS.match(n)]
    at = go.index(order_after) + 1 if order_after in go else len(go)
    go = go[:at] + letters + go[at:]
    at = go.index('bitcoin') + 1 if 'bitcoin' in go else len(go)  # with Allo's other currency signs
    font.lib['public.glyphOrder'] = go[:at] + money + go[at:]
    cats = font.lib.setdefault('public.openTypeCategories', {})
    for n in list(cats):
        if OURS.match(n):
            del cats[n]
    for n in glyphs:
        if n in R:
            cats[n] = 'base'
    ps = font.lib.setdefault('public.postscriptNames', {})
    for n, p in POSTSCRIPT.items():
        if n in glyphs:
            ps[n] = p


COPYRIGHT = ('Copyright 2026 Josh Puckett (https://joshpuckett.me). Copyright 2026 Degroshi '
             '(https://github.com/degroshi). Portions Copyright (c) 2016 The Inter Project Authors '
             '(https://github.com/rsms/inter)')


def finish(font):
    """The features and copyright that go with the Cyrillic."""
    import features
    enc = [(n, s['uni']) for n, s in R.items() if s.get('uni')]
    font.features.text = features.update(
        font.features.text,
        caps=[n for n, u in enc if chr(u).isupper()],
        letters=[n for n, u in enc if chr(u).isalpha()] + [n for n in R if not R[n].get('uni')],
        lower=[n for n, u in enc if chr(u).islower()],
        currency=[n for n, u in enc if not chr(u).isalpha()])
    font.features.text = features.arrows_to_dlig(font.features.text)
    font.info.copyright = COPYRIGHT


def main():
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument('--masters', nargs='*', default=None, help='opsz,wght,rond triples (default: all)')
    ap.add_argument('--root', default=str(ROOT), help='repo root holding sources/ (a scratch copy for trials)')
    args = ap.parse_args()
    root = Path(args.root)
    wanted = {tuple(int(v) for v in s.split(',')) for s in args.masters} if args.masters else None
    small_shift = json.loads((ROOT / 'release.json').read_text()).get('smallShift', 0)
    inter = Inter()
    masters, small = load_masters(inter, wanted, root)
    b = Builder(masters)
    any_font = next(iter(masters.values())).fonts[0]
    latin_groups = {g: [n for n in v if not kerning.OURS.match(n)] for g, v in any_font.groups.items()}
    group_plan = kerning.group_plan(inter, R, latin_groups)
    for (opsz, wght), m in sorted(masters.items(), key=lambda kv: kv[0] != REF):
        ronds = sorted(r for r in list(m.fonts) + list(m.sparse)
                       if wanted is None or (opsz, wght, r) in wanted or (9, wght, r) in wanted)
        print(f'opsz {opsz} wght {wght}: Inter wght {m.loc["wght"]}, R {m.R:.2f}, stem {m.stem:.1f}', flush=True)
        made = b.build_master(m, ronds)
        pairs = None
        for r in ronds:
            if r in m.sparse:
                continue
            if wanted is None or (opsz, wght, r) in wanted:
                font = m.fonts[r]
                write(font, {n: made[n][r] for n in made if r in made[n]})
                kerning.apply_groups(font, group_plan)
                cyr = kerning.cyrillic_only(font)
                if pairs is None:
                    pairs, ratio = kerning.cyrillic_pairs(inter, R, m.loc, font, cyr)
                    print(f'  kerning: {len(pairs)} Cyrillic pairs (Allo/Inter {ratio:.3f})', flush=True)
                kerning.apply_pairs(font, pairs, cyr)
                finish(font)
        for r, layer_name in m.sparse.items():
            if r not in ronds:
                continue
            layer = m.fonts[50].layers[layer_name]
            for n in [n for n in layer.keys() if OURS.match(n)]:
                del layer[n]
            for n in made:
                if r in made[n]:
                    layer.insertGlyph(made[n][r], name=n)
        for r, font in m.fonts.items():
            if wanted is None or (opsz, wght, r) in wanted or (r == 50 and any(x in ronds for x in m.sparse)):
                font.save(overwrite=True)
        if opsz == 14:
            for r in (0, 50, 100):
                if (wght, r) in small and (wanted is None or (9, wght, r) in wanted):
                    font = ufoLib2.Font.open(small[(wght, r)])
                    widths = {g.name: g.width for g in font}
                    here = {n: made[n][r] for n in made if r in made[n]}
                    widths.update({n: g.width for n, g in here.items()})
                    write(font, {n: shifted(g, small_shift, widths) for n, g in here.items()})
                    kerning.apply_groups(font, group_plan)
                    kerning.apply_pairs(font, pairs, kerning.cyrillic_only(font))
                    finish(font)
                    font.save(overwrite=True)
                    print(f'  opsz 9 wght {wght} ROND {r}: opsz 14 moved {small_shift} each side', flush=True)


if __name__ == '__main__':
    main()

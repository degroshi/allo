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
import shutil
import sys
from pathlib import Path

import ufoLib2
from ufoLib2.objects import Anchor, Component, Contour, Glyph, Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
from allo import ROOT, masters as designspace_masters, radius  # noqa: E402
from inter import Inter, reverse_contour  # noqa: E402
from outline import align, point_crotches, union  # noqa: E402
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
inter('uni0490', 0x0490, 'afii10050', ('H', 'T'))
ref('uni0492', 0x0492, 'uni0413', [('crossbar.uc', 'stroke')])
inter('uni049A', 0x049A, 'Kadescendercyrillic', ('H', 'K'))
inter('uni04A2', 0x04A2, 'Endescendercyrillic', ('H', 'H'))
ref('uni04AE', 0x04AE, 'Y')
ref('uni04B0', 0x04B0, 'Y', [('crossbar.uc', 'stroke')])
turned('uni04BA', 0x04BA, 'rotate', 'uni0427')
inter('uni04D8', 0x04D8, 'Schwacyrillic', ('O', 'O'))
bar('uni04E8', 0x04E8, 'O', 'afii10147')
# lowercase
ref('uni0430', 0x0430, 'a')
inter('uni0431', 0x0431, 'becyrillic', ('o', 'o'))
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
inter('uni0444', 0x0444, 'efcyrillic', ('o', 'o'), union=False)
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
inter('uni044F', 0x044F, 'iacyrillic', ('o', 'n'))
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
inter('uni04AF', 0x04AF, 'ustraightcyrillic', ('v', 'v'))
ref('uni04B1', 0x04B1, 'uni04AF', [('crossbar', 'stroke')])
ref('uni04BB', 0x04BB, 'h')
turned('uni04D9', 0x04D9, 'rotate', 'e', lower=True)
bar('uni04E9', 0x04E9, 'o', 'obarredcyrillic')
# currency
inter('tenge', 0x20B8, 'tenge', ('T', 'T'))
inter('lari', 0x20BE, 'lari', ('O', 'O'))
# alternates
ref('uni0406.1', None, 'I.1')
ref('uni0407.1', None, 'Idieresis.1')
ref('uni0430.1', None, 'a.1')

ORDER = list(R)
POSTSCRIPT = {'tenge': 'uni20B8', 'lari': 'uni20BE'}


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

    def __init__(self, inter, opsz, wght, fonts):
        self.inter, self.opsz, self.wght = inter, opsz, wght
        self.fonts = fonts  # {rond: ufoLib2.Font} (0, 50, 100 always; others for sparse layers)
        self.R = radius(fonts[0], fonts[50])
        self.xheight = fonts[0].info.xHeight
        self.cap = fonts[0].info.capHeight
        self.stem = self.allo_stem()
        self.loc = {'opsz': min(max(opsz, 14), 32), 'wght': self.calibrate()}
        self._delta = {}

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
        g = self.inter.decomposed_at(source, self.loc)
        return [to_cubic(c) for c in g['contours']], g['width'], dict(g['anchors'])


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


MAKERS = {'straight_u': straight_u}


def sharp_inter(m, spec):
    contours, width, anchors = m.inter_parts(spec['source'])
    if spec.get('make'):
        contours, width = MAKERS[spec['make']](m, contours, width)
    if spec.get('union', True) and len(contours) > 1:
        contours = union(contours)
    contours = point_crotches(contours, m.stem, ink_sign(contours))
    dl, _ = m.delta(spec['sb'][0])
    _, dr = m.delta(spec['sb'][1])
    contours = grid(shift(contours, dl))
    anchors = {k: (round(x + dl), round(y)) for k, (x, y) in anchors.items()}
    return contours, round(width + dl + dr), anchors


def grid(contours):
    """Sharp outlines on whole units, as Allo's own (only its fillets leave the grid)."""
    return [[(round(x), round(y), t) for x, y, t in c] for c in contours]


# ------------------------------------------------------------------------------------------ build

def to_glyph(name, spec, contours, width, anchors, components=()):
    g = Glyph(name)
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


class Builder:
    def __init__(self, masters):
        self.masters = masters  # {(opsz, wght): Master}
        self.ref = masters[REF] if REF in masters else next(iter(masters.values()))
        self.plans = {}
        self.ref_sharp = {}
        self.made = {}  # (opsz, wght) -> {name: {rond: Glyph}}

    def sharp(self, m, name, spec):
        """Sharp contours, width and anchors of an inter/custom glyph in master m, aligned to the
        reference master's contour order."""
        contours, width, anchors = sharp_inter(m, spec)
        if name not in self.ref_sharp:
            if m is self.ref:
                self.ref_sharp[name] = contours
            else:
                self.ref_sharp[name] = sharp_inter(self.ref, spec)[0]
        try:
            contours = align(contours, self.ref_sharp[name])
        except ValueError as e:
            raise ValueError(f'{name} in {m.opsz}/{m.wght}: {e}')
        return contours, width, anchors

    def plan(self, name, spec):
        if name not in self.plans:
            ref_contours = self.sharp(self.ref, name, spec)[0]
            self.plans[name] = plan_glyph(ref_contours, self.ref.stem)
        return self.plans[name]

    def build_master(self, m, ronds):
        out = {}
        for name in ORDER:
            spec = R[name]
            kind = spec['kind']
            out[name] = {}
            if kind in ('inter', 'custom'):
                contours, width, anchors = self.sharp(m, name, spec)
                plan = self.plan(name, spec)
                for r in ronds:
                    rc = round_glyph(contours, plan, m.R, r, m.stem)
                    out[name][r] = to_glyph(name, spec, rc, width, anchors)
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
                for r in ronds:
                    f = m.fonts[r]
                    base = spec['base']
                    src = out[base][r] if base in out else f[base]
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
                self.build_bar(m, name, spec, ronds, out)
            elif kind == 'pair':
                self.build_pair(m, name, spec, ronds, out)
            elif kind == 'yu':
                self.build_yu(m, name, spec, ronds, out)
        return out

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
        base = spec['base']
        f0 = m.fonts[0]
        base_counts = {len(to_cubic(c)) for c in m.inter.decomposed_at(base, m.loc)['contours']}
        bars, iw, ianchors = self.extra_parts(m, spec, base_counts)
        fx = self.part_map(m, base, spec['mirror'])
        bars = grid([[(fx(x), y, t) for x, y, t in c] for c in bars])
        if name not in self.plans:
            self.plans[name] = None
        bar_plan = plan_glyph(bars, self.ref.stem)
        for r in ronds:
            f = m.fonts[r]
            src = [[(p.x, p.y, p.type) for p in c.points] for c in f[base].contours]
            width = f[base].width
            if spec['mirror']:
                src = mirror(src, width)
            rb = round_glyph(bars, bar_plan, m.R, r, m.stem)
            anchors = {k: (round(fx(x)), round(y)) for k, (x, y) in ianchors.items()}
            out[name][r] = to_glyph(name, spec, src + rb, width, anchors)

    def build_pair(self, m, name, spec, ronds, out):
        """Ы = Ь + I as components, the gap between them Inter's, Allo's spacing on the outer sides."""
        left, right = spec['parts']
        ig = m.inter.glyph_at(spec['source'], m.loc)
        offs = dict((c[0], c[1][4]) for c in ig['components'])
        ileft = 'Softsign-cy' if left == 'uni042C' else 'softsigncyrillic'
        iright = 'I' if right == 'I' else 'idotless'
        il = m.inter.decomposed_at(ileft, m.loc)
        ir = m.inter.decomposed_at(iright, m.loc)
        gap = (offs[iright] + bbox(ir['contours'])[0]) - bbox(il['contours'])[2]
        for r in ronds:
            f = m.fonts[r]
            lg = out[left][r]
            lc = [[(p.x, p.y, p.type) for p in c.points] for c in lg.contours]
            rgc = ufo_glyph_contours(f, right)
            x = round(bbox(lc)[2] + gap - bbox(rgc)[0])
            width = x + f[right].width
            anchors = {}
            out[name][r] = to_glyph(name, spec, [], width, anchors, [(left, (0, 0)), (right, (x, 0))])

    def build_yu(self, m, name, spec, ronds, out):
        """Ю = I + bar + O (ю = ı + bar + o): Allo's letters, Inter's gap and bar."""
        left, right = spec['parts']
        ig = m.inter.glyph_at(spec['source'], m.loc)
        comps = dict((c[0], c[1][4]) for c in ig['components'])
        ileft, iright = left if left != 'idotless' else None, right
        icontours, iw, _ = m.inter_parts(spec['source'])
        # Inter: Ю's own contours are the stem/bar rectangles; the O (and I) are components
        own = [to_cubic(c) for c in ig['contours']]
        ro = m.inter.decomposed_at(iright, m.loc)
        o_x0 = comps[iright] + bbox(ro['contours'])[0]
        f0 = m.fonts[0]
        a_right = ufo_glyph_contours(f0, right)
        if left in comps:
            il = m.inter.decomposed_at(left, m.loc)
            stem_x1 = comps[left] + bbox(il['contours'])[2]
            a_left_x1 = bbox(ufo_glyph_contours(f0, left))[2]
            stem_parts = []
        else:  # ю: the stem is one of Inter's own rectangles (the taller one)
            tall = max(own, key=lambda c: bbox([c])[3] - bbox([c])[1])
            stem_x1 = bbox([tall])[2]
            a_left_x1 = None
            stem_parts = [tall]
            own = [c for c in own if c is not tall]
        gap = o_x0 - stem_x1
        dl, _ = m.delta('H' if left == 'I' else 'n')
        if stem_parts:
            stem_parts = shift(stem_parts, dl)
            a_left_x1 = bbox(stem_parts)[2]
        x_o = a_left_x1 + gap - bbox(a_right)[0]
        # the bar keeps its overlap into the stem and into the bowl
        bars = []
        for c in own:
            x0, y0, x1, y1 = bbox([c])
            nx0 = a_left_x1 - (stem_x1 - x0)
            nx1 = x_o + bbox(a_right)[0] + (x1 - o_x0)
            bars.append([(nx0 if abs(x - x0) < abs(x - x1) else nx1, y, t) for x, y, t in c])
        bars = grid(bars)
        stem_parts = grid(stem_parts)
        x_o = round(x_o)
        bar_plan = plan_glyph(bars, self.ref.stem)
        stem_plan = plan_glyph(stem_parts, self.ref.stem) if stem_parts else None
        for r in ronds:
            f = m.fonts[r]
            parts = []
            if stem_parts:
                parts += round_glyph(stem_parts, stem_plan, m.R, r, m.stem)
            else:
                parts += [[(p.x, p.y, p.type) for p in c.points] for c in f[left].contours]
            parts += shift([[(p.x, p.y, p.type) for p in c.points] for c in f[right].contours], x_o)
            parts += round_glyph(bars, bar_plan, m.R, r, m.stem)
            width = x_o + f[right].width
            out[name][r] = to_glyph(name, spec, parts, width, {})

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
    by_pair = {}
    for opsz, wght, rond, path, layer in designspace_masters():
        if layer is not None:
            continue
        if wanted and (opsz, wght, rond) not in wanted:
            continue
        by_pair.setdefault((opsz, wght), {})[rond] = root / path.relative_to(ROOT)
    masters = {}
    for (opsz, wght), paths in by_pair.items():
        if opsz == 9:
            continue  # opsz 9 is opsz 14 with wider spacing (see write)
        fonts = {r: ufoLib2.Font.open(p) for r, p in paths.items()}
        for r in (0, 50):
            if r not in fonts:
                fonts[r] = ufoLib2.Font.open(root / f'sources/masters/Allo-opsz{opsz}-wght{wght}-ROND{r}.ufo')
        masters[(opsz, wght)] = Master(inter, opsz, wght, fonts)
    return masters


def write(font, glyphs, order_after='eth'):
    for name, g in glyphs.items():
        if name in font:
            del font[name]
        font.layers.defaultLayer.insertGlyph(g, name=name)
    go = [n for n in font.lib['public.glyphOrder'] if n not in glyphs]
    at = go.index(order_after) + 1 if order_after in go else len(go)
    font.lib['public.glyphOrder'] = go[:at] + [n for n in ORDER if n in glyphs] + go[at:]
    cats = font.lib.setdefault('public.openTypeCategories', {})
    for n in glyphs:
        cats[n] = 'base'
    ps = font.lib.setdefault('public.postscriptNames', {})
    for n, p in POSTSCRIPT.items():
        if n in glyphs:
            ps[n] = p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--masters', nargs='*', default=None, help='opsz,wght,rond triples (default: all)')
    ap.add_argument('--root', default=str(ROOT), help='repo root holding sources/ (a scratch copy for trials)')
    args = ap.parse_args()
    root = Path(args.root)
    wanted = {tuple(int(v) for v in s.split(',')) for s in args.masters} if args.masters else None
    inter = Inter()
    masters = load_masters(inter, wanted, root)
    b = Builder(masters)
    for (opsz, wght), m in sorted(masters.items(), key=lambda kv: kv[0] != REF):
        ronds = sorted(r for r in m.fonts if wanted is None or (opsz, wght, r) in wanted)
        print(f'opsz {opsz} wght {wght}: Inter wght {m.loc["wght"]}, R {m.R:.2f}, stem {m.stem:.1f}', flush=True)
        made = b.build_master(m, ronds)
        for r in ronds:
            font = m.fonts[r]
            write(font, {n: made[n][r] for n in ORDER})
            font.save(overwrite=True)


if __name__ == '__main__':
    main()

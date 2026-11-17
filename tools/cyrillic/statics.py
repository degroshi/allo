#!/usr/bin/env python3
"""Cyrillic for Allo's 18 static fonts (sources/static), made the way Allo's own are.

Uprights are the masters at opsz 14, ROND 50, cut at the static's weight: each Cyrillic glyph, its
anchors, components and kerning interpolated between the two masters around that weight.

Obliques are drawings of their own in Allo: the upright slanted 9 degrees about half the x-height
(y 559), rounded again, every glyph an outline. Here:
* a letter that is a Latin one (А, Ё, і ...) is Allo's own oblique glyph, marks moved with the slant;
* a letter turned from a Latin one around y 559 (ә) is Allo's oblique e turned;
* every other glyph is its sharp upright outline (the ROND 0 masters cut at the weight, fillets
  taken off), slanted, and rounded with rounding.py at the weight's radius;
* glyphs built on a Latin one (Є = C + bar, Ы = Ь + I) are that Latin oblique plus the slanted parts.

    statics.py [--root DIR]
"""
import argparse
import math
import sys
from pathlib import Path

import ufoLib2
from ufoLib2.objects import Anchor, Component, Contour, Glyph, Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
import features  # noqa: E402
import kerning  # noqa: E402
from allo import ROOT, radius, stem  # noqa: E402
from build_cyrillic import ORDER, OURS, R, hide, mirror, rotate, ufo_glyph_contours, write  # noqa: E402
from rounding import plan_glyph, round_glyph, straighten_spurs, to_cubic, unround  # noqa: E402

WEIGHTS = {'Thin': 100, 'ExtraLight': 200, 'Light': 300, 'Regular': 400, 'Medium': 490, 'SemiBold': 580,
           'Bold': 670, 'ExtraBold': 780, 'Black': 900}  # design values (the weight axis map)
MASTER_WEIGHTS = (100, 400, 580, 900)
SLANT = math.tan(math.radians(9))
CENTRE = 559  # half the x-height at opsz 14: the obliques slant about it


def lerp(a, b, t):
    return a + (b - a) * t


def bracket(w):
    for w0, w1 in zip(MASTER_WEIGHTS, MASTER_WEIGHTS[1:]):
        if w0 <= w <= w1:
            return w0, w1, (w - w0) / (w1 - w0)
    raise ValueError(w)


def mix(g0, g1, t, name):
    """A glyph between two compatible glyphs."""
    g = Glyph(name)
    g.width = round(lerp(g0.width, g1.width, t))
    g.unicodes = list(g0.unicodes)
    for c0, c1 in zip(g0.contours, g1.contours):
        g.contours.append(Contour(points=[Point(round(lerp(p.x, q.x, t), 3), round(lerp(p.y, q.y, t), 3), p.type)
                                          for p, q in zip(c0.points, c1.points)]))
    for a, b in zip(g0.components, g1.components):
        t0, t1 = a.transformation, b.transformation
        g.components.append(Component(a.baseGlyph, (1, 0, 0, 1, round(lerp(t0[4], t1[4], t)), round(lerp(t0[5], t1[5], t)))))
    b_anchors = {x.name: x for x in g1.anchors}
    for a in g0.anchors:
        if a.name in b_anchors:
            g.anchors.append(Anchor(round(lerp(a.x, b_anchors[a.name].x, t)), round(lerp(a.y, b_anchors[a.name].y, t)), a.name))
    g.lib.update(g0.lib)
    return g


def skew(contours):
    return [[(x + SLANT * (y - CENTRE), y, tp) for x, y, tp in c] for c in contours]


def outline(g):
    return [[(p.x, p.y, p.type) for p in c.points] for c in g.contours]


def to_glyph(name, uni, contours, width, anchors):
    g = Glyph(name)
    g.width = width
    if uni:
        g.unicodes = [uni]
    for c in contours:
        g.contours.append(Contour(points=[Point(round(x, 3), round(y, 3), t) for x, y, t in c]))
    for k, (x, y) in sorted(anchors.items()):
        g.anchors.append(Anchor(round(x), round(y), k))
    return g


class Weight:
    """Everything about one static weight: the upright Cyrillic (cut from the masters) and the sharp
    outlines and radius its oblique is made from."""

    def __init__(self, masters, w):
        w0, w1, t = bracket(w)
        self.w, self.t = w, t
        self.m0 = {r: masters[(w0, r)] for r in (0, 50)}
        self.m1 = {r: masters[(w1, r)] for r in (0, 50)}
        self.R = lerp(radius(self.m0[0], self.m0[50]), radius(self.m1[0], self.m1[50]), t)
        self.stem = lerp(stem(self.m0[0]), stem(self.m1[0]), t)

    def glyph(self, name, rond=50):
        return mix(self.m0[rond][name], self.m1[rond][name], self.t, name)

    def sharp(self, name):
        """The glyph's own contours at this weight without rounding (from the ROND 0 masters)."""
        g = self.glyph(name, 0)
        return [straighten_spurs(to_cubic(unround(c)), 0.3 * self.stem) for c in outline(g)]


def oblique_glyphs(wt, upright, oblique_font):
    """{name: Glyph} of the Cyrillic for one oblique font, all outlines."""
    out = {}

    def latin(name):  # Allo's own oblique drawing of a Latin glyph
        return outline(oblique_font[name])

    def get(name):
        if name in out:
            return outline(out[name])
        if OURS.match(name):
            make(name)
            return outline(out[name])
        return latin(name)

    def rounded(name, contours, spec, hidden_ink=None):
        plans = plan_glyph(contours, wt.stem)
        for p in plans:
            p['bend_cap'] = spec.get('bend_cap', False)
        if hidden_ink is not None:
            plans = hide(plans, contours, hidden_ink)
        return round_glyph(contours, plans, wt.R, 50, wt.stem)

    def skewed_anchors(g):
        return {a.name: (a.x + SLANT * (a.y - CENTRE), a.y) for a in g.anchors}

    def make(name):
        spec = R.get(name, {})
        up = upright[name]
        kind = spec.get('kind')
        anchors = skewed_anchors(up)
        if up.components and kind != 'bar' and kind != 'yu':
            # a Latin letter, or a letter with marks: the parts' obliques, marks moved with the slant
            contours = []
            for comp in up.components:
                dx, dy = comp.transformation[4], comp.transformation[5]
                contours += [[(x + dx + SLANT * dy, y + dy, t) for x, y, t in c] for c in get(comp.baseGlyph)]
        elif kind == 'rotate' and spec.get('lower'):
            # turned about half the x-height, where the slant turns with it: Allo's oblique e, turned
            contours = rotate(latin(spec['base']), up.width, 2 * CENTRE)
        elif kind in ('bar', 'yu') and up.components:
            contours = []
            parts = []
            for comp in up.components:
                dx, dy = comp.transformation[4], comp.transformation[5]
                if comp.baseGlyph.endswith('.bar'):
                    parts.append(comp.baseGlyph)
                    continue
                contours += [[(x + dx + SLANT * dy, y + dy, t) for x, y, t in c] for c in get(comp.baseGlyph)]
            for part in parts:
                bar = skew(wt.sharp(part))
                contours += rounded(part, bar, spec, hidden_ink=contours)
        else:
            sharp = skew(wt.sharp(name))
            ink = None
            if len(sharp) > 1 and up.lib.get('public.truetype.overlap'):
                # overlapping parts (Э: turned C and bar): no fillets where one part is inside another
                contours = []
                for i, c in enumerate(sharp):
                    others = [d for j, d in enumerate(sharp) if j != i]
                    contours += rounded(name, [c], spec, hidden_ink=others)
                out[name] = to_glyph(name, spec.get('uni'), contours, up.width, anchors)
                out[name].lib['public.truetype.overlap'] = True
                return
            contours = rounded(name, sharp, spec, hidden_ink=ink)
        out[name] = to_glyph(name, spec.get('uni'), contours, up.width, anchors)
        if up.lib.get('public.truetype.overlap') or (up.components and len(up.components) > 1 and kind in ('bar', 'yu')):
            out[name].lib['public.truetype.overlap'] = True

    for name in upright:
        if name.endswith('.bar'):
            continue
        if name not in out:
            make(name)
    return out


def merged(g):
    """A static font is one master, so overlapping contours (Ф ф я Э э) can be merged: CoreText draws
    Ф's CFF outline with its stem cut out where it crosses the ring, though the contours run right."""
    if not g.lib.get('public.truetype.overlap') or len(g.contours) < 2:
        return g
    import pathops
    from fontTools.pens.pointPen import PointToSegmentPen, SegmentToPointPen
    from fontTools.pens.recordingPen import RecordingPointPen
    from rounding import area, to_cubic
    path = pathops.Path()
    seg = PointToSegmentPen(path.getPen())
    for c in outline(g):
        seg.beginPath()
        for x, y, t in to_cubic(c):
            seg.addPoint((x, y), t)
        seg.endPath()
    path.simplify(fix_winding=True, keep_starting_points=True)
    rec = RecordingPointPen()
    path.draw(SegmentToPointPen(rec))
    contours, cur = [], None
    for op, args, kw in rec.value:
        if op == 'beginPath':
            cur = []
        elif op == 'addPoint':
            cur.append((args[0][0], args[0][1], args[1] if len(args) > 1 else kw.get('segmentType')))
        elif op == 'endPath':
            contours.append(cur)
    # PostScript direction, as the rest of the font: the largest contour counter-clockwise
    if area(max(contours, key=lambda c: abs(area(c)))) < 0:
        from inter import reverse_contour
        contours = [reverse_contour(c) for c in contours]
    n = to_glyph(g.name, g.unicodes[0] if g.unicodes else None, contours, g.width, {a.name: (a.x, a.y) for a in g.anchors})
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(ROOT))
    args = ap.parse_args()
    root = Path(args.root)
    masters = {(w, r): ufoLib2.Font.open(root / f'sources/masters/Allo-opsz14-wght{w}-ROND{r}.ufo')
               for w in MASTER_WEIGHTS for r in (0, 50)}
    names = [n for n in masters[(400, 50)].keys() if OURS.match(n)]
    fea = None
    for style, w in WEIGHTS.items():
        wt = Weight(masters, w)
        upright = {n: wt.glyph(n) for n in names}
        up_path = root / f'sources/static/Allo-{style}.ufo'
        ob_path = root / ('sources/static/Allo-' + ('' if style == 'Regular' else style) + 'Oblique.ufo')
        k0, k1 = wt.m0[50].kerning, wt.m1[50].kerning
        cyr_groups = kerning.cyrillic_only(wt.m0[50])
        pairs = {}
        for p in set(k0) | set(k1):
            if any(OURS.match(k) or k in cyr_groups for k in p):
                v = round(lerp(k0.get(p, 0), k1.get(p, 0), wt.t))
                if v:
                    pairs[p] = v
        for path, glyphs in ((up_path, upright), (ob_path, None)):
            font = ufoLib2.Font.open(path)
            if glyphs is None:
                glyphs = oblique_glyphs(wt, upright, font)
            glyphs = {n: merged(g) for n, g in glyphs.items()}
            write(font, glyphs)
            font.groups.clear()
            font.groups.update({g: list(v) for g, v in masters[(400, 50)].groups.items()})
            kerning.apply_pairs(font, pairs, cyr_groups)
            font.features.text = masters[(400, 50)].features.text
            font.info.copyright = masters[(400, 50)].info.copyright
            font.save(overwrite=True)
            print(f'{path.name}: {len(glyphs)} Cyrillic glyphs, {len(pairs)} Cyrillic pairs', flush=True)


if __name__ == '__main__':
    main()

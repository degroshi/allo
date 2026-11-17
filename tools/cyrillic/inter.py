"""Read Inter's Glyphs source and interpolate any glyph at any (opsz, wght) location.

Inter 4.1's roman has six masters (opsz 14/32 x wght 100/400/900) and no brace layers, so
an instance is a plain multilinear interpolation of compatible masters."""
import os
import pickle
from pathlib import Path

from fontTools.misc.vector import Vector
from fontTools.varLib.models import VariationModel, normalizeLocation

INTER_SRC = Path(os.environ.get('INTER_SRC', Path.home() / 'Projects/inter-src')) / 'src/Inter-Roman.glyphspackage'
CACHE = Path(os.environ.get('INTER_CACHE', INTER_SRC.parent.parent / '.inter-roman.pkl'))
AXES = {'opsz': (14, 14, 32), 'wght': (100, 400, 900)}


def load():
    if CACHE.exists() and CACHE.stat().st_mtime > INTER_SRC.stat().st_mtime:
        return pickle.loads(CACHE.read_bytes())
    import glyphsLib
    font = glyphsLib.GSFont(str(INTER_SRC))
    CACHE.write_bytes(pickle.dumps(font))
    return font


class Inter:
    def __init__(self):
        self.font = load()
        self.masters = [m for m in self.font.masters]
        self.master_ids = [m.id for m in self.masters]
        locs = [{'opsz': m.axes[0], 'wght': m.axes[1]} for m in self.masters]
        self.locations = locs
        self.model = VariationModel([normalizeLocation(l, AXES) for l in locs], axisOrder=['opsz', 'wght'])
        self._cache = {}

    def master_layers(self, name):
        g = self.font.glyphs[name]
        by_id = {l.layerId: l for l in g.layers}
        return [by_id[i] for i in self.master_ids]

    def raw(self, layer):
        """A layer as plain data: width, contours [[(x, y, type)]], components [(name, (xx,xy,yx,yy,dx,dy))], anchors."""
        contours = []
        for p in layer.paths:
            nodes = [(float(n.position.x), float(n.position.y), None if n.type == 'offcurve' else n.type) for n in p.nodes]
            if p.closed:  # Glyphs keeps a closed path's start node last; UFO keeps it first
                nodes = nodes[-1:] + nodes[:-1]
            contours.append(nodes)
        comps = [(c.name, tuple(float(v) for v in c.transform)) for c in layer.components]
        anchors = {a.name: (float(a.position.x), float(a.position.y)) for a in layer.anchors}
        return {'width': float(layer.width), 'contours': contours, 'components': comps, 'anchors': anchors}

    def glyph_at(self, name, loc):
        """Interpolated raw glyph at loc {'opsz','wght'} (design coordinates)."""
        key = (name, loc['opsz'], loc['wght'])
        if key in self._cache:
            return self._cache[key]
        raws = [self.raw(l) for l in self.master_layers(name)]
        ref = raws[0]
        for r in raws[1:]:
            assert [len(c) for c in r['contours']] == [len(c) for c in ref['contours']], name
            assert [c[0] for c in r['components']] == [c[0] for c in ref['components']], name
        anchor_names = [a for a in ref['anchors'] if all(a in r['anchors'] for r in raws)]

        def flat(r):
            v = [r['width']]
            for c in r['contours']:
                for x, y, _ in c:
                    v += [x, y]
            for _, t in r['components']:
                v += list(t)
            for a in anchor_names:
                v += list(r['anchors'][a])
            return v
        vecs = [Vector(flat(r)) for r in raws]
        out = self.model.interpolateFromMasters(normalizeLocation(loc, AXES), vecs)
        it = iter(out)
        res = {'width': next(it), 'contours': [], 'components': [], 'anchors': {}}
        for c in ref['contours']:
            res['contours'].append([(next(it), next(it), t) for _, _, t in c])
        for n, _ in ref['components']:
            res['components'].append((n, tuple(next(it) for _ in range(6))))
        for a in anchor_names:
            res['anchors'][a] = (next(it), next(it))
        self._cache[key] = res
        return res

    def decomposed_at(self, name, loc):
        """Contours with every component resolved, at loc."""
        g = self.glyph_at(name, loc)
        contours = [list(c) for c in g['contours']]
        for base, (xx, xy, yx, yy, dx, dy) in g['components']:
            for c in self.decomposed_at(base, loc)['contours']:
                moved = [(xx * x + yx * y + dx, xy * x + yy * y + dy, t) for x, y, t in c]
                if xx * yy - xy * yx < 0:  # a mirrored component: keep the contour's direction
                    moved = reverse_contour(moved)
                contours.append(moved)
        return {'width': g['width'], 'contours': contours, 'anchors': g['anchors'], 'components': []}


def reverse_contour(c):
    """The same closed contour running the other way (point types move with their segments)."""
    pts = list(c)
    first_on = next(i for i, p in enumerate(pts) if p[2] is not None)
    pts = pts[first_on:] + pts[:first_on]
    # segment types belong to the segment's end point; reversed, they belong to its start
    rev = []
    n = len(pts)
    for k in range(n):
        x, y, t = pts[-k % n]
        rev.append((x, y, t))
    # rev[0] is the old start; now assign each on-curve the type of the segment that arrives at it
    types = [p[2] for p in pts]
    out = []
    for k in range(n):
        x, y, t = rev[k]
        if t is None:
            out.append((x, y, None))
            continue
        # the segment arriving at rev[k] (reversed) is the old segment leaving pts[-k]: its type is
        # that of the next on-curve after pts[-k] in the old order
        j = (-k) % n
        m = (j + 1) % n
        while types[m] is None:
            m = (m + 1) % n
        out.append((x, y, types[m]))
    return out

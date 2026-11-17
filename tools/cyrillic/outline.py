"""Outline operations for the Cyrillic build: overlap removal and matching contours across masters."""
import math

from booleanOperations.booleanGlyph import BooleanGlyph
from fontTools.pens.recordingPen import RecordingPointPen

from rounding import to_cubic, area


class _Glyph:
    def __init__(self, contours):
        self.contours = contours
        self.name = 'glyph'
        self.width = 0
        self.unicodes = []
        self.anchors = []
        self.lib = {}
        self.note = None

    def drawPoints(self, pen):
        for c in self.contours:
            pen.beginPath()
            for x, y, t in c:
                pen.addPoint((x, y), segmentType=t)
            pen.endPath()


def union(contours):
    """Remove overlaps (booleanOperations); returns cubic contours as (x, y, type) lists."""
    bg = BooleanGlyph(_Glyph([to_cubic(c) for c in contours]))
    res = bg.removeOverlap()
    rec = RecordingPointPen()
    res.drawPoints(rec)
    out, cur = [], None
    for op, args, kw in rec.value:
        if op == 'beginPath':
            cur = []
        elif op == 'addPoint':
            (x, y), t = args[0], args[1] if len(args) > 1 else kw.get('segmentType')
            cur.append((float(x), float(y), t))
        elif op == 'endPath':
            out.append(cur)
    return out


def signature(c):
    return tuple(p[2] is None for p in c)


def align(contours, reference):
    """Contours reordered and each rotated so they match the reference master's, point for point.
    Matching is by point-type pattern, then by position relative to the glyph's box."""
    def norm(cs):
        xs = [p[0] for c in cs for p in c]
        ys = [p[1] for c in cs for p in c]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        w, h = max(x1 - x0, 1), max(y1 - y0, 1)
        return [[((p[0] - x0) / w, (p[1] - y0) / h) for p in c] for c in cs]
    if sorted(len(c) for c in contours) != sorted(len(c) for c in reference):
        raise ValueError(f'incompatible: {[len(c) for c in contours]} vs {[len(c) for c in reference]}')
    nc, nr = norm(contours), norm(reference)
    out = [None] * len(reference)
    used = set()
    for ri, rc in enumerate(reference):
        best = None
        for ci, cc in enumerate(contours):
            if ci in used or len(cc) != len(rc):
                continue
            sig_r = signature(rc)
            for rot in range(len(cc)):
                rotated = cc[rot:] + cc[:rot]
                if signature(rotated) != sig_r:
                    continue
                nn = nc[ci][rot:] + nc[ci][:rot]
                err = sum(math.dist(a, b) for a, b in zip(nn, nr[ri]))
                if best is None or err < best[0]:
                    best = (err, ci, rotated)
        if best is None:
            raise ValueError('no match for contour %d' % ri)
        used.add(best[1])
        # keep the reference's on-curve types (line vs curve) when they agree in shape
        out[ri] = [(x, y, rt if (t is None) == (rt is None) else t)
                   for (x, y, t), (_, _, rt) in zip(best[2], reference[ri])]
    return out


def find_crotches(contours, stem, ink, max_len=0.2):
    """Inter cuts some crotches flat: a few units of line between two straight strokes meeting at an
    acute angle (и, where the diagonal meets a stem). Allo's own letters meet in a point there (N), and
    rounding then cuts its notch. Returns [(contour, segment)] of such flats, found in the reference
    master and then removed in every master (point_crotches), so all masters keep one structure."""
    from rounding import segments, seg_length, seg_tangent_end, seg_tangent_start, signed_turn
    found = []
    for ci, c in enumerate(contours):
        segs, _ = segments(c)
        n = len(segs)
        for i, s in enumerate(segs):
            if s[0] != 'line' or n < 4 or seg_length(s) > max_len * stem:
                continue
            prev, nxt = segs[i - 1], segs[(i + 1) % n]
            if prev[0] != 'line' or nxt[0] != 'line':
                continue
            a = signed_turn(seg_tangent_end(prev), seg_tangent_start(s))
            b = signed_turn(seg_tangent_start(s), seg_tangent_start(nxt))
            tot = signed_turn(seg_tangent_end(prev), seg_tangent_start(nxt))
            if a * ink < 0 and b * ink < 0 and tot * ink < 0 and 180 - abs(tot) < 80:
                found.append((ci, i))
    return found


def point_crotches(contours, flats):
    """The flats (find_crotches) taken out, their neighbouring lines run on to where they meet."""
    from rounding import segments, from_segments, line_intersection, sub, unit
    out = [list(c) for c in contours]
    for ci in sorted({ci for ci, _ in flats}):
        segs, _ = segments(out[ci])
        for i in sorted((i for c, i in flats if c == ci), reverse=True):
            n = len(segs)
            prev, nxt = segs[i - 1], segs[(i + 1) % n]
            X = line_intersection(prev[1][0], unit(sub(prev[1][1], prev[1][0])),
                                  nxt[1][1], unit(sub(nxt[1][0], nxt[1][1])))
            segs[i - 1] = ('line', [prev[1][0], X])
            segs[(i + 1) % n] = ('line', [X, nxt[1][1]])
            del segs[i]
        out[ci] = from_segments(segs)
    return out

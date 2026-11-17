"""Allo's corner rounding, measured from its Latin masters and reapplied to new glyphs.

Allo keeps its roundness in the outlines: every rounded corner is a cubic fillet (on, off, off, on)
in all three ROND masters, so the masters interpolate. The rules, read off the Latin (see README):

* Only outer contours are rounded (those running the way the glyph's largest contour does); counters stay sharp.
* A convex corner with interior angle t gets a fillet whose ends sit d = R * clamp(1 / tan(t/2), 0.8, 2)
  from the corner, where R is the master's radius (about 0.35 x stem; read from H in each master).
* An acute concave corner (t < 80 degrees, the crotch of v, the notch of n) gets
  d = min(R / 2, R / (4 tan(t/2))); wider concave corners (the joins of H's bar) stay sharp.
* d scales with ROND: ROND 50 is the value above, ROND 100 twice it, ROND 10 a fifth.
* Handles: both one length, 1.3375 x a circular arc's for the same turn, measured on the mean distance
  from the fillet's ends to where their tangents meet ("squircle" corners).
* At ROND 100 a stroke end (a straight edge between two convex corners, turning more than 110 degrees
  across it, no longer than 2 x stem) is rounded completely: both fillets meet with circular arcs of
  one radius and the edge between them keeps zero length.
* Fillets that share a segment and do not fit on it shrink in proportion until they meet (each takes
  the smaller of its two segments' factors); both corners of a stroke end take the smaller factor; next to a
  stroke end at ROND 100 the stroke end keeps its size and the other fillet takes what is left.
* ROND 0 keeps the fillets' points: 0.0145 units on a corner between two lines (0.00725 if concave),
  zero (all four points on the corner) where a curve is involved.
* A fillet's end on a curve is found at chord distance d from the corner and the curve is split there.

Contours are lists of (x, y, type), type None for off-curve points, cubic only (see to_cubic).
"""
import math

from fontTools.misc.bezierTools import splitCubicAtT

SQUIRCLE = 0.738681 / 0.552285  # Allo's handles relative to a circle's (H, all masters)
EPS_LINE = 0.0145
EPS_CONCAVE = 0.00725
CONCAVE_MAX = 80.0
TERMINAL_TURN = 110.0
TERMINAL_STEMS = 2.0
MIN_D = 2.0


# ----------------------------------------------------------------------------------------- basics

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def mul(a, k):
    return (a[0] * k, a[1] * k)


def unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n > 1e-12 else (0.0, 0.0)


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def signed_turn(u, v):
    """Signed angle in degrees from direction u to direction v (left turn positive)."""
    return math.degrees(math.atan2(cross(u, v), dot(u, v)))


def segments(contour):
    """A closed contour as segments [(type, [p0, ..., pn])], each starting at the previous one's end.
    The contour's first on-curve point starts the first segment."""
    pts = list(contour)
    first = next(i for i, p in enumerate(pts) if p[2] is not None)
    pts = pts[first:] + pts[:first]
    segs = []
    cur = [pts[0][:2]]
    for p in pts[1:] + [pts[0]]:
        cur.append(p[:2])
        if p[2] is not None:
            kind = p[2]
            if kind == 'curve' and len(cur) == 2:
                kind = 'line'
            segs.append((kind, cur))
            cur = [p[:2]]
    return segs, first


def to_cubic(contour):
    """Quadratic segments (qcurve, any number of off-curves) as exact cubics; a 'curve' with no
    off-curves as a line, with one off-curve as the cubic of that quadratic."""
    def clean(c):
        pts = list(c)
        n = len(pts)
        for i, p in enumerate(pts):
            if p[2] == 'curve':
                offs = 0
                while pts[(i - 1 - offs) % n][2] is None and offs < n:
                    offs += 1
                if offs == 0:
                    pts[i] = (p[0], p[1], 'line')
                elif offs == 1:
                    pts[i] = (p[0], p[1], 'qcurve')
        return pts
    contour = clean(contour)
    if not any(p[2] == 'qcurve' for p in contour):
        return list(contour)
    segs, _ = segments(contour)
    out = []
    for kind, pts in segs:
        if kind != 'qcurve':
            out += [(x, y, None) for x, y in pts[1:-1]] + [(pts[-1][0], pts[-1][1], kind)]
            continue
        offs = pts[1:-1]
        ons = [pts[0]]
        for a, b in zip(offs, offs[1:]):
            ons.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        ons.append(pts[-1])
        for i, c in enumerate(offs):
            p0, p1 = ons[i], ons[i + 1]
            c1 = (p0[0] + 2 / 3 * (c[0] - p0[0]), p0[1] + 2 / 3 * (c[1] - p0[1]))
            c2 = (p1[0] + 2 / 3 * (c[0] - p1[0]), p1[1] + 2 / 3 * (c[1] - p1[1]))
            out += [(c1[0], c1[1], None), (c2[0], c2[1], None), (p1[0], p1[1], 'curve')]
    # segments() started at an on-curve point: keep that order
    return out[-1:] + out[:-1]


def from_segments(segs):
    out = []
    for kind, pts in segs:
        out += [(x, y, None) for x, y in pts[1:-1]]
        out.append((pts[-1][0], pts[-1][1], kind))
    return out[-1:] + out[:-1]  # start with the first segment's start point


def area(contour):
    """Signed area of the contour's control polygon with curves sampled (positive = counter-clockwise)."""
    segs, _ = segments(contour)
    poly = []
    for kind, pts in segs:
        if kind == 'curve':
            for k in range(8):
                t = k / 8
                poly.append(cubic_point(pts, t))
        else:
            poly.append(pts[0])
    s = 0
    for i in range(len(poly)):
        s += cross(poly[i], poly[(i + 1) % len(poly)])
    return s / 2


def cubic_point(pts, t):
    p0, p1, p2, p3 = pts
    mt = 1 - t
    return (mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
            mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1])


def seg_tangent_end(seg):
    kind, pts = seg
    if kind == 'line':
        return unit(sub(pts[1], pts[0]))
    for q in (pts[2], pts[1], pts[0]):
        if math.dist(pts[3], q) > 1e-6:
            return unit(sub(pts[3], q))
    return (0.0, 0.0)


def seg_tangent_start(seg):
    kind, pts = seg
    if kind == 'line':
        return unit(sub(pts[1], pts[0]))
    for q in (pts[1], pts[2], pts[3]):
        if math.dist(pts[0], q) > 1e-6:
            return unit(sub(q, pts[0]))
    return (0.0, 0.0)


def seg_length(seg):
    kind, pts = seg
    if kind == 'line':
        return math.dist(pts[0], pts[1])
    n = 24
    prev = pts[0]
    s = 0
    for k in range(1, n + 1):
        q = cubic_point(pts, k / n)
        s += math.dist(prev, q)
        prev = q
    return s


def t_at_chord(pts, d, from_end):
    """Parameter t on a cubic at chord distance d from its end (from_end) or its start."""
    corner = pts[3] if from_end else pts[0]

    def dist(t):
        return math.dist(cubic_point(pts, t), corner)
    # walk away from the corner until the distance reaches d
    n = 64
    prev_t = 1.0 if from_end else 0.0
    for k in range(1, n + 1):
        t = 1 - k / n if from_end else k / n
        if dist(t) >= d:
            lo, hi = (t, prev_t) if from_end else (prev_t, t)
            for _ in range(60):
                mid = (lo + hi) / 2
                if (dist(mid) >= d) == from_end:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2
        prev_t = t
    return 0.0 if from_end else 1.0



# ------------------------------------------------------------------------------------------ spurs
# Inter joins some bowls to stems with a short flat spur (b, d, p, q: stem, 20 units across, then the
# bowl). Allo keeps the spur at ROND 0 and drawn as a fillet (handles at its thirds); from ROND 50 the
# bowl's end slides onto the stem by the spur's length and the join becomes a concave notch there.

SPUR_MAX = 0.3   # x stem


def find_spurs(segs, stem, ink):
    """[(i, side)] for spur segments: i a short line; side 'out' when stem, spur, bowl follow each
    other in contour order, 'in' when bowl, spur, stem do."""
    n = len(segs)
    found = []
    for i, seg in enumerate(segs):
        if seg[0] != 'line' or n < 4 or seg_length(seg) > SPUR_MAX * stem:
            continue
        prev, nxt = segs[i - 1], segs[(i + 1) % n]
        u = seg_tangent_start(seg)
        if prev[0] == 'line' and nxt[0] == 'curve':
            side, first = 'out', signed_turn(seg_tangent_end(prev), u)
        elif prev[0] == 'curve' and nxt[0] == 'line':
            side, first = 'in', signed_turn(u, seg_tangent_start(nxt))
        else:
            continue
        total = signed_turn(seg_tangent_end(prev), seg_tangent_start(nxt))
        if first * ink < 0 and 60 <= abs(first) <= 120 and total * ink < 0 and 180 - abs(total) < CONCAVE_MAX:
            found.append((i, side))
    return found


def merge_spurs(segs, spurs):
    """Segments with every spur taken out and its bowl slid onto the stem, and {new vertex index:
    (spur start, spur end, original bowl, side)} for the vertices where the spurs were."""
    n = len(segs)
    spur_at = dict(spurs)
    new, info = [], {}
    skip = set()
    for i in range(n):
        if i in skip:
            continue
        if i in spur_at:
            side = spur_at[i]
            V0, S0 = segs[i][1][0], segs[i][1][1]
            if side == 'out':  # the next segment is the bowl: move its start from S0 to V0
                j = (i + 1) % n
                bowl = segs[j][1]
                shift = sub(V0, S0)
                moved = [V0, add(bowl[1], shift), bowl[2], bowl[3]]
                info[len(new)] = (V0, S0, bowl, side)
                new.append(('curve', moved))
                skip.add(j)
                if j == 0:  # the bowl was the first segment: drop the copy already written
                    new.pop(0)
                    info = {k - 1: v for k, v in info.items()}
            else:  # the previous segment is the bowl: move its end from V0 (spur start) to S0
                bowl = new[-1][1] if new else segs[i - 1][1]
                shift = sub(S0, V0)
                moved = [bowl[0], bowl[1], add(bowl[2], shift), S0]
                if new:
                    new[-1] = ('curve', moved)
                else:  # the bowl is the contour's last segment
                    skip.add(n - 1)
                    new.append(None)  # placeholder, filled at the end
                    tail = ('curve', moved)
                info[len(new)] = (S0, V0, bowl, side)  # the notch's corner is the spur's far end
            continue
        new.append(segs[i])
    if None in new:
        k = new.index(None)
        new[k:k + 1] = []
        new.append(tail)
        info = {(v - 1 if v > k else v): w for v, w in info.items()}
    return new, info


# ------------------------------------------------------------------------------------------- plan

def corners(contour, stem, ink=1):
    """The rounding plan for one contour, from the reference master's geometry: for each vertex
    (start of segment i), None or {'kind': 'convex'|'concave'}, and for each line segment whether
    it is a stroke end (rounded completely at ROND 100)."""
    contour = to_cubic(contour)
    segs, _ = segments(contour)
    a = area(contour)
    outer = a * ink > 0
    spurs = find_spurs(segs, stem, ink) if outer else []
    segs, spur_info = merge_spurs(segs, spurs)
    n = len(segs)
    plan = {'outer': outer, 'vertex': [None] * n, 'terminal': [False] * n, 'spurs': spurs}
    if not outer:
        return plan
    for i in range(n):
        tin = seg_tangent_end(segs[i - 1])
        tout = seg_tangent_start(segs[i])
        phi = signed_turn(tin, tout)
        if abs(phi) < 2:
            continue
        theta = 180 - abs(phi)
        if i in spur_info:
            plan['vertex'][i] = {'kind': 'concave', 'spur': True}
        elif phi * ink > 0:
            plan['vertex'][i] = {'kind': 'convex'}
        elif theta < CONCAVE_MAX:
            plan['vertex'][i] = {'kind': 'concave'}
    for i in range(n):
        j = (i + 1) % n
        va, vb = plan['vertex'][i], plan['vertex'][j]
        if segs[i][0] != 'line' or not va or not vb or va['kind'] != 'convex' or vb['kind'] != 'convex':
            continue
        tin = seg_tangent_end(segs[i - 1])
        tout = seg_tangent_start(segs[j])
        turn = abs(math.degrees(math.acos(max(-1, min(1, dot(tin, tout))))))
        if turn >= TERMINAL_TURN and seg_length(segs[i]) <= TERMINAL_STEMS * stem:
            plan['terminal'][i] = True
    return plan


def ink_sign(contours):
    """The orientation of ink in this glyph: the sign of its largest contour's area (Allo's cubic glyphs
    run counter-clockwise, its quadratic ones clockwise)."""
    areas = [area(to_cubic(c)) for c in contours] or [1]
    return 1 if max(areas, key=abs) > 0 else -1


def plan_glyph(contours, stem):
    ink = ink_sign(contours)
    return [corners(c, stem, ink) for c in contours]


# ------------------------------------------------------------------------------------------ apply

def corner_angle(segs, i):
    tin = seg_tangent_end(segs[i - 1])
    tout = seg_tangent_start(segs[i])
    return 180 - abs(signed_turn(tin, tout))


def nominal(kind, theta, R):
    half = math.radians(max(theta, 1e-3)) / 2
    if kind == 'convex':
        return R * min(max(1 / math.tan(half), 0.8), 2.0)
    return min(R / 2, R / (4 * math.tan(half)))


def handle_factor(phi_deg):
    """Handle length / tangent length of a circular arc turning phi degrees."""
    phi = math.radians(abs(phi_deg))
    if phi < 1e-6:
        return 1 / 3
    return 4 / 3 * math.tan(phi / 4) / math.tan(phi / 2)


def line_intersection(p, u, q, v):
    den = cross(u, v)
    if abs(den) < 1e-12:
        return None
    t = cross(sub(q, p), v) / den
    return add(p, mul(u, t))


def round_contour(contour, plan, R, rond, stem=None):
    segs, first = segments(to_cubic(contour))
    if not plan['outer'] or not any(plan['vertex']):
        return [(x, y, t) for x, y, t in to_cubic(contour)]
    segs, spur_info = merge_spurs(segs, plan.get('spurs', []))
    n = len(segs)
    assert n == len(plan['vertex']), 'contour does not match its plan'
    s = rond / 50.0
    d = [0.0] * n        # tangent distance at vertex i (start of segment i)
    circle = [False] * n
    for i, v in enumerate(plan['vertex']):
        if not v:
            continue
        both_lines = segs[i - 1][0] == 'line' and segs[i][0] == 'line'
        if rond == 0:
            d[i] = (EPS_LINE if v['kind'] == 'convex' else EPS_CONCAVE) if both_lines else 0.0
        else:
            d[i] = nominal(v['kind'], corner_angle(segs, i), R) * s
    # fillets sharing a segment must fit on it: both shrink in proportion until they meet
    def fits(i):
        j = (i + 1) % n
        return seg_length(segs[i]), j
    factor = [1.0] * n   # per segment, from the nominal sizes; each fillet takes the smaller of its two
    for i in range(n):
        L, j = fits(i)
        need = d[i] + d[j]
        if plan['vertex'][i] and plan['vertex'][j] and need > L > 0:
            factor[i] = L / need
    f = [min(factor[i - 1], factor[i]) for i in range(n)]
    # the two corners of a stroke end shrink alike: both take the smaller factor
    for i in range(n):
        if plan['terminal'][i]:
            j = (i + 1) % n
            f[i] = f[j] = min(f[i], f[j])
    d = [d[i] * f[i] for i in range(n)]
    # at ROND 100 a stroke end is rounded completely (circular arcs of one radius that meet), and the
    # fillet across from it on each side takes what is left (at least MIN_D)
    if rond >= 100:
        for i in range(n):
            if plan['terminal'][i]:
                j = (i + 1) % n
                L = seg_length(segs[i])
                ta = math.radians(corner_angle(segs, i)) / 2
                tb = math.radians(corner_angle(segs, j)) / 2
                r = L / (1 / math.tan(ta) + 1 / math.tan(tb))
                d[i], d[j] = r / math.tan(ta), r / math.tan(tb)
                circle[i] = circle[j] = True
        for i in range(n):
            L, j = fits(i)
            if plan['terminal'][i] or not (plan['vertex'][i] and plan['vertex'][j]) or circle[i] == circle[j]:
                continue
            fixed, free = (i, j) if circle[i] else (j, i)
            if d[fixed] + d[free] > L:
                d[free] = max(MIN_D, L - d[fixed])
                d[fixed] = min(d[fixed], L - d[free])
    # trim every segment
    trimmed = []
    for i, (kind, pts) in enumerate(segs):
        j = (i + 1) % n
        a, b = d[i] if plan['vertex'][i] else 0.0, d[j] if plan['vertex'][j] else 0.0
        if kind == 'line':
            u = unit(sub(pts[1], pts[0]))
            trimmed.append(('line', [add(pts[0], mul(u, a)), sub(pts[1], mul(u, b))]))
        else:
            t0 = t_at_chord(pts, a, from_end=False) if a > 0 else 0.0
            t1 = t_at_chord(pts, b, from_end=True) if b > 0 else 1.0
            c = pts
            if t1 < 1.0:
                c = list(splitCubicAtT(*c, t1)[0])
                t0 = t0 / t1 if t1 > 0 else 0.0
            if t0 > 0.0:
                c = list(splitCubicAtT(*c, t0)[1])
            trimmed.append(('curve', [tuple(p) for p in c]))
    if rond == 0:  # spurs stay as Inter drew them, written as fillets (handles at their thirds)
        for v, (V0, S0, bowl, side) in spur_info.items():
            if side == 'out':
                trimmed[v] = ('curve', [tuple(p) for p in bowl])
            else:
                trimmed[v - 1] = ('curve', [tuple(p) for p in bowl])
    # fillets
    out = []
    for i in range(n):
        if rond == 0 and i in spur_info:
            V0, S0, bowl, side = spur_info[i]
            a, b = (V0, S0) if side == 'out' else (S0, V0)
            if side == 'in':
                a, b = bowl[3], spur_info[i][0]
            third = mul(sub(b, a), 1 / 3)
            out.append(('fillet', [a, add(a, third), sub(b, third), b]))
            out.append(trimmed[i])
            continue
        if plan['vertex'][i]:
            prev = trimmed[i - 1]
            nxt = trimmed[i]
            A, B = prev[1][-1], nxt[1][0]
            V = segs[i][1][0]
            # a trimmed line keeps its direction even when the fillets consume it entirely
            tA = seg_tangent_end(prev) if prev[0] == 'curve' and math.dist(A, V) > 1e-9 else seg_tangent_end(segs[i - 1])
            tB = seg_tangent_start(nxt) if nxt[0] == 'curve' and math.dist(B, V) > 1e-9 else seg_tangent_start(segs[i])
            X = line_intersection(A, tA, B, tB) or V
            dA, dB = math.dist(A, X), math.dist(B, X)
            # both handles one length: the arc factor times the mean distance to the tangents' meeting point
            h = handle_factor(signed_turn(tA, tB)) * (1.0 if circle[i] else SQUIRCLE) * (dA + dB) / 2
            h1 = add(A, mul(tA, h))
            h2 = sub(B, mul(tB, h))
            out.append(('fillet', [A, h1, h2, B]))
        out.append(trimmed[i])
    # assemble points: Allo writes a fillet on the contour's first vertex with its start point last
    pts = []
    for kind, p in out:
        if kind == 'fillet':
            pts.append((p[0][0], p[0][1], 'end-of-previous'))
            pts += [(p[1][0], p[1][1], None), (p[2][0], p[2][1], None), (p[3][0], p[3][1], 'curve')]
        else:
            pts += [(x, y, None) for x, y in p[1:-1]]
            pts.append((p[-1][0], p[-1][1], kind))
    # the fillet start point duplicates the end of the previous segment: merge them
    merged = []
    for p in pts:
        if p[2] == 'end-of-previous':
            continue
        merged.append(p)
    # merged starts after vertex 0; vertex 0 itself (or its fillet end B) is the last point written
    if plan['vertex'][0]:
        # out[0] is the fillet at vertex 0: its A is the end of the last segment (last point);
        # Allo lists the fillet's off-curves first: rotate so the list starts with them
        return merged
    return merged[-1:] + merged[:-1]


def round_glyph(contours, plans, R, rond, stem=None):
    return [round_contour(c, p, R, rond, stem) for c, p in zip(contours, plans)]


# ---------------------------------------------------------------------------------------- unround

def unround(contour, tol=0.05):
    """Allo's ROND 0 contour as a sharp one: every fillet whose ends are within tol collapses into its corner."""
    pts = list(contour)
    n = len(pts)
    drop, replace = set(), {}
    i = 0
    while i < n:
        a, b, c, e = (pts[(i + k) % n] for k in range(4))
        if a[2] is not None and b[2] is None and c[2] is None and e[2] == 'curve' and \
                math.dist(a[:2], e[:2]) < tol and math.dist(a[:2], b[:2]) < tol and math.dist(a[:2], c[:2]) < tol:
            prev = pts[(i - 1) % n]
            nxt = pts[(i + 4) % n]
            V = a[:2]
            if a[2] == 'line' and nxt[2] == 'line':
                X = line_intersection(prev[:2], unit(sub(a[:2], prev[:2])), nxt[:2], unit(sub(e[:2], nxt[:2])))
                if X and math.dist(X, a[:2]) < tol * 2:
                    V = X
            replace[i] = (V[0], V[1], a[2])
            drop.update({(i + 1) % n, (i + 2) % n, (i + 3) % n})
            i += 4
            continue
        i += 1
    out = [replace.get(i, p) for i, p in enumerate(pts) if i not in drop]
    return out


def straighten_spurs(contour, max_len):
    """Allo's ROND 0 spurs (straight cubics with handles at their thirds, shorter than max_len) as the
    lines Inter drew."""
    pts = list(contour)
    n = len(pts)
    out = []
    i = 0
    drop = set()
    for i in range(n):
        a, b, c, e = (pts[(i + k) % n] for k in range(4))
        if a[2] is None or b[2] is not None or c[2] is not None or e[2] != 'curve':
            continue
        L = math.dist(a[:2], e[:2])
        if not 0.5 < L <= max_len:
            continue
        third = ((e[0] - a[0]) / 3, (e[1] - a[1]) / 3)
        if math.dist(b[:2], (a[0] + third[0], a[1] + third[1])) < 0.05 and \
                math.dist(c[:2], (e[0] - third[0], e[1] - third[1])) < 0.05:
            drop.update({(i + 1) % n, (i + 2) % n})
            pts[(i + 3) % n] = (e[0], e[1], 'line')
    return [p for k, p in enumerate(pts) if k not in drop]

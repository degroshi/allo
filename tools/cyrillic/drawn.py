"""Currency signs Inter doesn't draw (֏ ৳ ៛), built from Inter's own parts at any (opsz, wght).

Each function returns a glyph as Inter.decomposed_at does ({'width', 'contours', 'anchors'}, in Inter's
design space), so the build treats it as one of Inter's: Allo's weight, spacing and rounding follow, at
every master, and the parts keep Inter's strokes and curves at that weight.

* ֏ (Armenian dram): Inter's U turned over, its left leg cut short, and ₴'s two bars across the right leg.
* ৳ (Bengali taka): f's stem and hook turned round, a bar where f's crossbar is, and a bowl that is three
  quarters of o, open at the top left.
* ៛ (Khmer riel): the loop of ɂ (the small glottal stop), squashed and turned round, on a stem that ends in
  J's hook, with a bar across it.

The bars are as thick as ₴'s.
"""
from inter import reverse_contour

CAP = 1490


def bbox(contours):
    xs = [p[0] for c in contours for p in c]
    ys = [p[1] for c in contours for p in c]
    return min(xs), min(ys), max(xs), max(ys)


def rect(x0, y0, x1, y1):
    """A rectangle, counter-clockwise as Inter's outer contours are."""
    return [(x0, y0, 'line'), (x1, y0, 'line'), (x1, y1, 'line'), (x0, y1, 'line')]


def mirrored(contour, axis):
    """The contour reflected about x = axis, its direction kept."""
    return reverse_contour([(2 * axis - x, y, t) for x, y, t in contour])


def bars(inter, loc):
    """₴'s two bars: (thickness, gap between them, right side bearing at their ends)."""
    g = inter.decomposed_at('hryvnia', loc)
    rects = sorted((bbox([c]) for c in g['contours'] if len(c) == 4), key=lambda b: b[1])
    (_, l0, x1, l1), (_, u0, _, u1) = rects
    return l1 - l0, u0 - l1, g['width'] - x1


def f_parts(inter, loc):
    """f's stem and hook contour, and (stem left, stem right, crossbar right, crossbar top)."""
    f = inter.decomposed_at('f', loc)
    bar = next(c for c in f['contours'] if len(c) == 4)
    stem = next(c for c in f['contours'] if len(c) != 4)
    _, _, bx1, by1 = bbox([bar])
    xs = sorted({round(x, 3) for x, y, t in stem if t is not None and y <= 1})
    return stem, (xs[0], xs[-1], bx1, by1)


GAP = 0.06 * CAP  # between a bar and the bowl or loop under it


def dram(inter, loc):
    u = inter.decomposed_at('U', loc)
    (c,) = u['contours']
    w = u['width']
    # turned over about the middle of the cap height: the bowl becomes the arch, the legs stand on the baseline
    arch = [(w - x, CAP - y, t) for x, y, t in c]
    feet = sorted((i for i, p in enumerate(arch) if abs(p[1]) < 1), key=lambda i: arch[i][0])
    assert len(feet) == 4, feet
    lo, li, ri, ro = (arch[i][0] for i in feet)  # left leg outer/inner, right leg inner/outer
    t, gap, rsb = bars(inter, loc)
    band = 2 * t + gap
    y0 = 0.42 * CAP - band / 2
    lower, upper = (y0, y0 + t), (y0 + t + gap, y0 + band)
    for i in feet[:2]:  # the left leg stops level with the upper bar's underside
        x, _, typ = arch[i]
        arch[i] = (x, upper[0], typ)
    x_left = li + 0.4 * (ri - li)
    x_right = ro + 0.75 * (ro - ri)
    parts = [arch, rect(x_left, lower[0], x_right, lower[1]), rect(x_left, upper[0], x_right, upper[1])]
    return {'width': x_right + rsb, 'contours': parts, 'anchors': {}}


def taka(inter, loc):
    o = inter.decomposed_at('o', loc)
    outer, inner = o['contours']
    stem, (f_sl, f_sr, f_br, f_bt) = f_parts(inter, loc)
    stem = [list(p) for p in stem]
    t_bar, _, h_rsb = bars(inter, loc)
    o_top = bbox(inter.decomposed_at('O', loc)['contours'])[3]

    # o's extremes: outer B R T L at 0 3 6 9 (counter-clockwise), inner B L T R at 0 3 6 9 (clockwise)
    ox0, oy0, ox1, oy1 = bbox([outer])
    ix0, iy0, ix1, iy1 = bbox([inner])
    tl, tr, tb, tt = ix0 - ox0, ox1 - ix1, iy0 - oy0, oy1 - iy1
    # the bar where f's crossbar is, as thick as ₴'s bars; the bowl's top at 0.6 of the cap height, or
    # lower when the bar comes down (heavy weights); its width follows its height, but its counter
    # keeps at least 0.7 of o's
    bar_bottom = f_bt - t_bar
    top = min(0.6 * CAP + (o_top - CAP), bar_bottom - GAP)
    width = max(0.92 * (top - oy0), tl + tr + 0.7 * (ix1 - ix0))
    nb = (0, oy0, width, top)
    ni = (nb[0] + tl, nb[1] + tb, nb[2] - tr, nb[3] - tt)

    def fit(p, src, dst):
        x, y, t = p
        return (dst[0] + (x - src[0]) * (dst[2] - dst[0]) / (src[2] - src[0]),
                dst[1] + (y - src[1]) * (dst[3] - dst[1]) / (src[3] - src[1]), t)
    out = [fit(p, (ox0, oy0, ox1, oy1), nb) for p in outer]
    inn = [fit(p, (ix0, iy0, ix1, iy1), ni) for p in inner]
    y_mid = out[9][1]
    inn[3] = (inn[3][0], y_mid, inn[3][2])
    L_o, L_i = out[9], inn[3]

    # f's stem and hook, turned round so the hook points left, its left edge on the bowl's left and as
    # wide as the bowl's side
    k = tl / (f_sr - f_sl)
    for p in stem:
        if p[1] <= 1:
            p[1] = y_mid
        p[0] = L_o[0] + (f_sr - p[0]) * k
    stem = reverse_contour([tuple(p) for p in stem])  # turned round: back to counter-clockwise
    # splice: bowl from its left outer extreme round to its left inner extreme, then the stem up its right
    # edge, round the hook and down its left edge back to the start
    start = next(i for i, p in enumerate(stem) if abs(p[0] - L_i[0]) < 0.01 and abs(p[1] - y_mid) < 0.01)
    stem = stem[start:] + stem[:start]
    assert abs(stem[-1][0] - L_o[0]) < 0.01 and abs(stem[-1][1] - y_mid) < 0.01, stem[-1]
    off = lambda p: (p[0], p[1], None)  # noqa: E731
    bowl = ([(L_o[0], y_mid, 'line'), off(out[10]), off(out[11]), out[0], off(out[1]), off(out[2]), out[3],
             off(out[4]), off(out[5]), out[6], (inn[6][0], inn[6][1], 'line'), off(inn[7]), off(inn[8]), inn[9],
             off(inn[10]), off(inn[11]), inn[0], off(inn[1]), off(inn[2]), (L_i[0], y_mid, 'curve')] +
            stem[1:-1])
    # the bar: from as far left of the stem as f's crossbar reaches right of it, to the bowl's right
    bar = rect(L_o[0] - (f_br - f_sr) * k, bar_bottom, nb[2], f_bt)
    shift = h_rsb - bbox([bowl, bar])[0]
    parts = [[(x + shift, y, t) for x, y, t in c] for c in (bowl, bar)]
    return {'width': bbox(parts)[2] + h_rsb, 'contours': parts, 'anchors': {}}


def riel(inter, loc):
    g = inter.decomposed_at('uni0242', loc)
    loop = next(c for c in g['contours'] if len(c) != 4)
    sx0, _, sx1, _ = bbox([next(c for c in g['contours'] if len(c) == 4)])
    sc, ws = (sx0 + sx1) / 2, sx1 - sx0
    lsb_loop = bbox([loop])[0]
    o_top = bbox(inter.decomposed_at('O', loc)['contours'])[3]
    # ɂ's loop runs: the terminal (0, 1), the inner side (1-11) down to the stub, the outer side (12-21) back.
    # Squashed to 0.75 of its height (its counter keeps at least 0.6 of its own), each side on its own so
    # the strokes keep their thickness, its top
    # at the cap height's overshoot (O's), then turned round so the terminal is on the right.
    outer_i = [0] + list(range(12, len(loop)))
    inner_i = list(range(1, 12))
    oy0, oy1 = min(loop[i][1] for i in outer_i), max(loop[i][1] for i in outer_i)
    iy0, iy1 = min(loop[i][1] for i in inner_i), max(loop[i][1] for i in inner_i)
    tb, tt = iy0 - oy0, oy1 - iy1
    h = max(0.75 * (oy1 - oy0), tb + tt + 0.6 * (iy1 - iy0))
    ny0 = o_top - h
    pts = []
    for i, (x, y, t) in enumerate(loop):
        if i in inner_i:
            y = ny0 + tb + (y - iy0) * (h - tb - tt) / (iy1 - iy0)
        else:
            y = ny0 + (y - oy0) * h / (oy1 - oy0)
        pts.append((x, y, t))
    ty = (pts[0][1] + pts[1][1]) / 2  # the terminal stays a level cut
    pts[0], pts[1] = (pts[0][0], ty, pts[0][2]), (pts[1][0], ty, pts[1][2])
    stem_top = pts[11][1]  # the stub's top: ɂ's stem rises to it
    loop = mirrored(pts, sc)

    j = inter.decomposed_at('J', loc)
    (jc,) = j['contours']
    jc = [list(p) for p in jc]
    jx0 = bbox([jc])[0]
    tops = sorted((i for i, p in enumerate(jc) if p[1] > CAP - 1), key=lambda i: jc[i][0])
    assert len(tops) == 2, tops
    sl, sr = jc[tops[0]][0], jc[tops[1]][0]
    # J's hook, 0.72 as wide (its stroke kept; its opening at least 0.6 of J's), on a stem as wide as ɂ's,
    # centred under the loop
    # J runs: bottom, outer right, stem top, the inner side down and round to the terminal, the outer left
    terminal = min(i for i in range(tops[0], len(jc)) if abs(jc[i][0] - jx0) < 0.01)
    inner = set(range(tops[0], terminal))
    inner_left = min(jc[i][0] for i in inner)
    d_i = max((sl - jx0) * 0.72 - (inner_left - jx0), 0.6 * (sl - inner_left))
    d_o = d_i + (inner_left - jx0)
    for i, p in enumerate(jc):
        if p[0] < sl - 0.01:
            p[0] = sl - (sl - p[0]) * ((d_i / (sl - inner_left)) if i in inner else (d_o / (sl - jx0)))
    dx = sc + ws / 2 - sr
    for i, p in enumerate(jc):
        if i in inner and abs(p[0] - sl) < 0.01:
            p[0] = sc - ws / 2 - dx
        p[0] += dx
        if i in tops:
            p[1] = stem_top
    jc = [tuple(p) for p in jc]

    # ₴'s bar across the stem, under the loop; on the left it stops short of the hook's terminal
    t_bar = bars(inter, loc)[0]
    bar_top = bbox([loop])[1] - GAP
    e = 0.85 * ws
    bar = rect(sc - ws / 2 - min(e, d_i - GAP / 2), bar_top - t_bar, sc + ws / 2 + e, bar_top)
    parts = [loop, jc, bar]
    shift = jx0 - bbox(parts)[0]
    parts = [[(x + shift, y, t) for x, y, t in c] for c in parts]
    return {'width': bbox(parts)[2] + lsb_loop, 'contours': parts, 'anchors': {}}

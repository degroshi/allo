"""Kerning for Allo's Cyrillic, from Inter's.

Allo's kerning groups are Inter's, under the same names, and its pair values are Inter's (Allo's are
0.99 of Inter's, measured on the pairs they share, at every master). So:

* each Cyrillic glyph joins the groups Inter puts it in (Г's right side kerns as T's, И's as H's);
  the Cyrillic-only groups Inter has (Elcyrillic, Decyrillic, ...) are added; where Inter gives a glyph
  no group, it takes the group its shape shares with a Latin letter (CYR_GROUPS);
* pairs between groups Allo already has keep Allo's values, and now reach the Cyrillic too (Го kerns
  as To);
* Inter's pairs that involve a Cyrillic glyph or a Cyrillic-only group are added, interpolated at each
  master's location in Inter and scaled by that master's Allo/Inter ratio.
"""
import re
import statistics

from fontTools.varLib.models import normalizeLocation

from inter import AXES

OURS = re.compile(r'^(uni04[0-9A-F]{2}(\..+)?|tenge|lari)$')
# where Inter gives a glyph no group: (left side group, right side group) by shape
CYR_GROUPS = {
    'uni0427': ('U', None),       # Ч: its left arm comes down like U's
    'uni042F': (None, 'H'),       # Я: R turned round, a stem on the right
    'uni040E': ('V', 'Y'),        # Ў: as У
    'uni0492': ('B', None),       # Ғ: as Г, its right side keeps Inter's T
    'uni04D8': ('C', 'D'),        # Ә: round both sides, as O
}
ALTERNATES = {'uni0406.1': 'I.1', 'uni0407.1': 'Idieresis.1', 'uni0430.1': 'a.1'}


def inter_names(inter, recipes):
    """Inter's glyph name -> ours, for the glyphs we have (by Unicode)."""
    by_cp = {spec['uni']: name for name, spec in recipes.items() if spec.get('uni')}
    out = {}
    for g in inter.font.glyphs:
        for u in g.unicodes or []:
            if int(u, 16) in by_cp:
                out[g.name] = by_cp[int(u, 16)]
    return out


def group_plan(inter, recipes, latin_groups):
    """{group name: [our glyphs to add]} for both sides."""
    names = inter_names(inter, recipes)
    ours = {v: k for k, v in names.items()}
    add = {}
    for name, spec in recipes.items():
        if not spec.get('uni'):
            continue
        g = inter.font.glyphs[ours[name]] if name in ours else None
        left, right = (g.leftKerningGroup, g.rightKerningGroup) if g else (None, None)
        fl, fr = CYR_GROUPS.get(name, (None, None))
        left, right = left or fl, right or fr
        if right:
            add.setdefault('public.kern1.' + right, []).append(name)
        if left:
            add.setdefault('public.kern2.' + left, []).append(name)
    for alt, latin in ALTERNATES.items():
        for group, members in latin_groups.items():
            if latin in members:
                add.setdefault(group, []).append(alt)
    return add


def apply_groups(font, plan):
    groups = font.groups
    for group in list(groups):  # an earlier run's members go first
        members = [n for n in groups[group] if not OURS.match(n)]
        if members:
            groups[group] = members
        else:
            del groups[group]
    for group, members in plan.items():
        groups[group] = list(groups.get(group, [])) + [m for m in members if m not in groups.get(group, [])]


def inter_pairs(inter, loc):
    """Inter's kerning at a location, as {(left, right): value} with UFO group names."""
    def key(k):
        if k.startswith('@MMK_L_'):
            return 'public.kern1.' + k[7:]
        if k.startswith('@MMK_R_'):
            return 'public.kern2.' + k[7:]
        return k
    per = []
    for mid in inter.master_ids:
        per.append({(key(l), key(r)): v for l, rr in inter.font.kerningLTR.get(mid, {}).items() for r, v in rr.items()})
    scalars = inter.model.getScalars(normalizeLocation(loc, AXES))
    out = {}
    for p in set().union(*per):
        out[p] = inter.model.interpolateFromMastersAndScalars([d.get(p, 0) for d in per], scalars)
    return out


def cyrillic_pairs(inter, recipes, loc, font, cyrillic_groups):
    """Inter's pairs involving the Cyrillic, in Allo's names and at Allo's scale for this master."""
    names = inter_names(inter, recipes)
    ik = inter_pairs(inter, loc)
    allo = {p: v for p, v in font.kerning.items() if not any(OURS.match(k) or k in cyrillic_groups for k in p)}
    shared = [(allo[p], v) for p, v in ik.items() if p in allo and abs(v) >= 20]
    ratio = statistics.median(a / b for a, b in shared) if shared else 1.0
    known = set(font.keys()) | set(font.groups)

    def ours(k):
        if k.startswith('public.kern'):
            return k
        return names.get(k, k)

    out = {}
    for (l, r), v in ik.items():
        L, Rk = ours(l), ours(r)
        involved = any(OURS.match(k) or k in cyrillic_groups for k in (L, Rk))
        if not involved or L not in known or Rk not in known:
            continue
        value = round(v * ratio)
        if value:
            out[(L, Rk)] = value
    return out, ratio


def cyrillic_only(font):
    """Groups whose members are all Cyrillic (after apply_groups)."""
    return {g for g, members in font.groups.items() if members and all(OURS.match(m) for m in members)}


def apply_pairs(font, pairs, cyrillic_groups):
    kerning = font.kerning
    for p in list(kerning):
        if any(OURS.match(k) or k in cyrillic_groups for k in p):
            del kerning[p]
    for p, v in pairs.items():
        kerning[p] = v

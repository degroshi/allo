# Cyrillic for Allo: how it is made

These scripts add Cyrillic to Allo's UFO masters. They are not needed to build the fonts (`build.py`
compiles the sources as they are); they record how the Cyrillic outlines were made, so they can be
remade or extended the same way.

Scope: Ukrainian, Russian, Belarusian (Ў ў) and Kazakh letters, Ѕ ѕ Ј ј, ₸ and ₾.

## Method

Allo began from Inter, and its Latin is still Inter's in every master with three systematic changes,
measured here master by master:

1. **Spacing.** Allo's sidebearings are about 9–10 units tighter per side at opsz 14, wght 400 (more at
   opsz 32). Each Cyrillic glyph takes Inter's sidebearings plus the change Allo made to its Latin
   reference letter on that side (П, Ш, Ц: H; п, и, ш: n; Ф: O; ...).
2. **Weight.** Allo's stems are within 1% of Inter's at the same nominal weight. The Cyrillic is
   interpolated from Inter at the weight whose H and n stems match each Allo master (opsz 14, wght
   400 reads Inter at 395.7).
3. **Roundness.** Corners are rounded in the outlines, the same way in every glyph. `rounding.py`
   reimplements that rounding. It was read off Allo's Latin, and `validate_rounding.py` checks it
   against the Latin.

Allo also redrew a few letters, and the Cyrillic follows those changes: y has a straight tail (so У
does too), and v, y, M, N and their kin meet in a point where Inter cuts its crotches flat (so И, и
do too).

Each Cyrillic glyph is made one of four ways:

| kind | glyphs | how |
|---|---|---|
| component | А В Е З І Ј М Н О Р С Т Х Ѕ Ү а е і ј о р с у х ѕ һ, Ё ё Ї ї Й й Ў ў Ғ ғ Ұ ұ | Allo's own glyphs as components, plus marks on anchors: they match the Latin exactly and follow its changes |
| turned | И Я Һ ә | Allo's N and R mirrored, Ч and e turned over, with their rounding |
| Allo + bar | Є є Ө ө Ю ю, Э э | components of Allo's C c O o I ı plus a bar glyph (`uni0404.bar`, ...), overlapping as Allo's dcroat and Tbar do; Э and э turn C and c round, so they are outlines |
| Inter | the rest | Inter's outline, overlaps removed, spaced as above, rounded by `rounding.py` |

All the ROND masters of a glyph come from one sharp outline and one corner plan, which is made in
the opsz 14, wght 400 master. So the masters interpolate. opsz 9 is opsz 14 moved 17 units each side
(release.json "smallShift"), as for the Latin, and glyphs whose rounding trims curves also get the ROND
10 and 30 layers at wght 580 and 900.

A few glyphs keep overlapping contours, because removing the overlap gives different structures in
different masters: Ф ф я Э э. They carry `public.truetype.overlap`, so rasterisers that look for the
flag treat the overlap properly. A bar's ends inside the letter it crosses are not rounded, so no
nick shows where it leaves the stroke.

## Rounding rules (`rounding.py`)

Read off the Latin in every master. R is the master's radius: how far ROND 50 moves the fillet ends
of H's corners (64.5 at opsz 14, wght 400; about 0.35 × stem).

- Only outer contours are rounded; counters stay sharp.
- Convex corner of interior angle θ: the fillet's ends lie d = R · clamp(1/tan(θ/2), 0.8, 2) from the
  corner. An acute concave corner (θ < 80°) gets min(R/2, R/(4 tan(θ/2))); wider ones stay sharp.
- d scales with ROND: ROND 50 as above, 100 twice that, 10 and 30 a fifth and three fifths.
- Both handles of a fillet have one length: 1.3375 × a circular arc's for the same turn, on the mean
  distance from the fillet's ends to where their tangents meet.
- At ROND 100 a stroke end (an edge between two convex corners, turning more than 110° across it, no
  longer than 2 × stem) is rounded completely: circular arcs that meet.
- Fillets that share a segment and don't fit on it shrink in proportion; both corners of a stroke end
  shrink alike; next to a full stroke end at ROND 100 the other fillet takes what is left.
- Where Inter joins a bowl to a stem with a short flat spur (b, d, p, q), ROND 0 keeps the spur and
  ROND 50 and up replace it with a concave notch at the stem.
- ROND 0 keeps every fillet's points (0.0145 units between two lines, none where a curve meets).

`validate_rounding.py 14 400` unrounds each Latin glyph's ROND 0 outline, rounds it again, and
compares the result with Allo's ROND 0, 50 and 100 masters. In most letters every point matches to
within half a unit. Where it doesn't, the difference is one of these:

- a zero-size fillet that Allo keeps at a corner it leaves sharp (K, N, R);
- the hooked terminals of J and ȷ;
- some joins at Black, which Allo also corrects with its ROND 10 and 30 layers.

## Running

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt glyphsLib
git clone --depth 1 --branch v4.1 --filter=blob:none --sparse https://github.com/rsms/inter ../inter-src
git -C ../inter-src sparse-checkout set --no-cone '/src/*.glyphspackage/'
.venv/bin/python tools/cyrillic/build_cyrillic.py                # every master
.venv/bin/python tools/cyrillic/build_cyrillic.py --masters 14,400,50 --root /tmp/copy   # a trial on a copy
.venv/bin/python tools/cyrillic/validate_rounding.py 14 400
.venv/bin/python tools/cyrillic/specimen.py out.html --font "Regular=fonts/variable/AlloVariable.ttf@'wght' 400"
```

`INTER_SRC` points elsewhere if Inter's sources live somewhere else.

"""Allo's features.fea with the Cyrillic in it (every master and static has the same file).

* languagesystem cyrl dflt, so the features reach Cyrillic text;
* ccmp: і and ј lose their dot before a mark, as i and j do;
* calt: Cyrillic capitals count as capitals (punctuation and signs lift beside them), Cyrillic letters
  count as letters where the lifting rules ask for them, and ₸ ₾ as currency;
* ss01 single-storey а, ss02 and cv04 serifed І and Ї, as for a and I.
Run again on an edited file, it removes what it added before adding it again.
"""
import re

OURS = re.compile(r'^(uni04[0-9A-F]{2}|tenge|lari|tugrik|Sigma|manat|cedi|coloncurrency|guarani|kip|rupee|Xi|'
                  r'dram|taka|riel)(\..+)?$')
MARKER = '# Cyrillic'


def strip_ours(names):
    return [n for n in names if not OURS.match(n)]


def edit_class(fea, name, add):
    m = re.search(r'(@' + re.escape(name) + r' = \[)([^\]]*)(\];)', fea)
    if not m:
        raise ValueError(f'no class @{name}')
    names = strip_ours(m.group(2).split()) + add
    return fea[:m.start()] + m.group(1) + ' '.join(names) + m.group(3) + fea[m.end():]


def update(fea, caps, letters, lower, currency):
    # scripts
    fea = re.sub(r'\nlanguagesystem cyrl dflt;', '', fea)
    fea = fea.replace('languagesystem latn dflt;', 'languagesystem latn dflt;\nlanguagesystem cyrl dflt;', 1)
    # ccmp: і and ј lose their dots before marks
    fea = re.sub(r'sub \[i j[^\]]*\]\' (\[[^\]]+\]) by \[idotless jdotless[^\]]*\];',
                 r"sub [i j uni0456 uni0458]' \1 by [idotless jdotless idotless jdotless];", fea)
    # classes
    fea = edit_class(fea, 'CAPS', caps)
    fea = edit_class(fea, 'NOT_SPACE', letters + currency)
    fea = edit_class(fea, 'NOT_BRACKET', letters + currency)
    # the lowercase that keeps + and - down before figures, and the currency they lift before
    def lowers(m):
        names = strip_ours(m.group(1).split())
        return 'ignore sub [' + ' '.join(names + lower) + "] [plus minus]' [" + \
            ' '.join(strip_ours(m.group(2).split()) + currency) + '];'
    fea = re.sub(r"ignore sub \[([^\]]*)\] \[plus minus\]' \[([^\]]*)\];", lowers, fea)
    fea = re.sub(r"sub \[plus minus\]' \[([^\]]*)\] by \[plus\.case minus\.case\];",
                 lambda m: "sub [plus minus]' [" + ' '.join(strip_ours(m.group(1).split()) + currency) +
                 '] by [plus.case minus.case];', fea)
    # alternates
    fea = re.sub(r'\n  sub uni04[0-9A-F]{2} by uni04[0-9A-F]{2}\.1;', '', fea)
    fea = fea.replace('  sub atilde by atilde.1;\n', '  sub atilde by atilde.1;\n  sub uni0430 by uni0430.1;\n')
    for feat in ('ss02', 'cv04'):
        fea = re.sub(r'(feature ' + feat + r' \{.*?)(  sub Itilde by Itilde\.1;\n)',
                     lambda m: m.group(1) + m.group(2) + '  sub uni0406 by uni0406.1;\n  sub uni0407 by uni0407.1;\n',
                     fea, count=1, flags=re.S)
    return fea


def arrows_to_dlig(fea):
    """Degroshi: typed text is never rewritten, so the typed arrows (-> => <- ...) move from calt,
    which is on by default, to dlig, which is opt-in. The lifting lookups stay in calt."""
    m = re.search(r'\n  lookup arrows \{.*?\} arrows;\n', fea, flags=re.S)
    if not m or 'feature dlig' in fea:
        return fea
    lookup = m.group(0)
    fea = fea[:m.start()] + '\n' + fea[m.end():]
    end = fea.index('} calt;\n') + len('} calt;\n')
    return fea[:end] + '\nfeature dlig {' + lookup + '} dlig;\n' + fea[end:]

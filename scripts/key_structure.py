"""K1: keyword/shift structure in the solved Z408 and Z340 keys (pre-registered tests T1-T3).

  python scripts/key_structure.py --make-table   # step 1: results/key_structure/glyph_table.json (descriptions only)
  python scripts/key_structure.py                # step 2: results/key_structure/results.json

Plan: results/key_structure/PLAN.md (hashes in PLAN.sha256). Glyph classes never read the symbol's decoded letter.
"""
import json, os, re, sys, hashlib
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(ROOT, 'results', 'key_structure')
D = os.path.join(ROOT, 'data', 'ciphers') + os.sep
N = 100000
SEED = 20261124
A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


# ---- step 1: glyph table (description text only; never reads 'letter') ----
# B1's fixed judgments for glyphs whose description is not "capital letter X" (copied from B1/census.py letter_like)
B1 = {'t': ('T', 'rotated/upside-down'), '=': ('K', 'rotated/upside-down'), '^': ('V', 'rotated/upside-down'),
      '|': ('I', 'normal'), '!': ('I', 'normal'), ':': ('I', 'normal'), ';': ('I', 'normal'), '&': ('P', 'normal')}
def classify(a, desc):
    if a in B1: return B1[a]
    m = re.search(r'mirror-reversed.*capital ([A-Z])\b', desc)
    if m: return (m.group(1), 'reversed')
    m = re.match(r'(?:serifed )?capital letter ([A-Z]) in normal orientation', desc)
    if m: return (m.group(1), 'normal')
    return (None, 'other')

def make_glyph_table():
    out = {}
    for c in ['z408', 'z340']:
        d = json.load(open(D + c + '.json'))
        out[c] = {}
        for s in d['symbols']:
            g, t = classify(s['ascii'], s['description'])
            out[c][s['ascii']] = {'glyph_letter': g, 'transform': t}
    json.dump(out, open(os.path.join(H, 'glyph_table.json'), 'w'), indent=1, sort_keys=True)
    return out

def lnds(seq):
    """Longest non-decreasing subsequence length (patience sorting, bisect_right)."""
    from bisect import bisect_right
    t = []
    for x in seq:
        i = bisect_right(t, x)
        if i == len(t): t.append(x)
        else: t[i] = x
    return len(t)

def stat_t1(glyph, enc):
    return int(np.bincount((np.asarray(enc) - np.asarray(glyph)) % 26, minlength=26).max())

def stat_t2(enc_sorted):
    return lnds(list(enc_sorted))

def null_perms(rng, enc, n):
    """n permutations of the encoded letters among the set's symbols (multiset preserved)."""
    enc = np.asarray(enc)
    for _ in range(n):
        yield rng.permutation(enc)

def run_test(kind, glyph, enc, rng, n=N):
    if kind == 'T1':
        f = lambda e: stat_t1(glyph, e)
    else:
        f = lambda e: stat_t2(e)
    obs = f(enc)
    ge = sum(1 for e in null_perms(rng, enc, n) if f(e) >= obs)
    return obs, (1 + ge) / (1 + n)

def sets_for(cipher):
    gt = json.load(open(os.path.join(H, 'glyph_table.json')))[cipher]
    d = json.load(open(D + cipher + '.json'))
    rows = {'NORMAL': [], 'NONNORMAL': []}
    for s in d['symbols']:
        g = gt[s['ascii']]
        if g['glyph_letter'] is None or s['letter'] not in A: continue
        row = (g['glyph_letter'], s['ascii'], A.index(s['letter']))
        if g['transform'] == 'normal': rows['NORMAL'].append(row)
        elif g['transform'] in ('reversed', 'rotated/upside-down'): rows['NONNORMAL'].append(row)
    for k in rows: rows[k].sort(key=lambda r: (r[0], r[1]))
    return rows

def main(n=N):
    res = {'seed': SEED, 'N': n, 'alpha_bonferroni': 0.05 / 6}
    for c in ['z408', 'z340']:
        rows = sets_for(c)
        rng = np.random.default_rng(SEED)
        nm, nn = rows['NORMAL'], rows['NONNORMAL']
        out = {'set_sizes': {'NORMAL': len(nm), 'NONNORMAL': len(nn)}}
        g = [A.index(r[0]) for r in nm]; e = [r[2] for r in nm]
        out['T1'], out['p_T1'] = run_test('T1', g, e, rng, n)
        d = np.bincount((np.array(e) - np.array(g)) % 26, minlength=26)
        out['T1_shift_counts'] = {A[i]: int(d[i]) for i in range(26) if d[i]}
        out['T2'], out['p_T2'] = run_test('T2', None, e, rng, n)
        out['T3'], out['p_T3'] = run_test('T3', None, [r[2] for r in nn], rng, n)
        res[c] = out
    # descriptive pooling of nothing beyond reporting; no pooled inference
    res['significant_at_bonferroni'] = [f'{c}:{t}' for c in ['z408', 'z340'] for t in ['T1', 'T2', 'T3']
                                         if res[c]['p_' + t] <= res['alpha_bonferroni']]
    return res

if __name__ == '__main__':
    if '--make-table' in sys.argv:
        make_glyph_table(); sys.exit()
    res = main()
    json.dump(res, open(os.path.join(H, 'results.json'), 'w'), indent=1, sort_keys=True)
    print(json.dumps(res, indent=1, sort_keys=True))

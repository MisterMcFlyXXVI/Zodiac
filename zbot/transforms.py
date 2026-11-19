"""Read-order families (transpositions) applied before substitution.

Every function returns a list of (label, order) where order[k] is the
written index of the k-th symbol read. A *family* is tested as a whole: the
hypothesis score is the best over the family, and the null model takes the
same maximum, so trying many orders is paid for honestly (look-elsewhere).
"""
from __future__ import annotations

import itertools
import math
import random

Order = list[int]


def identity(n: int) -> list[tuple[str, Order]]:
    return [("identity", list(range(n)))]


def reverse(n: int) -> list[tuple[str, Order]]:
    return [("reverse", list(range(n))[::-1])]


def decimations(n: int) -> list[tuple[str, Order]]:
    """Read every k-th symbol with wrap-around (k coprime with n, k != 1)."""
    return [(f"decimate{k}", [(i * k) % n for i in range(n)])
            for k in range(2, n) if math.gcd(k, n) == 1]


def rail_fences(n: int, rails=(2, 3, 4, 5)) -> list[tuple[str, Order]]:
    out = []
    for r in rails:
        if r >= n:
            continue
        pattern = list(range(r)) + list(range(r - 2, 0, -1))
        rows = [[] for _ in range(r)]
        for i in range(n):
            rows[pattern[i % len(pattern)]].append(i)
        # The cipher was written row by row; plaintext index i sits at written slot w.
        written = [i for row in rows for i in row]
        order = [0] * n
        for w, i in enumerate(written):
            order[i] = w
        out.append((f"railfence{r}", order))
    return out


def columnar(n: int, width: int, col_order: tuple[int, ...] | None = None) -> Order:
    """Plaintext written in rows of `width`, read off by columns in `col_order`.

    The cipher we hold is the column read-off, so undoing it means: for each
    plaintext slot (row-major), find which ciphertext index it went to.
    """
    col_order = col_order or tuple(range(width))
    nrows = math.ceil(n / width)
    cells = [(r, c) for r in range(nrows) for c in range(width) if r * width + c < n]
    pos_in_cipher = {}
    k = 0
    for c in col_order:
        for r in range(nrows):
            if r * width + c < n:
                pos_in_cipher[(r, c)] = k
                k += 1
    return [pos_in_cipher[cell] for cell in cells]


def columnars(n: int, widths=range(2, 9), max_perms: int = 720, rng: random.Random | None = None):
    rng = rng or random.Random(0)
    out = []
    for w in widths:
        if w >= n:
            continue
        perms = list(itertools.permutations(range(w))) if math.factorial(w) <= max_perms else \
            [tuple(rng.sample(range(w), w)) for _ in range(max_perms)]
        for p in perms:
            out.append((f"columnar{w}:{''.join(map(str, p)) if w <= 10 else p}", columnar(n, w, p)))
    return out


def grid_decimations(n: int, shapes=None) -> list[tuple[str, Order]]:
    """Z340-style: k-th symbol at row (dr*k mod R), col (dc*k mod W) on an R x W grid.

    This is the family the Z340 solvers found (section 1 used (1,2) on 9x17).
    Only full-coverage (bijective) steps are kept.
    """
    out = []
    shapes = shapes or [(r, n // r) for r in range(2, n) if n % r == 0 and n // r >= 2]
    for R, W in shapes:
        for dr in range(1, R):
            for dc in range(1, W):
                order = [((dr * k) % R) * W + (dc * k) % W for k in range(R * W)]
                if len(set(order)) == R * W and order != list(range(n)):
                    out.append((f"griddec{R}x{W}:({dr},{dc})", order))
    return out


def routes(n: int, widths=range(2, 17)) -> list[tuple[str, Order]]:
    """Boustrophedon and plain column reads for each grid width."""
    out = []
    for w in widths:
        if w >= n:
            continue
        nrows = math.ceil(n / w)
        snake = []
        for r in range(nrows):
            row = [r * w + c for c in range(w) if r * w + c < n]
            snake += row if r % 2 == 0 else row[::-1]
        out.append((f"boustrophedon{w}", snake))
        out.append((f"columns{w}", columnar(n, w)))
    return out


def dedupe(family):
    seen, out = set(), []
    for label, order in family:
        t = tuple(order)
        if t not in seen:
            seen.add(t)
            out.append((label, order))
    return out


FAMILIES = {
    "identity": lambda n: identity(n),
    "reverse": lambda n: reverse(n),
    "decimations": decimations,
    "railfences": rail_fences,
    "routes": routes,
    "griddec": grid_decimations,
    "columnar2to6": lambda n: columnars(n, widths=range(2, 7)),
    "columnar7to8_sampled": lambda n: columnars(n, widths=range(7, 9), max_perms=500),
}


def family(names: list[str], n: int):
    fam = []
    for name in names:
        fam += FAMILIES[name](n)
    return dedupe(fam)

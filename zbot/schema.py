"""What a hypothesis spec may contain, and checks for specs that come from outside.

Built-in specs are trusted. Specs dropped into hypotheses/queue/ (by hand or by the
web app) are checked here before the bot runs them, so a typo or an oversized
request is rejected with a clear message instead of wasting a 5.5-hour run.
"""
from __future__ import annotations

import re

from . import lm, transforms
from .cipher import load as load_cipher, variants

BASE_CIPHERS = ["z13", "z32", "z408", "z340"]
MODELS = {"homophonic": "Several symbols may stand for the same letter (Zodiac's usual method)",
          "simple": "Exactly one symbol per letter"}
FAMILY_HELP = {
    "identity": "Read as written (no transposition)",
    "reverse": "Read backwards",
    "decimations": "Read every k-th symbol, wrapping around",
    "railfences": "Rail-fence (zig-zag) transposition, 2-5 rails",
    "routes": "Boustrophedon and column-by-column reads for each grid width",
    "griddec": "Z340-style diagonal reads on a grid (how Z340 was transposed)",
    "columnar2to6": "Keyed columnar transposition, widths 2-6, every key (872 orders)",
    "columnar7to8_sampled": "Keyed columnar transposition, widths 7-8, 500 random keys each",
}
LIMITS = {"restarts": (1, 8), "nulls": (9, 199), "controls": (0, 20), "extend_nulls": (0, 499),
          "iters": (10_000, 3_000_000), "pins": 10, "pin_family": 64, "drop_symbols": 3,
          "family_orders": 2_000, "title": 120, "motivation": 1_000}
ALLOWED_KEYS = {"id", "title", "motivation", "cipher", "model", "lang", "families", "drop_symbols",
                "pins", "pin_family", "restarts", "iters", "nulls", "controls", "extend_nulls",
                "explore_columnar", "klw", "source", "suggested_by"}
ID_RE = re.compile(r"^user\.[a-z0-9][a-z0-9._-]{2,80}$")


def cipher_names() -> list[str]:
    out = []
    for b in BASE_CIPHERS:
        out.append(b)
        out += [v for v in variants(b) if not v.endswith(".canonical")]  # same as the base
    return out


def check(spec: dict) -> list[str]:
    """Return a list of problems (empty if the spec is acceptable)."""
    errs: list[str] = []
    extra = set(spec) - ALLOWED_KEYS
    if extra:
        errs.append(f"unknown fields: {sorted(extra)}")
    if not ID_RE.match(str(spec.get("id", ""))):
        errs.append("id must look like user.something (lowercase letters, digits, . _ -)")
    for k in ("title", "motivation"):
        if not isinstance(spec.get(k, ""), str) or len(spec.get(k, "")) > LIMITS[k]:
            errs.append(f"{k} must be text of at most {LIMITS[k]} characters")
    if not spec.get("title"):
        errs.append("title is required")
    names = spec.get("cipher")
    names = names if isinstance(names, list) else [names]
    known = cipher_names()
    if not (1 <= len(names) <= 2) or any(n not in known for n in names):
        errs.append(f"cipher must be one or two of {known}")
        return errs
    text = "".join(load_cipher(n).text for n in names)
    if spec.get("model", "homophonic") not in MODELS:
        errs.append(f"model must be one of {list(MODELS)}")
    if spec.get("lang", "en") not in lm.CORPORA:
        errs.append(f"lang must be one of {list(lm.CORPORA)}")
    fams = spec.get("families", ["identity"])
    if not isinstance(fams, list) or any(f not in transforms.FAMILIES for f in fams):
        errs.append(f"families must be a list from {list(transforms.FAMILIES)}")
    elif len(names) > 1 and fams != ["identity"]:
        errs.append("a shared-key test of two ciphers can only use the identity read order")
    else:
        n = len(load_cipher(names[0]).text) - sum(load_cipher(names[0]).text.count(d)
                                                 for d in spec.get("drop_symbols", []))
        if len(transforms.family(fams, n)) > LIMITS["family_orders"]:
            errs.append(f"read-order families give more than {LIMITS['family_orders']} orders")
    for k in ("restarts", "nulls", "controls", "extend_nulls", "iters"):
        if k in spec:
            lo, hi = LIMITS[k]
            if not isinstance(spec[k], int) or not lo <= spec[k] <= hi:
                errs.append(f"{k} must be a whole number from {lo} to {hi}")
    drops = spec.get("drop_symbols", [])
    if not isinstance(drops, list) or len(drops) > LIMITS["drop_symbols"] or any(d not in text for d in drops):
        errs.append(f"drop_symbols must be up to {LIMITS['drop_symbols']} symbols that occur in the cipher")
    pinsets = spec.get("pin_family", [spec.get("pins", {})])
    if not isinstance(pinsets, list) or len(pinsets) > LIMITS["pin_family"]:
        errs.append(f"at most {LIMITS['pin_family']} pin sets")
    else:
        for ps in pinsets:
            if (not isinstance(ps, dict) or len(ps) > LIMITS["pins"]
                    or any(s not in text or not re.fullmatch(r"[A-Z]", str(l)) for s, l in ps.items())):
                errs.append(f"pins map up to {LIMITS['pins']} cipher symbols to single letters A-Z")
                break
    if spec.get("model") == "simple" and len(set(text)) - len(set(drops)) > 26:
        errs.append("simple substitution is impossible: more than 26 distinct symbols")
    ec = spec.get("explore_columnar")
    if ec is not None:
        ok = (isinstance(ec, dict) and isinstance(ec.get("width"), int) and 2 <= ec["width"] <= 16
              and isinstance(ec.get("perms"), list) and len(ec["perms"]) <= 200
              and all(sorted(p) == list(range(ec["width"])) for p in ec["perms"]))
        if not ok:
            errs.append("explore_columnar needs width 2-16 and up to 200 column orders")
    return errs


def options() -> dict:
    """Everything the web app needs to build a valid form."""
    ciphers = []
    for n in cipher_names():
        c = load_cipher(n)
        ciphers.append({"name": n, "text": c.text, "length": len(c.text), "distinct": len(set(c.text)),
                        "solved": n.split(".")[0] in ("z408", "z340")})
    return {"ciphers": ciphers, "models": MODELS, "languages": lm.LANG_NAMES,
            "families": FAMILY_HELP, "limits": LIMITS}

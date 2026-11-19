"""The hypothesis queue.

Built-in hypotheses come first, in priority order. Anyone (or any agent)
can add more by dropping a JSON file into hypotheses/queue/ with the same
fields. When everything queued is done, the explorer generates new
members of open-ended families so the bot keeps working.

Spec fields:
  id           unique, stable name (results are keyed on it)
  title        one line, human readable
  motivation   why this is worth testing; cite prior work
  cipher       'z13', 'z32', a variant like 'z13.circles_distinct', or a list (shared key)
  model        'homophonic' (default) or 'simple' (one symbol per letter)
  families     read-order families from zbot.transforms.FAMILIES (default identity)
  drop_symbols symbols removed before solving (treated as nulls/fillers)
  pins / pin_family   fixed symbol->letter assignments (one set, or a family of sets)
  restarts, iters, nulls, controls, extend_nulls   search/test budget
"""
from __future__ import annotations

import itertools
import json
import pathlib
import random

from . import lm

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE_DIR = ROOT / "hypotheses" / "queue"

WINCHXYZ = "winchxyz/zodiac-z13-z32 REPORT.md Appendix C lists this as not tested (2026)."


def _subsets(items):
    for r in range(1, len(items) + 1):
        yield from itertools.combinations(items, r)


def builtin() -> list[dict]:
    H: list[dict] = []

    # --- 0. Calibration: the bot must pass these before its other results mean anything.
    H.append(dict(id="calib.z408.homophonic", title="Z408 as plain homophonic substitution",
                  motivation="Positive calibration: solved 1969. Must come out p<0.05, power 1.",
                  cipher="z408", iters=1_500_000, restarts=4, nulls=19, controls=0, extend_nulls=0))

    # --- 1. Baselines on the canonical and variant transcriptions (replicates prior work).
    for c, models in [("z13", ["homophonic", "simple"]), ("z32", ["homophonic"])]:
        # (Z32 has 29 distinct symbols, so a one-symbol-per-letter key is impossible.)
        for model in models:
            H.append(dict(id=f"base.{c}.{model}", title=f"{c.upper()} canonical, {model} substitution, written order",
                          motivation="Baseline; replicates Oranchak and winchxyz null-model results.",
                          cipher=c, model=model))
    for v in ["z13.circles_distinct", "z13.bracket_is_perp", "z13.crosshair_null", "z13.reversed",
              "z32.bar_is_serif_I", "z32.t2_is_perp", "z32.tau_distinct", "z32.triangles_merged",
              "z32.bar_I_and_t2_perp"]:
        H.append(dict(id=f"variant.{v}", title=f"Transcription variant {v}, homophonic",
                      motivation="Transcription uncertainty from winchxyz data/ciphers/README.md.",
                      cipher=v))

    # --- 2. Hypotheses the 2026 exhaustive study did not test.
    H.append(dict(id="new.z13.transpositions.simple",
                  title="Z13 under transpositions other than reversal, simple substitution",
                  motivation=WINCHXYZ + " Z13's 8 symbols fit a near-simple key (their F2).",
                  cipher="z13", model="simple",
                  families=["decimations", "railfences", "routes", "columnar2to6"], restarts=3))
    H.append(dict(id="new.z32.transpositions.homophonic",
                  title="Z32 under structured transpositions (incl. Z340-style grid decimation) + homophonic key",
                  motivation=WINCHXYZ + " Z340 used a (1,2) grid decimation; Zodiac may have reused the idea.",
                  cipher="z32", families=["reverse", "decimations", "railfences", "routes", "griddec"],
                  restarts=3))
    H.append(dict(id="new.z32.crosshair_null", title="Z32 with the crosshair symbol as a null",
                  motivation=WINCHXYZ + " The crosshair is Zodiac's signature and may not encode a letter.",
                  cipher="z32", drop_symbols=["z"]))
    H.append(dict(id="new.z32.omega_null", title="Z32 with the omega symbol as a null",
                  motivation=WINCHXYZ, cipher="z32", drop_symbols=["?"]))
    H.append(dict(id="new.joint.z13_z32.homophonic", title="Z13 and Z32 enciphered with one shared key",
                  motivation=WINCHXYZ + " ('a converged joint Z13+Z32 key solver'). Sent 2 months apart; share symbols A, N, M, z, K-like glyphs.",
                  cipher=["z13", "z32"]))
    letters = [s for s in "AENKM"]
    H.append(dict(id="new.z13.literal_pin_subsets",
                  title="Z13 with subsets of its Latin-letter symbols standing for themselves",
                  motivation=WINCHXYZ + " ('subsets of the letters-literal pins').",
                  cipher="z13", model="simple",
                  pin_family=[{s: s for s in sub} for sub in _subsets(letters)], restarts=3))
    z32_letters = list("CJOAMRTGXFDVHEL")
    rng = random.Random(32)
    H.append(dict(id="new.z32.literal_pin_subsets_sampled",
                  title="Z32 with random subsets (size 3-6) of its Latin-letter symbols standing for themselves",
                  motivation="Extends the letters-literal idea to Z32; 40 sampled subsets.",
                  cipher="z32",
                  pin_family=[{s: s for s in rng.sample(z32_letters, rng.randint(3, 6))} for _ in range(40)],
                  restarts=2))
    H.append(dict(id="new.z32.columnar_full", title="Z32 under keyed columnar transposition, widths 2-8",
                  motivation=WINCHXYZ + " ('a key model combined with transposition for Z32'). Widths 7-8 sampled.",
                  cipher="z32", families=["columnar2to6", "columnar7to8_sampled"], restarts=2,
                  nulls=19, controls=6))
    # --- 3. Other languages. Zodiac's solved ciphers and letters are English, so the prior
    # is low; but each test is cheap. Every language must pass its own calibration first.
    for lang in ["es", "fr", "de", "it", "vi"]:
        name = lm.LANG_NAMES[lang]
        H.append(dict(id=f"calib.{lang}.synthetic408",
                      title=f"Calibration: Z408-like homophonic cipher of held-out {name}",
                      motivation=f"The {name} model and solver must crack a known {name} cipher "
                                 f"before any {name} result counts.",
                      lang=lang, synthetic={"length": 408, "key_size": 54, "seed": 1},
                      iters=1_500_000, restarts=4, nulls=19, controls=0, extend_nulls=0))
        H.append(dict(id=f"lang.{lang}.z13.simple", title=f"Z13 as {name}, simple substitution",
                      motivation="Language hypothesis.", cipher="z13", model="simple", lang=lang))
        H.append(dict(id=f"lang.{lang}.z13.homophonic", title=f"Z13 as {name}, homophonic",
                      motivation="Language hypothesis.", cipher="z13", lang=lang))
        H.append(dict(id=f"lang.{lang}.z32.homophonic", title=f"Z32 as {name}, homophonic",
                      motivation="Language hypothesis.", cipher="z32", lang=lang))
    # The slowest built-in (hours) goes last so it doesn't hold up everything else.
    H.sort(key=lambda h: h["id"] == "new.z32.columnar_full")
    return H


def queued() -> list[dict]:
    out = []
    if QUEUE_DIR.exists():
        for p in sorted(QUEUE_DIR.glob("*.json")):
            spec = json.loads(p.read_text())
            spec.setdefault("id", p.stem)
            spec["source"] = str(p.relative_to(ROOT))
            out.append(spec)
    return out


def explore(n_done: int) -> dict:
    """Generate the next open-ended exploration hypothesis (deterministic in n_done)."""
    rng = random.Random(1000 + n_done)
    kind = rng.choice(["z32_colkeys", "z13_pins_cols"])
    if kind == "z32_colkeys":
        w = rng.choice([9, 10, 11, 12])
        perms = [rng.sample(range(w), w) for _ in range(60)]
        return dict(id=f"explore.{n_done}.z32.columnar{w}",
                    title=f"Z32 keyed columnar width {w}, 60 random keys",
                    motivation="Open-ended exploration of the transposition space.",
                    cipher="z32", families=["identity"], explore_columnar={"width": w, "perms": perms},
                    restarts=2, nulls=19, controls=6)
    sub = rng.sample("AENKM", rng.randint(1, 3))
    return dict(id=f"explore.{n_done}.z13.pins{''.join(sorted(sub))}.columnar",
                title=f"Z13 pins {sub} literal + columnar 2-6",
                motivation="Combination of two untested ideas.",
                cipher="z13", model="simple", pins={s: s for s in sub},
                families=["columnar2to6"], restarts=2)

"""results/STATUS.json: the bot's state for the web app, plus suggested next experiments.

Written after every hypothesis and at the end of every run. Contains:
  * pending / done hypotheses, with rough cost estimates
  * the bot's own suggestions, as ready-to-queue specs
  * the options a new hypothesis may use (ciphers, languages, families, limits)
"""
from __future__ import annotations

import json
import os
import time

from . import evaluate, hypotheses, lm, schema

WORKERS = 4  # GitHub's public runners have 4 cores


def estimate_seconds(spec: dict) -> float:
    """Rough wall-clock estimate on a 4-core runner (within a factor of ~2)."""
    try:
        texts = evaluate.real_texts(spec)
    except Exception:
        return float("nan")
    n = sum(len(t) for t in texts)
    nsym = len(set("".join(texts)))
    iters = spec.get("iters") or max(50_000, 10_000 * nsym)
    per_iter = 0.8e-6 + 0.2e-6 * (n / nsym)  # fitted to measured run times
    members = len(evaluate.family_for(spec, len(texts[0]))) * len(evaluate.pin_sets(spec))
    instances = 1 + spec.get("nulls", 19) + spec.get("controls", 10)
    return 2.0 + instances * members * spec.get("restarts", 4) * iters * per_iter / WORKERS


def _latest(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        out[r["id"]] = r
    return out


def _variant_of(cipher: str) -> tuple[str, str]:
    base, _, var = cipher.partition(".")
    return base, var or "canonical"


def suggestions(rows: list[dict], known_ids: set[str], specs: list[dict] = ()) -> list[dict]:
    """Next experiments worth running, most useful first. Each carries a ready spec."""
    latest = _latest(rows)
    out: list[dict] = []

    def add(kind: str, why: str, spec: dict):
        if spec["id"] in known_ids or any(s["spec"]["id"] == spec["id"] for s in out):
            return
        if schema.check(spec):
            return
        spec["suggested_by"] = "zbot"
        out.append({"kind": kind, "why": why, "spec": spec, "est_seconds": estimate_seconds(spec)})

    # 1. Follow up anything that came close: confirm with more nulls, check robustness.
    for r in latest.values():
        if r["id"].startswith("calib.") or r.get("p") is None or r["p"] > 0.1:
            continue
        if r.get("power") is not None and r["power"] < 0.2:
            continue  # an untestable result can't be confirmed, however low its p
        base = {k: v for k, v in r["spec"].items() if k in schema.ALLOWED_KEYS and k not in ("source", "suggested_by")}
        slug = r["id"].replace("user.", "")
        conf = dict(base, id=f"user.confirm.{slug}", nulls=199, extend_nulls=0,
                    title=f"Confirm {r['id']} with 199 nulls",
                    motivation=f"{r['id']} gave p={r['p']:.3f} (power {r.get('power')}). More nulls tell "
                               "whether that was luck.")
        add("follow-up", f"`{r['id']}` came out at p={r['p']:.3f}. A larger null sample shows whether it holds.",
            conf)
        cipher = r["spec"].get("cipher")
        if isinstance(cipher, str):
            b, _ = _variant_of(cipher)
            for v in [b] + [x for x in schema.variants(b) if not x.endswith('.canonical')]:
                if v != cipher:
                    add("robustness", f"If `{r['id']}` is real it should survive other readings of the symbols.",
                        dict(base, cipher=v, id=f"user.robust.{slug}.{v.replace('.', '-')}",
                             title=f"{r['spec'].get('title', r['id'])} — on {v}",
                             motivation=f"Robustness check of {r['id']} under transcription {v}."))

    # 2. Coverage gaps: cheap combinations not tried yet.
    done_sigs = set()
    for s in [r["spec"] for r in latest.values()] + list(specs):
        if not s.get("families") and not s.get("pins") and not s.get("pin_family") and not s.get("drop_symbols"):
            done_sigs.add((json.dumps(s.get("cipher")), s.get("model", "homophonic"), s.get("lang", "en")))
    for lang in ["en", "es", "fr", "de", "it", "vi"]:
        for c in ["z13", "z13.circles_distinct", "z13.bracket_is_perp", "z13.crosshair_null", "z13.reversed"]:
            for model in ["simple", "homophonic"]:
                if (json.dumps(c), model, lang) in done_sigs or \
                        len([x for x in out if x["kind"] == "coverage"]) >= 8:
                    continue
                name = lm.LANG_NAMES[lang]
                add("coverage", f"Not tried yet: {c} as {name} with a {model} key.",
                    dict(id=f"user.cover.{lang}.{c.replace('.', '-')}.{model}", cipher=c, model=model, lang=lang,
                         title=f"{c} as {name}, {model} substitution",
                         motivation="Fills a gap in the transcription x key x language grid."))

    # 3. Transposition idea with real precedent: Z340's diagonal read, on Z13 in other languages.
    for lang in ["es", "fr", "de", "it", "vi"]:
        add("idea", "Z340 was transposed; a reading-order search in another language hasn't been run.",
            dict(id=f"user.idea.{lang}.z13.transpositions", cipher="z13", model="simple", lang=lang,
                 families=["decimations", "railfences", "routes"],
                 title=f"Z13 as {lm.LANG_NAMES[lang]} under simple transpositions",
                 motivation="Combines the transposition and language hypotheses at modest cost."))
        if len([s for s in out if s["kind"] == "idea"]) >= 3:
            break
    return out[:20]


def write(rows: list[dict], path) -> dict:
    latest = _latest(rows)
    specs = hypotheses.queued() + hypotheses.builtin()
    langs = lm.available()
    pending, done = [], []
    for s in specs:
        r = latest.get(s["id"])
        item = {"id": s["id"], "title": s.get("title", ""), "lang": evaluate.lang_of(s),
                "source": "queue" if s.get("source") else "built-in",
                "suggested_by": s.get("suggested_by"),
                "est_seconds": estimate_seconds(s)}
        if s.get("invalid"):
            item["problems"] = s["invalid"]
        if r and (r["spec_hash"] == evaluate._spec_hash(s)):
            done.append(dict(item, verdict=r.get("verdict")))
        elif evaluate.lang_of(s) in langs:
            pending.append(item)
    known = {s["id"] for s in specs} | set(latest)
    counts: dict[str, int] = {}
    for r in latest.values():
        v = (r.get("verdict") or "?").split(":")[0]
        counts[v] = counts.get(v, 0) + 1
    status = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run": {"github_run_id": os.environ.get("GITHUB_RUN_ID"),
                "github_run_url": (f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
                                   f"/actions/runs/{os.environ['GITHUB_RUN_ID']}")
                if os.environ.get("GITHUB_RUN_ID") else None},
        "models": {l: lm.fingerprint(l) for l in langs},
        "counts": counts,
        "pending": pending,
        "done": done,
        "explore_next": hypotheses.explore(sum(1 for i in latest if i.startswith("explore."))).get("title"),
        "suggestions": suggestions(rows, known, specs),
        "options": schema.options(),
    }
    path.write_text(json.dumps(status, indent=1))
    return status

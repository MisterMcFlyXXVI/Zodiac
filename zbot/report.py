"""Write results/REPORT.md and results/ALERTS.md from the ledger.

Multiple comparisons: every hypothesis the bot has ever run counts. Holm's
correction is applied across all of them, so a long-running bot cannot
"find" a solution just by trying enough things.
"""
from __future__ import annotations

import os
import pathlib

from .evaluate import power_at, power_ci, power_pooled, tier, wilson

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = pathlib.Path(os.environ.get("ZBOT_RESULTS_DIR", ROOT / "results"))
OUT = RESULTS / "REPORT.md"
ALERTS = RESULTS / "ALERTS.md"


MIN_POWER = 0.2


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj = [1.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * ps[i]))
        adj[i] = running
    return adj


def effective_power(r: dict):
    """Pooled-threshold power when the row has the raw scores, else the stored power."""
    if r.get("real_score") is not None and r.get("null_scores") and r.get("control_scores"):
        return power_pooled(r["real_score"], r["null_scores"], r["control_scores"])
    return r.get("power")


def write(rows: list[dict]) -> None:
    # Latest result per (id) wins.
    latest: dict[str, dict] = {}
    for r in rows:
        latest[r["id"]] = r
    rs = list(latest.values())
    for r in rs:
        r["power"] = effective_power(r)
        r["tier"] = tier(r["id"])
    tested = [r for r in rs if r.get("p") is not None and r["tier"] != "calibration"]
    # Correction families: Holm runs separately within each tier (exploratory, confirmatory),
    # so a large screening sweep cannot dilute a targeted test. Within a tier, the family is
    # tests with power >= MIN_POWER. Power uses a threshold from the pooled {real} + nulls
    # scores. Under the null the real score is exchangeable with the nulls, so that threshold
    # does not depend on which score is real, and the filter is independent of p under the
    # null. Filtering on a nulls-only threshold would not be, since the same nulls set p.
    # Untestable tests get no corrected p.
    for r in tested:
        r["p_holm"] = None
    for t in ("exploratory", "confirmatory"):
        family = [r for r in tested if r["tier"] == t and (r["power"] is None or r["power"] >= MIN_POWER)]
        for r, a in zip(family, holm([r["p"] for r in family])):
            r["p_holm"] = a

    m_conf = len([r for r in tested if r["tier"] == "confirmatory" and r["p_holm"] is not None])
    for r in tested:
        r["power_alert"] = None
        if r["tier"] == "confirmatory" and m_conf and r.get("real_score") is not None \
                and r.get("null_scores") and r.get("control_scores"):
            r["power_alert"] = power_at(0.05 / m_conf, r["real_score"], r["null_scores"], r["control_scores"])
        r["power_ci_now"] = (power_ci(r["power"], len(r["control_scores"]))
                             if r["power"] is not None and r.get("control_scores") else r.get("power_ci"))

    lines = ["# Zodiac bot: results", "",
             "Generated from `results/ledger.jsonl`. Do not edit by hand.", "",
             f"Hypotheses run: {len(rs)} (excluding calibration: {len(tested)}).", "",
             "How to read this: **p** compares the real cipher with shuffled copies of its own symbols. "
             "**power** is how often genuine English, enciphered the same way, beats the nulls. "
             "If power is low, a low or high p means nothing. "
             "**p (Holm)** corrects within the row's tier. "
             "Exploration is screening only and never alerts: a low exploratory p should be re-run as a "
             "queued (confirmatory) test.", ""]
    cal = [r for r in rs if r["id"].startswith("calib.")]
    if cal:
        lines += ["## Calibration", ""]
        for r in cal:
            lines.append(f"- `{r['id']}`: **{r.get('verdict')}**, z={r.get('z') or 0:.1f} vs "
                         f"{len(r.get('null_scores', []))} nulls, letter accuracy "
                         f"{r.get('calib_accuracy', 0):.1%}, best: `{(r.get('top') or [{}])[0].get('plaintext', '')[:60]}`")
        lines.append("")
    lines += ["## Hypotheses", "",
              "| id | tier | lang | family | p | p (Holm) | z | power | power 95% CI | power at alert bar | verdict | best decode |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(tested, key=lambda r: r["p"]):
        best = (r.get("top") or [{}])[0]
        pw = "n/a" if r.get("power") is None else f"{r['power']:.2f}"
        ci = r["power_ci_now"]
        pci = "–" if not ci else f"{ci[0]:.2f}–{ci[1]:.2f}"
        pa = "–"
        if r["power_alert"] is not None:
            n_c = len(r["control_scores"])
            lo, hi = wilson(round(r["power_alert"] * n_c), n_c)
            pa = f"{r['power_alert']:.2f} ({lo:.2f}–{hi:.2f})"
        lines.append(f"| `{r['id']}` | {r['tier']} | {r.get('lang', 'en')} | {r.get('family_size', '?')} | {r['p']:.3f} | {"–" if r['p_holm'] is None else f"{r['p_holm']:.3f}"} | {r.get('z') or 0:+.1f} | {pw} | {pci} | {pa} | "
                     f"{r['verdict'].split(':')[0]} | `{best.get('plaintext', '')[:40]}` |")
    errs = [r for r in rs if r.get("verdict") == "ERROR" or r.get("verdict", "").startswith("SKIPPED")]
    if errs:
        lines += ["", "## Errors and skips", ""] + [f"- `{r['id']}`: {r.get('error') or r['verdict']}" for r in errs]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")

    # Gating on power_alert (power at the Holm alpha) instead of power is the owner's call; the rule stays as is.
    hits = [r for r in tested if r["tier"] == "confirmatory" and r["p_holm"] is not None and r["p_holm"] < 0.05 and (r.get("power") or 0) >= 0.5]
    alert = ["# Alerts", ""]
    if not hits:
        alert.append("None. No hypothesis survives correction for multiple comparisons with adequate power.")
    for r in hits:
        alert += [f"## {r['id']}", "", r["spec"].get("title", ""), "",
                  f"p={r['p']:.4f}, Holm-adjusted {r['p_holm']:.4f}, power {r['power']:.2f}.", "",
                  "Top decodes:", ""] + [f"- `{t['plaintext']}` ({t['order']}, {t['score']:.1f})" for t in r["top"][:5]]
        alert += ["", "A statistical signal is not a solution. Before taking it seriously: rerun with "
                  "more nulls, check it under other transcription variants, and ask whether the "
                  "plaintext is meaningful *and* predicted in advance.", ""]
    ALERTS.write_text("\n".join(alert) + "\n")

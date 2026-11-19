"""Write results/REPORT.md and results/ALERTS.md from the ledger.

Multiple comparisons: every hypothesis the bot has ever run counts. Holm's
correction is applied across all of them, so a long-running bot cannot
"find" a solution just by trying enough things.
"""
from __future__ import annotations

import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = pathlib.Path(os.environ.get("ZBOT_RESULTS_DIR", ROOT / "results"))
OUT = RESULTS / "REPORT.md"
ALERTS = RESULTS / "ALERTS.md"


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj = [1.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * ps[i]))
        adj[i] = running
    return adj


def write(rows: list[dict]) -> None:
    # Latest result per (id) wins.
    latest: dict[str, dict] = {}
    for r in rows:
        latest[r["id"]] = r
    rs = list(latest.values())
    tested = [r for r in rs if r.get("p") is not None and not r["id"].startswith("calib.")]
    adj = holm([r["p"] for r in tested])
    for r, a in zip(tested, adj):
        r["p_holm"] = a

    lines = ["# Zodiac bot: results", "",
             "Generated from `results/ledger.jsonl`. Do not edit by hand.", "",
             f"Hypotheses run: {len(rs)} (excluding calibration: {len(tested)}).", "",
             "How to read this: **p** compares the real cipher with shuffled copies of its own symbols. "
             "**power** is how often genuine English, enciphered the same way, beats the nulls. "
             "If power is low, a low or high p means nothing. "
             "**p (Holm)** corrects for every hypothesis the bot has tried.", ""]
    cal = [r for r in rs if r["id"].startswith("calib.")]
    if cal:
        lines += ["## Calibration", ""]
        for r in cal:
            lines.append(f"- `{r['id']}`: **{r.get('verdict')}**, z={r.get('z') or 0:.1f} vs "
                         f"{len(r.get('null_scores', []))} nulls, letter accuracy "
                         f"{r.get('calib_accuracy', 0):.1%}, best: `{(r.get('top') or [{}])[0].get('plaintext', '')[:60]}`")
        lines.append("")
    lines += ["## Hypotheses", "",
              "| id | lang | family | p | p (Holm) | z | power | verdict | best decode |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(tested, key=lambda r: r["p"]):
        best = (r.get("top") or [{}])[0]
        pw = "n/a" if r.get("power") is None else f"{r['power']:.2f}"
        lines.append(f"| `{r['id']}` | {r.get('lang', 'en')} | {r.get('family_size', '?')} | {r['p']:.3f} | {r['p_holm']:.3f} | {r.get('z') or 0:+.1f} | {pw} | "
                     f"{r['verdict'].split(':')[0]} | `{best.get('plaintext', '')[:40]}` |")
    errs = [r for r in rs if r.get("verdict") == "ERROR" or r.get("verdict", "").startswith("SKIPPED")]
    if errs:
        lines += ["", "## Errors and skips", ""] + [f"- `{r['id']}`: {r.get('error') or r['verdict']}" for r in errs]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")

    hits = [r for r in tested if r["p_holm"] < 0.05 and (r.get("power") or 0) >= 0.5]
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

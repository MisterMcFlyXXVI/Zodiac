import { notFound } from "next/navigation";
import { loadAll } from "@/lib/data";
import { isAdmin } from "@/lib/auth";
import { canWrite, getRow } from "@/lib/github";
import { cipherLabel, fmtDuration, fmtP, isAlert, relTime } from "@/lib/stats";
import Verdict, { VERDICT_HELP } from "@/components/Verdict";
import ScoreChart from "@/components/ScoreChart";
import { CipherGlyphs } from "@/components/Glyph";
import SuggestionList from "@/components/SuggestionList";
import type { Spec } from "@/lib/types";

export const dynamic = "force-dynamic"; // fresh relative times; GitHub data itself is cached 2 min

const LANGS: Record<string, string> = { en: "English", es: "Spanish", fr: "French", de: "German", it: "Italian", vi: "Vietnamese" };

export default async function Hypothesis({ params }: { params: Promise<{ id: string }> }) {
  const id = decodeURIComponent((await params).id);
  const [{ rows, status }, full] = await Promise.all([loadAll(), getRow(id)]);
  const listed = rows.find((x) => x.id === id);
  if (!listed) notFound();
  // List data carries the corrected p and verdict; the full row adds the score arrays for the chart.
  const r = { ...(full ?? {}), ...listed, null_scores: full?.null_scores, control_scores: full?.control_scores,
              spec: full?.spec ?? listed.spec, top: full?.top ?? listed.top };
  const admin = await isAdmin();
  const slug = id.replace(/^user\./, "");
  const related = (status?.suggestions ?? []).filter((s) => s.spec.id.includes(slug));
  const isCalib = id.startsWith("calib.");
  // The tested cipher as written (after any ignored symbols are removed), for the glyph views.
  const names = Array.isArray(r.spec.cipher) ? r.spec.cipher : r.spec.cipher ? [r.spec.cipher] : [];
  const opts = status?.options.ciphers ?? [];
  const tested = names.map((n) => {
    let t = opts.find((c) => c.name === n)?.text ?? "";
    for (const d of r.spec.drop_symbols ?? []) t = t.split(d).join("");
    return t;
  });
  const haveText = tested.length > 0 && tested.every((t) => t.length > 0) && tested.join("").length <= 60;
  const best = r.top?.[0];
  // Letters line up with the glyphs only when the cipher was read as written.
  const aligned = haveText && best && best.order.startsWith("identity") && best.plaintext.replaceAll("/", "").length === tested.join("").length
    ? best.plaintext.split("/") : null;

  return (
    <>
      <p className="small"><a href="/results">← All results</a></p>
      <h1>{r.spec.title ?? r.id}</h1>
      <div className="row" style={{ margin: "6px 0 14px" }}>
        <Verdict kind={r.verdictKind} />
        {isAlert(r) && <span className="badge candidate"><span aria-hidden="true">⚑</span>Alert</span>}
        <span className="chip">{cipherLabel(r.spec.cipher)}</span>
        <span className="chip">{LANGS[r.lang ?? "en"]}</span>
        <span className="chip">{r.spec.model ?? "homophonic"} key</span>
        <span className="small muted">finished {relTime(r.finished)} · took {fmtDuration(r.seconds ?? NaN)}</span>
      </div>
      <div className="headline">{VERDICT_HELP[r.verdictKind]}{r.error && <><br /><code>{r.error}</code></>}</div>
      {r.spec.motivation && <p className="lede"><strong>Why test this:</strong> {r.spec.motivation}</p>}

      {!r.error && !r.verdict.startsWith("SKIPPED") && (
        <>
          <div className="grid tiles" style={{ marginTop: 16 }}>
            {isCalib ? (
              <Metric v={r.calib_accuracy !== undefined ? `${(r.calib_accuracy * 100).toFixed(1)}%` : "–"} l="letters recovered" h="must be above 90% to pass" />
            ) : (
              <>
                <Metric v={fmtP(r.p)} l="p" h="share of shuffled copies scoring at least as well" />
                <Metric v={fmtP(r.p_holm)} l="p (Holm)" h="corrected for every test the bot has run" />
                <Metric v={r.power === null ? "–" : r.power.toFixed(2)} l="power" h="how often genuine text would have been detected" />
              </>
            )}
            <Metric v={r.z === null || r.z === undefined ? "–" : Math.abs(r.z) < 0.05 ? "0.0" : (r.z > 0 ? "+" : "") + r.z.toFixed(1)} l="z" h="distance from the shuffled copies, in standard deviations" />
            <Metric v={(r.family_size ?? 1).toLocaleString()} l="variations tried" h="reading orders × pinned-letter sets" />
            <Metric v={String(r.length ?? "–")} l="symbols" h="length of the text searched" />
          </div>

          {!isCalib && r.p_dominance !== undefined && r.p_dominance !== null && (
            <div className="card" style={{ marginTop: 14 }}>
              <h3>Second test: does one reading stand out?</h3>
              <p className="small muted" style={{ marginTop: 0 }}>
                How far the best reading scores above the best <em>clearly different</em> reading, compared the same way with
                shuffled copies and genuine text. Real messages sometimes have one dominant reading where noise has many near-ties.
              </p>
              <div className="row">
                <span><strong>p</strong> {fmtP(r.p_dominance)}</span>
                <span><strong>power</strong> {r.power_dominance === null || r.power_dominance === undefined ? "–" : r.power_dominance.toFixed(2)}</span>
                <span className="small muted">gap {r.dominance?.toFixed(1)} nats</span>
              </div>
              <p className="small muted" style={{ marginBottom: 0 }}>
                {(r.power_dominance ?? 0) < 0.2
                  ? "Low power: this test can't tell either."
                  : (r.p_dominance ?? 1) < 0.05
                    ? "The real cipher's best reading stands out more than chance would give. Treat it as a lead, not a result: this second test is not part of the Holm correction."
                    : "The real cipher's best reading doesn't stand out more than noise."}
              </p>
            </div>
          )}

          {r.null_scores && r.real_score !== undefined && (
            <>
              <h2>Did the real cipher stand out?</h2>
              <p className="small muted">
                Each dot is one complete search. If the orange line sits among the grey dots, the real cipher looks no more like
                text than scrambled copies of itself. If the blue dots also sit among the grey ones, the test could not have told
                anyway (low power).
              </p>
              <div className="card">
                <ScoreChart nulls={r.null_scores} controls={r.control_scores ?? []} real={r.real_score}
                  q95={r.null_q95} length={r.length ?? 1} />
              </div>
            </>
          )}

          {r.top && r.top.length > 0 && (
            <>
              <h2>Best decodes</h2>
              {aligned && (
                <div className="card" style={{ marginBottom: 12 }}>
                  <div className="small muted" style={{ marginBottom: 6 }}>The best decode, letter by letter under each symbol:</div>
                  {tested.map((t, i) => (
                    <CipherGlyphs key={i} text={t} under={aligned[i] ?? ""}
                      rows={names[i]?.split(".")[0] === "z32" && t.length === 32 ? [17, 15] : undefined} />
                  ))}
                </div>
              )}
              <p className="small muted">
                {isCalib
                  ? "The solver's reading of the calibration cipher."
                  : "What the solver read under this hypothesis. Fluent-looking text here proves nothing on its own: shuffled copies produce text that reads just as well, which is what the chart above measures."}
              </p>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>#</th><th>Decoded text</th><th>Variation</th><th className="num">Score</th></tr></thead>
                  <tbody>
                    {r.top.slice(0, 10).map((d, i) => (
                      <tr key={i}>
                        <td className="muted">{i + 1}</td>
                        <td className="decode">{d.plaintext}</td>
                        <td className="small muted">{d.order}</td>
                        <td className="num">{d.score.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      <h2>What was tested</h2>
      <div className="card">
        {haveText && (
          <div style={{ marginBottom: 10 }}>
            {tested.map((t, i) => (
              <CipherGlyphs key={i} text={t} rows={names[i]?.split(".")[0] === "z32" && t.length === 32 ? [17, 15] : undefined} />
            ))}
            {(r.spec.drop_symbols?.length ?? 0) > 0 && <div className="small muted">Shown with the ignored symbols removed.</div>}
          </div>
        )}
        <Describe spec={r.spec} />
      </div>
      <details style={{ marginTop: 10 }}>
        <summary className="small">Exact specification (JSON)</summary>
        <pre>{JSON.stringify(r.spec, null, 2)}</pre>
      </details>

      {related.length > 0 && (
        <>
          <h2>Suggested follow-ups</h2>
          <SuggestionList items={related} admin={admin} writable={canWrite()} />
        </>
      )}
    </>
  );
}

function Metric({ v, l, h }: { v: string; l: string; h: string }) {
  return (
    <div className="card tile">
      <div className="num" style={{ fontSize: "1.5rem" }}>{v}</div>
      <div className="label">{l}</div>
      <div className="hint">{h}</div>
    </div>
  );
}

function Describe({ spec }: { spec: Spec }) {
  const items: [string, React.ReactNode][] = [];
  items.push(["Cipher", spec.synthetic ? `A synthetic ${spec.synthetic.length}-symbol cipher made from held-out ${LANGS[spec.lang ?? "en"]} text` : cipherLabel(spec.cipher)]);
  items.push(["Language", LANGS[spec.lang ?? "en"]]);
  items.push(["Key", spec.model === "simple" ? "One symbol per letter"
    : spec.model === "zodiac" ? "Homophonic, limited to Zodiac's own number of symbols per letter"
    : "Several symbols may share a letter (homophonic)"]);
  items.push(["Scoring", !spec.scorer ? "Letter patterns (5-letter chunks)"
    : `${spec.scorer.ngram ? "Letter patterns + " : ""}whole English words${spec.scorer.zodiac_boost ? ", favouring words Zodiac used in his letters" : ""}`]);
  items.push(["Reading orders", (spec.families ?? ["identity"]).join(", ")]);
  if (spec.drop_symbols?.length) items.push(["Ignored symbols", <code key="d">{spec.drop_symbols.join(" ")}</code>]);
  if (spec.pins && Object.keys(spec.pins).length) items.push(["Fixed letters", <code key="p">{Object.entries(spec.pins).map(([s, l]) => `${s}→${l}`).join("  ")}</code>]);
  if (spec.pin_family) items.push(["Fixed-letter sets", `${spec.pin_family.length} different sets tried`]);
  items.push(["Statistics", `${spec.nulls ?? 19} shuffled copies, ${spec.controls ?? 10} real-text tests, ${spec.restarts ?? 4} restarts per search`]);
  if (spec.source) items.push(["Added by", spec.suggested_by === "zbot" ? "the bot's suggestion, queued by you" : "you (queue file)"]);
  return (
    <dl className="explain" style={{ margin: 0 }}>
      {items.map(([k, v]) => (<div key={k}><dt>{k}</dt><dd>{v}</dd></div>))}
    </dl>
  );
}

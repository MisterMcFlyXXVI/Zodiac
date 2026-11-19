import { loadAll } from "@/lib/data";
import { cipherLabel, fmtDuration, fmtP, isAlert, relTime } from "@/lib/stats";
import Verdict from "@/components/Verdict";
import NowPanel from "@/components/NowPanel";

export const dynamic = "force-dynamic"; // fresh relative times; GitHub data itself is cached 2 min

const LANGS: Record<string, string> = { en: "English", es: "Spanish", fr: "French", de: "German", it: "Italian", vi: "Vietnamese" };

export default async function Overview() {
  const { rows, status, runs, problems } = await loadAll();
  const now = new Date();
  const tests = rows.filter((r) => !r.id.startsWith("calib."));
  const count = (k: string) => tests.filter((r) => r.verdictKind === k).length;
  const alerts = tests.filter(isAlert);
  const candidates = tests.filter((r) => r.verdictKind === "candidate");
  const calib = rows.filter((r) => r.id.startsWith("calib."));
  const recent = [...rows].sort((a, b) => (b.finished ?? "").localeCompare(a.finished ?? "")).slice(0, 8);
  const pendingHours = (status?.pending ?? []).reduce((a, p) => a + (isFinite(p.est_seconds) ? p.est_seconds : 0), 0);

  let headline: React.ReactNode;
  if (alerts.length) {
    headline = (
      <>
        <strong>{alerts.length} result{alerts.length > 1 ? "s" : ""} survive{alerts.length > 1 ? "" : "s"} the statistics.</strong>{" "}
        That is a lead for a human to check, not a solution. <a href="/results?view=alerts">See which</a>.
      </>
    );
  } else if (tests.length) {
    headline = (
      <>
        <strong>No hypothesis has produced a signal that survives correction for multiple testing.</strong>{" "}
        {count("untestable")} of {tests.length} tests were <em>untestable</em>: at 13 or 32 symbols even genuine text
        would not have stood out. That is the expected outcome; see <a href="/guide">why</a>.
      </>
    );
  } else {
    headline = <>No results yet. The bot publishes its first results after its first run.</>;
  }

  return (
    <>
      <h1>Overview</h1>
      <p className="lede">
        zbot tests ideas about how the unsolved Zodiac ciphers Z13 and Z32 were made (key type, reading order,
        transcription, language) and measures whether the real cipher looks any more like text than chance.
      </p>
      {problems.length > 0 && <div className="msg err">Couldn&apos;t load everything: {problems.join("; ")}</div>}
      <div className={`headline ${alerts.length ? "alert" : ""}`}>{headline}</div>

      <div className="grid tiles" style={{ marginTop: 18 }}>
        <Tile num={tests.length} label="Tests run" hint="excluding calibrations" href="/results" />
        <Tile num={count("untestable")} label="Untestable" hint="real text wouldn't stand out" href="/results?verdict=untestable" />
        <Tile num={count("nosignal")} label="No signal" hint="testable, looked like chance" href="/results?verdict=nosignal" />
        <Tile num={candidates.length} label="Candidate signals" hint="before correction" href="/results?verdict=candidate" />
        <Tile num={alerts.length} label="Alerts" hint="survive correction, with power" href="/results?view=alerts" />
        <Tile num={status?.pending.length ?? 0} label="Waiting in queue" hint={`about ${fmtDuration(pendingHours)} of work`} href="/queue" />
      </div>

      <div className="grid two" style={{ marginTop: 14 }}>
        <NowPanel status={status} runs={runs} />
        <div className="card">
          <h3>Calibration</h3>
          <p className="small muted">Before any result in a language counts, the bot must crack a known cipher in that language.</p>
          <table>
            <tbody>
              {Object.entries(LANGS).map(([code, name]) => {
                const r = calib.find((c) => (c.lang ?? "en") === code);
                return (
                  <tr key={code}>
                    <td>{name}</td>
                    <td>{r ? <Verdict kind={r.verdictKind} /> : <span className="muted small">not run yet</span>}</td>
                    <td className="num small muted">{r?.calib_accuracy !== undefined ? `${(r.calib_accuracy * 100).toFixed(1)}% letters` : ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <h2>Latest results</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Hypothesis</th><th>Verdict</th><th className="num">p</th><th className="num">power</th><th>Finished</th></tr>
          </thead>
          <tbody>
            {recent.map((r) => (
              <tr key={r.id}>
                <td>
                  <a href={`/h/${encodeURIComponent(r.id)}`}>{r.spec.title ?? r.id}</a>
                  <div className="small muted">{cipherLabel(r.spec.cipher)} · {LANGS[r.lang ?? "en"]}</div>
                </td>
                <td><Verdict kind={r.verdictKind} /></td>
                <td className="num">{fmtP(r.p)}</td>
                <td className="num">{r.power === null || r.power === undefined ? "–" : r.power.toFixed(2)}</td>
                <td className="small muted">{relTime(r.finished, now)}</td>
              </tr>
            ))}
            {!recent.length && <tr><td colSpan={5} className="muted">Nothing yet.</td></tr>}
          </tbody>
        </table>
      </div>
      <p><a href="/results">All results →</a></p>
    </>
  );
}

function Tile({ num, label, hint, href }: { num: number; label: string; hint: string; href: string }) {
  return (
    <a className="card tile" href={href} style={{ color: "inherit" }}>
      <div className="num">{num}</div>
      <div className="label">{label}</div>
      <div className="hint">{hint}</div>
    </a>
  );
}

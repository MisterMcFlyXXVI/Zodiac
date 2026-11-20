import { fmtDuration, nextScheduled, relTime } from "@/lib/stats";
import type { Status, WorkflowRun } from "@/lib/types";

const LANGS: Record<string, string> = { en: "English", es: "Spanish", fr: "French", de: "German", it: "Italian", vi: "Vietnamese" };

/** What the bot is doing now and what comes next. Server component. */
export default function NowPanel({ status, runs, compact = false }: { status: Status | null; runs: WorkflowRun[]; compact?: boolean }) {
  const now = new Date();
  const active = runs.find((r) => r.status !== "completed");
  const last = runs.find((r) => r.status === "completed");
  const cur = active ? status?.current : null;
  const elapsed = cur ? (now.getTime() - new Date(cur.started).getTime()) / 1000 : 0;
  const frac = cur && isFinite(cur.est_seconds) && cur.est_seconds > 0 ? Math.min(1, elapsed / cur.est_seconds) : 0;
  const over = cur && isFinite(cur.est_seconds) && elapsed > cur.est_seconds * 1.5;
  const next = (status?.pending ?? []).filter((p) => p.id !== cur?.id).slice(0, compact ? 2 : 4);
  const sched = nextScheduled(now);

  return (
    <div className="card stack">
      <div className="row">
        <h3 style={{ margin: 0 }}>Right now</h3>
        <span className="spacer" />
        {active ? (
          <span className="badge pass"><span aria-hidden="true">●</span>Running</span>
        ) : (
          <span className="badge nosignal"><span aria-hidden="true">○</span>Idle</span>
        )}
      </div>

      {active && cur && (
        <div>
          <div className="small muted">Working on</div>
          <div><a href={`/queue`}>{cur.title}</a> <span className="chip">{LANGS[cur.lang] ?? cur.lang}</span></div>
          <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(frac * 100)}
            aria-label="Progress against the estimate">
            <span style={{ width: `${Math.max(3, frac * 100)}%` }} />
          </div>
          <div className="small muted">
            started {relTime(cur.started, now)} · estimated {fmtDuration(cur.est_seconds)}
            {over ? " · taking longer than estimated (estimates are rough)" : ""}
          </div>
        </div>
      )}
      {active && !cur && (
        <p className="small" style={{ margin: 0 }}>
          A run started {relTime(active.run_started_at ?? active.created_at, now)}. It reports what it is working on within
          about 10 minutes of starting.
        </p>
      )}
      {!active && (
        <p className="small" style={{ margin: 0 }}>
          {last ? <>Last run finished {relTime(last.updated_at, now)}. </> : null}
          Runs normally follow each other back to back, so a gap usually means the last one failed or GitHub was slow
          to start the next. Start one from the Queue page, or the daily restart will at {sched.toUTCString().slice(17, 22)} UTC
          ({relTime(sched.toISOString(), now)}).
        </p>
      )}

      {next.length > 0 && (
        <div>
          <div className="small muted">Up next</div>
          <ol className="small" style={{ margin: "4px 0 0", paddingLeft: 20 }}>
            {next.map((p) => (
              <li key={p.id}>
                {p.title} <span className="muted">· {fmtDuration(p.est_seconds)}{p.source === "queue" ? " · queued by you" : ""}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
      <div className="row small">
        {active && <a href={active.html_url} target="_blank" rel="noreferrer">Live log on GitHub ↗</a>}
        <span className="spacer" />
        <span className="muted">5.5-hour runs, back to back{status?.generated ? ` · updated ${relTime(status.generated, now)}` : ""}</span>
      </div>
    </div>
  );
}

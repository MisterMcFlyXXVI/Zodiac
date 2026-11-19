import { loadAll } from "@/lib/data";
import { isAdmin } from "@/lib/auth";
import { canWrite, getQueue } from "@/lib/github";
import { estimateSeconds, fmtDuration, relTime } from "@/lib/stats";
import Login from "@/components/Login";
import RunNow from "@/components/RunNow";
import SuggestionList from "@/components/SuggestionList";
import QueueList, { type QueueItem } from "@/components/QueueList";
import AddForm from "@/components/AddForm";

export const dynamic = "force-dynamic";

const LANGS: Record<string, string> = { en: "English", es: "Spanish", fr: "French", de: "German", it: "Italian", vi: "Vietnamese" };

export default async function QueuePage() {
  const [{ rows, status, runs, problems }, admin, queue] = await Promise.all([
    loadAll(), isAdmin(), getQueue().catch(() => []),
  ]);
  const writable = canWrite();
  const active = runs.find((r) => r.status !== "completed");
  const byId = new Map(rows.map((r) => [r.id, r]));
  const pendingById = new Map((status?.pending ?? []).map((p) => [p.id, p]));
  const opt = status?.options;

  const mine: QueueItem[] = queue.map((q) => {
    const r = byId.get(q.id);
    const p = pendingById.get(q.id);
    const cipher = opt?.ciphers.find((c) => c.name === (Array.isArray(q.spec?.cipher) ? q.spec?.cipher[0] : q.spec?.cipher));
    const refused = r?.verdict?.startsWith("SKIPPED: invalid");
    return {
      name: q.name, sha: q.sha, id: q.id, title: q.spec?.title ?? q.id,
      state: refused ? "refused" : r ? "done" : "waiting",
      verdict: r?.verdict,
      problems: refused ? [r!.verdict.replace("SKIPPED: invalid spec: ", "")] : p?.problems,
      est: p?.est_seconds ?? (cipher && q.spec ? estimateSeconds(q.spec, cipher) : NaN),
    };
  });
  const queuedIds = new Set(queue.map((q) => q.id));
  const builtinPending = (status?.pending ?? []).filter((p) => p.source === "built-in");
  const builtinHours = builtinPending.reduce((a, p) => a + (isFinite(p.est_seconds) ? p.est_seconds : 0), 0);

  return (
    <>
      <h1>Queue &amp; ideas</h1>
      <p className="lede">
        Give the bot more work: queue one of its own suggestions, or describe a new test. Work you add runs first,
        at the start of the next run.
      </p>
      {problems.length > 0 && <div className="msg err">{problems.join("; ")}</div>}
      <div className="card"><Login admin={admin} configured={writable} /></div>

      <h2>Run the bot</h2>
      <div className="card">
        <p style={{ marginTop: 0 }}>
          {active
            ? <>A run is going now (started {relTime(active.run_started_at ?? active.created_at)}). <a href={active.html_url} target="_blank" rel="noreferrer">Watch it on GitHub ↗</a></>
            : <>No run is going right now. Scheduled runs start every 6 hours; you can start one sooner.</>}
        </p>
        <RunNow enabled={admin && writable} busy={Boolean(active)} />
      </div>

      <h2>The bot&apos;s suggestions</h2>
      <p className="small muted">
        Generated after every test from what has been run so far: follow-ups on anything that came close, checks of how robust it
        is, gaps in coverage, and new combinations. Each is a ready-made test.
      </p>
      {status ? <SuggestionList items={status.suggestions.filter((x) => !queuedIds.has(x.spec.id) && !byId.has(x.spec.id))} admin={admin} writable={writable} /> :
        <p className="muted">The bot has not published suggestions yet; they appear after its next run.</p>}

      <h2>Your queue</h2>
      <QueueList items={mine} admin={admin} writable={writable} />

      <h2>Add your own test</h2>
      {opt ? <AddForm options={opt} admin={admin} writable={writable} /> : <p className="muted">Available once the bot has published its status.</p>}

      <h2>Built-in plan</h2>
      <p className="small muted">
        {builtinPending.length
          ? <>{builtinPending.length} built-in tests left, about {fmtDuration(builtinHours)} of work. After that the bot explores on its own{status?.explore_next ? <> (next: <em>{status.explore_next}</em>)</> : null}.</>
          : <>The built-in plan is finished; the bot is exploring{status?.explore_next ? <> (next: <em>{status.explore_next}</em>)</> : null}. Your own tests always go first.</>}
      </p>
      {builtinPending.length > 0 && (
        <details open={builtinPending.length <= 6}>
        <summary className="small">Show all {builtinPending.length} built-in tests</summary>
        <div className="table-wrap" style={{ marginTop: 8 }}>
          <table>
            <thead><tr><th>Test</th><th>Language</th><th className="num">Estimate</th></tr></thead>
            <tbody>
              {builtinPending.map((p) => (
                <tr key={p.id}><td>{p.title}<div className="small muted mono">{p.id}</div></td><td>{LANGS[p.lang] ?? p.lang}</td><td className="num">{fmtDuration(p.est_seconds)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        </details>
      )}
    </>
  );
}

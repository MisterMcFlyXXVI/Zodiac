"use client";
import { useState } from "react";
import { call } from "@/lib/client";
import { fmtDuration } from "@/lib/stats";

export type QueueItem = {
  name: string; sha: string; id: string; title: string;
  state: "waiting" | "done" | "refused"; verdict?: string; problems?: string[]; est: number;
};

export default function QueueList({ items, admin, writable }: { items: QueueItem[]; admin: boolean; writable: boolean }) {
  const [gone, setGone] = useState<Set<string>>(new Set());
  const [err, setErr] = useState("");
  const shown = items.filter((i) => !gone.has(i.name));
  if (!shown.length) return <p className="muted">Nothing queued by you yet. Queue a suggestion or add your own below.</p>;
  return (
    <>
      {err && <div className="msg err">{err}</div>}
      <div className="table-wrap">
        <table>
          <thead><tr><th>Hypothesis</th><th>State</th><th className="num">Estimate</th><th /></tr></thead>
          <tbody>
            {shown.map((i) => (
              <tr key={i.name}>
                <td>
                  {i.state === "done" ? <a href={`/h/${encodeURIComponent(i.id)}`}>{i.title}</a> : i.title}
                  <div className="small muted mono">{i.id}</div>
                  {i.problems && <div className="small" style={{ color: "var(--critical-ink)" }}>Refused: {i.problems.join("; ")}</div>}
                </td>
                <td className="small">
                  {i.state === "waiting" && "Waiting for the next run"}
                  {i.state === "done" && <>Done: {i.verdict?.split(":")[0]}</>}
                  {i.state === "refused" && "Refused by the bot"}
                </td>
                <td className="num small">{fmtDuration(i.est)}</td>
                <td>
                  {i.state !== "done" && (
                    <button className="btn ghost small" disabled={!admin || !writable} onClick={async () => {
                      if (!confirm(`Remove ${i.id} from the queue?`)) return;
                      const r = await call("/api/queue", "DELETE", { name: i.name, sha: i.sha });
                      if (r.ok) setGone((g) => new Set(g).add(i.name)); else setErr(String(r.data.error));
                    }}>Remove</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

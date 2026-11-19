"use client";
import { useState } from "react";
import { call } from "@/lib/client";
import { fmtDuration } from "@/lib/stats";
import type { Suggestion } from "@/lib/types";

const KIND: Record<string, string> = {
  "follow-up": "Follow-up", robustness: "Robustness check", coverage: "Gap in coverage", idea: "New idea",
};

export default function SuggestionList({ items, admin, writable }: { items: Suggestion[]; admin: boolean; writable: boolean }) {
  const [state, setState] = useState<Record<string, { ok: boolean; text: string } | "busy">>({});
  if (!items.length) return <p className="muted">No suggestions right now.</p>;
  return (
    <div className="grid two">
      {items.map((s) => {
        const st = state[s.spec.id];
        return (
          <div className="card stack" key={s.spec.id}>
            <div className="row">
              <span className="chip">{KIND[s.kind] ?? s.kind}</span>
              <span className="spacer" />
              <span className="small muted">≈ {fmtDuration(s.est_seconds)}</span>
            </div>
            <h3>{s.spec.title}</h3>
            <p className="small" style={{ margin: 0 }}>{s.why}</p>
            <details><summary className="small">Details</summary><pre>{JSON.stringify(s.spec, null, 2)}</pre></details>
            <div className="row">
              <button className="btn small" disabled={!admin || !writable || st === "busy" || (typeof st === "object" && st.ok)}
                onClick={async () => {
                  setState((x) => ({ ...x, [s.spec.id]: "busy" }));
                  const r = await call("/api/queue", "POST", { spec: s.spec });
                  setState((x) => ({ ...x, [s.spec.id]: { ok: r.ok, text: r.ok ? "Queued. The next run picks it up." : String(r.data.error) } }));
                }}>
                {typeof st === "object" && st.ok ? "Queued ✓" : "Queue this"}
              </button>
              {typeof st === "object" && <span className={`small ${st.ok ? "" : "msg err"}`}>{st.text}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

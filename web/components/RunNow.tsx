"use client";
import { useState } from "react";
import { call } from "@/lib/client";

export default function RunNow({ enabled, busy }: { enabled: boolean; busy: boolean }) {
  const [hours, setHours] = useState("5.5");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [sending, setSending] = useState(false);
  return (
    <div>
      <div className="row">
        <select aria-label="How long to run" value={hours} onChange={(e) => setHours(e.target.value)} style={{ width: 150 }}>
          {["0.5", "1", "2", "3", "4", "5.5"].map((h) => <option key={h} value={h}>{h} hours</option>)}
        </select>
        <button className="btn" disabled={!enabled || sending} onClick={async () => {
          setSending(true);
          const r = await call("/api/run", "POST", { hours: Number(hours) });
          setSending(false);
          setMsg({ ok: r.ok, text: String(r.ok ? r.data.note : r.data.error) });
        }}>{busy ? "Queue another run" : "Start a run now"}</button>
      </div>
      {!enabled && <p className="small muted">Unlock above to use this.</p>}
      {msg && <div className={`msg ${msg.ok ? "ok" : "err"}`}>{msg.text}</div>}
    </div>
  );
}

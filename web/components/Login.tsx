"use client";
import { useState } from "react";
import { call } from "@/lib/client";

export default function Login({ admin, configured }: { admin: boolean; configured: boolean }) {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  if (!configured)
    return (
      <div className="msg info">
        Read-only: the buttons that change things are switched off until <code>GITHUB_TOKEN</code> and{" "}
        <code>ADMIN_PASSWORD</code> are set in Vercel. See <code>web/README.md</code>.
      </div>
    );
  if (admin)
    return (
      <div className="row small">
        <span className="badge pass"><span aria-hidden="true">✓</span>Unlocked</span>
        <button className="btn ghost small" onClick={async () => { await call("/api/logout", "POST"); location.reload(); }}>Lock</button>
      </div>
    );
  return (
    <form className="row" onSubmit={async (e) => {
      e.preventDefault(); setBusy(true); setErr("");
      const r = await call("/api/login", "POST", { password: pw });
      setBusy(false);
      if (r.ok) location.reload(); else setErr(String(r.data.error ?? "failed"));
    }}>
      <div style={{ width: 220 }}>
        <label htmlFor="pw" className="small">Password to unlock buttons</label>
        <input id="pw" type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" />
      </div>
      <button className="btn" disabled={busy || !pw} style={{ alignSelf: "end" }}>Unlock</button>
      {err && <span className="msg err" style={{ alignSelf: "end" }}>{err}</span>}
    </form>
  );
}

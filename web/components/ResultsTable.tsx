"use client";
import { useMemo, useState } from "react";
import Verdict from "./Verdict";
import type { VerdictKind } from "@/lib/types";
import { fmtP, relTime } from "@/lib/stats";

export type SlimRow = {
  id: string; title: string; cipher: string; base: string; lang: string; model: string;
  kind: VerdictKind; p: number | null; p_holm: number | null; power: number | null; z: number | null;
  family: number; best: string; finished: string; alert: boolean; calib: boolean; queued: boolean;
};
type SortKey = "finished" | "p" | "power" | "title";

const LANGS: Record<string, string> = { en: "English", es: "Spanish", fr: "French", de: "German", it: "Italian", vi: "Vietnamese" };
const KINDS: [string, string][] = [
  ["", "Any verdict"], ["candidate", "Candidate signal"], ["nosignal", "No signal"], ["untestable", "Untestable"],
  ["pass", "Calibration passed"], ["fail", "Calibration failed"], ["skipped", "Skipped"], ["error", "Error"],
];

export default function ResultsTable({ rows, initial }: {
  rows: SlimRow[];
  initial: { verdict: string; view: string; q: string; cipher: string; lang: string };
}) {
  const [q, setQ] = useState(initial.q);
  const [verdict, setVerdict] = useState(initial.verdict);
  const [cipher, setCipher] = useState(initial.cipher);
  const [lang, setLang] = useState(initial.lang);
  const [alertsOnly, setAlertsOnly] = useState(initial.view === "alerts");
  const [hideCalib, setHideCalib] = useState(true);
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({ key: "finished", asc: false });

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const out = rows.filter((r) =>
      (!needle || `${r.id} ${r.title} ${r.best}`.toLowerCase().includes(needle)) &&
      (!verdict || r.kind === verdict) &&
      (!cipher || r.base === cipher) &&
      (!lang || r.lang === lang) &&
      (!alertsOnly || r.alert) &&
      (!hideCalib || !r.calib || verdict === "pass" || verdict === "fail"),
    );
    const val = (r: SlimRow) => (sort.key === "title" ? r.title : sort.key === "finished" ? r.finished : (r[sort.key] ?? Infinity));
    out.sort((a, b) => {
      const x = val(a), y = val(b);
      const c = typeof x === "string" ? x.localeCompare(y as string) : (x as number) - (y as number);
      return sort.asc ? c : -c;
    });
    return out;
  }, [rows, q, verdict, cipher, lang, alertsOnly, hideCalib, sort]);

  const head = (key: SortKey, label: string, num = false) => (
    <th className={num ? "num" : undefined} aria-sort={sort.key === key ? (sort.asc ? "ascending" : "descending") : "none"}>
      <button onClick={() => setSort({ key, asc: sort.key === key ? !sort.asc : key !== "finished" })}>
        {label} {sort.key === key ? (sort.asc ? "▲" : "▼") : ""}
      </button>
    </th>
  );
  const now = new Date();

  return (
    <>
      <div className="filters">
        <div style={{ flex: 2, minWidth: 220 }}>
          <label htmlFor="q">Search</label>
          <input id="q" type="text" placeholder="name, id or decoded text" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div>
          <label htmlFor="v">Verdict</label>
          <select id="v" value={verdict} onChange={(e) => setVerdict(e.target.value)}>
            {KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="c">Cipher</label>
          <select id="c" value={cipher} onChange={(e) => setCipher(e.target.value)}>
            <option value="">Any cipher</option>
            <option value="z13">Z13</option>
            <option value="z32">Z32</option>
            <option value="joint">Z13 + Z32 together</option>
            <option value="z408">Z408</option>
            <option value="z340">Z340</option>
          </select>
        </div>
        <div>
          <label htmlFor="l">Language</label>
          <select id="l" value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="">Any language</option>
            {Object.entries(LANGS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </div>
        <div style={{ minWidth: 0 }}>
          <label style={{ fontWeight: 400 }}><input type="checkbox" checked={alertsOnly} onChange={(e) => setAlertsOnly(e.target.checked)} /> Alerts only</label>
          <label style={{ fontWeight: 400 }}><input type="checkbox" checked={hideCalib} onChange={(e) => setHideCalib(e.target.checked)} /> Hide calibrations</label>
        </div>
      </div>
      <p className="small muted">{shown.length} of {rows.length} shown. p (Holm) is corrected for every test the bot has run; power says whether the test could have seen anything.</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {head("title", "Hypothesis")}
              <th>Verdict</th>
              {head("p", "p", true)}
              <th className="num">p (Holm)</th>
              {head("power", "power", true)}
              <th>Best decode</th>
              {head("finished", "Finished")}
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id}>
                <td style={{ minWidth: 220 }}>
                  <a href={`/h/${encodeURIComponent(r.id)}`}>{r.title}</a>
                  <div className="small muted">
                    {r.cipher} · {LANGS[r.lang] ?? r.lang} · {r.model}
                    {r.family > 1 ? ` · ${r.family.toLocaleString()} variations` : ""}
                    {r.queued ? " · you queued this" : ""}
                  </div>
                </td>
                <td><Verdict kind={r.kind} />{r.alert && <div className="small" style={{ marginTop: 4 }}>⚑ alert</div>}</td>
                <td className="num">{fmtP(r.p)}</td>
                <td className="num">{fmtP(r.p_holm)}</td>
                <td className="num">{r.power === null ? "–" : r.power.toFixed(2)}</td>
                <td className="decode" style={{ maxWidth: 260 }}>{r.best.slice(0, 48)}{r.best.length > 48 ? "…" : ""}</td>
                <td className="small muted" style={{ whiteSpace: "nowrap" }}>{relTime(r.finished, now)}</td>
              </tr>
            ))}
            {!shown.length && <tr><td colSpan={7} className="muted">No results match these filters.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}

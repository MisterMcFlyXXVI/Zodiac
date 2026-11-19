"use client";
import { useState } from "react";

type Pt = { x: number; row: 0 | 1; label: string; jitter: number };

const W = 760;
const H = 190;
const M = { l: 150, r: 24, t: 30, b: 42 };
const ROWS = [
  { y: 62, name: "Shuffled copies", sub: "(nulls)" },
  { y: 122, name: "Real text, same pattern", sub: "(controls)" },
];

function ticks(lo: number, hi: number, n = 5): number[] {
  const step0 = (hi - lo) / n;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= step0) ?? step0;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

/** Deterministic jitter so dots with equal scores don't hide each other. */
const jit = (i: number) => (((i * 7919) % 23) / 22 - 0.5) * 22;

export default function ScoreChart({ nulls, controls, real, q95, length }: {
  nulls: number[]; controls: number[]; real: number; q95?: number; length: number;
}) {
  const [hover, setHover] = useState<{ x: number; y: number; text: string } | null>(null);
  const pts: Pt[] = [
    ...nulls.map((v, i) => ({ x: v, row: 0 as const, label: `Shuffled copy ${i + 1}`, jitter: jit(i) })),
    ...controls.map((v, i) => ({ x: v, row: 1 as const, label: `Real-text test ${i + 1}`, jitter: jit(i + 101) })),
  ];
  const all = [...nulls, ...controls, real, ...(q95 !== undefined && isFinite(q95) ? [q95] : [])];
  let lo = Math.min(...all), hi = Math.max(...all);
  const pad = (hi - lo) * 0.06 || 1;
  lo -= pad; hi += pad;
  const sx = (v: number) => M.l + ((v - lo) / (hi - lo)) * (W - M.l - M.r);
  const fmt = (v: number) => `${v.toFixed(1)} (${(v / length).toFixed(2)} per letter)`;
  const show = (e: React.MouseEvent | React.FocusEvent, text: string, x: number, y: number) => {
    const svg = (e.currentTarget as SVGElement).ownerSVGElement!;
    const r = svg.getBoundingClientRect();
    setHover({ x: (x / W) * r.width, y: (y / H) * r.height, text });
  };

  return (
    <div>
      <div className="legend" aria-hidden="true">
        <span><i style={{ background: "var(--null-dot)" }} />Shuffled copies of the cipher</span>
        {controls.length > 0 && <span><i style={{ background: "var(--series-control)" }} />Genuine text with the same repeat pattern</span>}
        <span><i className="bar" style={{ background: "var(--series-real)" }} />The real cipher</span>
        {q95 !== undefined && isFinite(q95) && <span><i className="dash" />95% of shuffled copies score below</span>}
      </div>
      <div className="chart" onMouseLeave={() => setHover(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img"
          aria-label={`Real cipher scores ${real.toFixed(1)}; shuffled copies range ${Math.min(...nulls).toFixed(1)} to ${Math.max(...nulls).toFixed(1)}`}>
          {ROWS.slice(0, controls.length ? 2 : 1).map((r) => (
            <g key={r.name}>
              <line x1={M.l} x2={W - M.r} y1={r.y} y2={r.y} stroke="var(--border)" />
              <text className="rowlabel" x={M.l - 12} y={r.y - 2} textAnchor="end">{r.name}</text>
              <text className="rowlabel" x={M.l - 12} y={r.y + 13} textAnchor="end" style={{ fill: "var(--muted)" }}>{r.sub}</text>
            </g>
          ))}
          <g className="axis">
            <line x1={M.l} x2={W - M.r} y1={H - M.b} y2={H - M.b} />
            {ticks(lo, hi).map((t) => (
              <g key={t}>
                <line x1={sx(t)} x2={sx(t)} y1={H - M.b} y2={H - M.b + 4} />
                <text x={sx(t)} y={H - M.b + 17} textAnchor="middle">{t}</text>
              </g>
            ))}
            <text x={(M.l + W - M.r) / 2} y={H - 4} textAnchor="middle">
              score (log-probability) → further right means more like real text
            </text>
          </g>
          {q95 !== undefined && isFinite(q95) && (
            <line x1={sx(q95)} x2={sx(q95)} y1={M.t + 8} y2={H - M.b} stroke="var(--muted)" strokeWidth={1.5} strokeDasharray="4 4" />
          )}
          {pts.map((p, i) => {
            const cx = sx(p.x), cy = ROWS[p.row].y + p.jitter * 0.6;
            return (
              <g key={i}>
                <circle cx={cx} cy={cy} r={5} fill={p.row === 0 ? "var(--null-dot)" : "var(--series-control)"}
                  stroke="var(--surface)" strokeWidth={2} />
                <circle cx={cx} cy={cy} r={11} fill="transparent" tabIndex={0}
                  onMouseEnter={(e) => show(e, `${p.label}: ${fmt(p.x)}`, cx, cy)}
                  onFocus={(e) => show(e, `${p.label}: ${fmt(p.x)}`, cx, cy)}
                  onBlur={() => setHover(null)} />
              </g>
            );
          })}
          <line x1={sx(real)} x2={sx(real)} y1={M.t} y2={H - M.b} stroke="var(--series-real)" strokeWidth={3} strokeLinecap="round" />
          <text className="reallabel" x={sx(real)} y={M.t - 8} textAnchor={sx(real) > W - 140 ? "end" : "middle"}>
            Real cipher
          </text>
          <rect x={sx(real) - 9} y={M.t} width={18} height={H - M.b - M.t} fill="transparent"
            onMouseEnter={(e) => show(e, `Real cipher: ${fmt(real)}`, sx(real), M.t + 20)} />
        </svg>
        {hover && <div className="tooltip" style={{ left: hover.x, top: hover.y }}>{hover.text}</div>}
      </div>
      <details style={{ marginTop: 6 }}>
        <summary className="small">Show the numbers as a table</summary>
        <div className="table-wrap" style={{ marginTop: 8, maxHeight: 280, overflowY: "auto" }}>
          <table>
            <thead><tr><th>What</th><th className="num">Score</th><th className="num">Per letter</th></tr></thead>
            <tbody>
              <tr><td><strong>Real cipher</strong></td><td className="num">{real.toFixed(2)}</td><td className="num">{(real / length).toFixed(3)}</td></tr>
              {pts.map((p, i) => (
                <tr key={i}><td>{p.label}</td><td className="num">{p.x.toFixed(2)}</td><td className="num">{(p.x / length).toFixed(3)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

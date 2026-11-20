import { glyphInfo, type Shape } from "@/lib/glyphs";

// One cipher symbol drawn as it appears in the letters. Unknown codes (most of Z408/Z340's
// alphabet) fall back to the transcription code in a dashed box.

const S = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" } as const;

function ShapeSvg({ shape }: { shape: Shape }) {
  switch (shape) {
    case "crosshair":
      return <><circle cx={12} cy={14} r={6} {...S} /><path d="M12 4 V24 M2 14 H22" {...S} /></>;
    case "circle8":
      return <><circle cx={12} cy={14} r={8.5} {...S} strokeWidth={2.6} /><circle cx={12} cy={10.6} r={2.3} {...S} strokeWidth={1.4} /><path d="M7.6 14.4 Q12 12.6 16.4 14.4 M12 13.5 V20.5" {...S} strokeWidth={1.4} /></>;
    case "hookT":
      return <path d="M12 5 V21.5 M6.5 20 Q6.5 21.5 8 21.5 H15.5 Q18.5 21.5 18.5 17.5" {...S} />;
    case "perpT":
      return <path d="M12 5 V21.5 M5 21.5 H19" {...S} />;
    case "triOpen":
      return <path d="M12 5 L20.5 21.5 H3.5 Z" {...S} />;
    case "triFilled":
      return <path d="M12 5 L20.5 21.5 H3.5 Z" {...S} fill="currentColor" />;
    case "bar":
      return <path d="M12 5 V22" {...S} />;
    case "squareFilled":
      return <rect x={5} y={7} width={14} height={14} fill="currentColor" stroke="currentColor" strokeWidth={1.2} />;
    case "squareHalf":
      return <><rect x={5} y={7} width={14} height={14} {...S} /><path d="M19 7 V21 H5 Z" fill="currentColor" /></>;
    case "omega":
      return <path d="M4 21.5 H9 C5.5 19 4.5 16 4.5 13 A7.5 7.5 0 0 1 19.5 13 C19.5 16 18.5 19 15 21.5 H20" {...S} />;
    case "circleDot":
      return <><circle cx={12} cy={14} r={7.5} {...S} /><circle cx={12} cy={14} r={2.2} fill="currentColor" /></>;
    case "tau":
      return <path d="M5 8.5 V6 H19 M12 6 V17.5 Q12 22 17 21.5" {...S} />;
  }
}

export default function Glyph({ code, size = 24, title = true }: { code: string; size?: number; title?: boolean }) {
  const g = glyphInfo(code);
  const h = (size * 28) / 24;
  const label = g ? `${g.name} (code ${code}): ${g.desc}` : `Transcription code ${code}`;
  return (
    <svg className="glyph" width={size} height={h} viewBox="0 0 24 28" role="img" aria-label={label}>
      {title && <title>{label}</title>}
      {!g && (
        <>
          <rect x={2} y={3} width={20} height={22} rx={3} fill="none" stroke="currentColor" strokeOpacity={0.35} strokeDasharray="2 2" />
          <text x={12} y={19} textAnchor="middle" fontSize={13} fontFamily="ui-monospace, monospace" fill="currentColor">{code}</text>
        </>
      )}
      {g?.kind === "letter" && (
        <text x={12} y={21.5} textAnchor="middle" fontSize={g.serif ? 19 : 18} fill="currentColor"
          fontFamily={g.serif ? "Georgia, 'Times New Roman', serif" : "'Arial Narrow', Arial, Helvetica, sans-serif"}
          fontWeight={g.serif ? 400 : 500}
          transform={g.mirror ? "translate(24 0) scale(-1 1)" : undefined}>
          {g.ch}
        </text>
      )}
      {g?.kind === "shape" && <ShapeSvg shape={g.shape} />}
      {g?.kind === "shape" && g.mark && (
        <text x={21.5} y={8} fontSize={7} textAnchor="middle" fill="currentColor">{g.mark}</text>
      )}
    </svg>
  );
}

/** A whole cipher as glyphs. `rows` splits it into lines (e.g. Z32's 17 + 15); `under` puts a letter under each glyph. */
export function CipherGlyphs({ text, rows, under, size = 24 }: { text: string; rows?: number[]; under?: string; size?: number }) {
  const lines: [number, number][] = [];
  if (rows && rows.reduce((a, b) => a + b, 0) === text.length) {
    let i = 0;
    for (const r of rows) { lines.push([i, i + r]); i += r; }
  } else lines.push([0, text.length]);
  return (
    <div className="cipher-glyphs">
      {lines.map(([a, b], li) => (
        <div className="cipher-row" key={li}>
          {[...text.slice(a, b)].map((c, k) => (
            <span className="cell" key={k}>
              <Glyph code={c} size={size} />
              {under !== undefined && <span className="under">{under[a + k] ?? ""}</span>}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}

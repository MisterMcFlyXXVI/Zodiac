"use client";
import { useMemo, useState } from "react";
import { call } from "@/lib/client";
import { estimateSeconds, fmtDuration } from "@/lib/stats";
import { checkSpec, slugify } from "@/lib/validate";
import type { Options, Spec } from "@/lib/types";
import Glyph, { CipherGlyphs } from "./Glyph";

const PRESETS: { label: string; apply: Partial<Spec> }[] = [
  { label: "Z13, one symbol per letter", apply: { cipher: "z13", model: "simple", families: ["identity"] } },
  { label: "Z32 in another language", apply: { cipher: "z32", model: "homophonic", lang: "es", families: ["identity"] } },
  { label: "Z13 read in a different order", apply: { cipher: "z13", model: "simple", families: ["reverse", "decimations", "railfences"] } },
  { label: "Z32 with a symbol ignored", apply: { cipher: "z32", model: "homophonic", drop_symbols: ["z"] } },
];

export default function AddForm({ options, admin, writable }: { options: Options; admin: boolean; writable: boolean }) {
  const [title, setTitle] = useState("");
  const [motivation, setMotivation] = useState("");
  const [cipher, setCipher] = useState("z13");
  const [model, setModel] = useState<"homophonic" | "simple">("simple");
  const [lang, setLang] = useState("en");
  const [families, setFamilies] = useState<string[]>(["identity"]);
  const [drops, setDrops] = useState<string[]>([]);
  const [pins, setPins] = useState<Record<string, string>>({});
  const [nulls, setNulls] = useState(19);
  const [controls, setControls] = useState(10);
  const [restarts, setRestarts] = useState(4);
  const [stamp] = useState(() => new Date().toISOString().slice(2, 16).replace(/[-:T]/g, ""));
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const c = options.ciphers.find((x) => x.name === cipher)!;
  const symbols = useMemo(() => [...new Set(c.text)].sort(), [c]);
  const unsolved = options.ciphers.filter((x) => !x.solved);
  const solved = options.ciphers.filter((x) => x.solved);

  const spec: Spec = useMemo(() => {
    const s: Spec = {
      id: `user.${slugify(title || `${cipher}-${model}-${lang}`)}-${stamp}`,
      title: title.trim() || `${cipher.toUpperCase()} as ${options.languages[lang]}, ${model} key`,
      motivation: motivation.trim() || undefined,
      cipher, model, lang,
    };
    if (!(families.length === 1 && families[0] === "identity")) s.families = families.length ? families : ["identity"];
    if (drops.length) s.drop_symbols = drops;
    const p = Object.fromEntries(Object.entries(pins).filter(([sym, l]) => l && !drops.includes(sym)));
    if (Object.keys(p).length) s.pins = p;
    if (nulls !== 19) s.nulls = nulls;
    if (controls !== 10) s.controls = controls;
    if (restarts !== 4) s.restarts = restarts;
    return JSON.parse(JSON.stringify(s)) as Spec; // drop undefined
  }, [title, motivation, cipher, model, lang, families, drops, pins, nulls, controls, restarts, stamp, options]);

  const problems = checkSpec(spec, options);
  const est = estimateSeconds(spec, c);
  const tooSimple = model === "simple" && c.distinct - drops.length > 26;

  const applyPreset = (p: Partial<Spec>) => {
    if (p.cipher) setCipher(p.cipher as string);
    if (p.model) setModel(p.model);
    if (p.lang) setLang(p.lang);
    setFamilies(p.families ?? ["identity"]);
    setDrops(p.drop_symbols ?? []);
    setPins({});
  };

  return (
    <form className="card" onSubmit={async (e) => {
      e.preventDefault();
      setBusy(true); setResult(null);
      const r = await call("/api/queue", "POST", { spec });
      setBusy(false);
      setResult({ ok: r.ok, text: r.ok ? `Queued as ${spec.id}. The next run starts on it before anything else.` : String(r.data.error) });
    }}>
      <div className="field">
        <label>Start from an example (optional)</label>
        <div className="row">
          {PRESETS.map((p) => <button type="button" key={p.label} className="btn ghost small" onClick={() => applyPreset(p.apply)}>{p.label}</button>)}
        </div>
      </div>

      <div className="grid two">
        <div className="field">
          <label htmlFor="f-cipher">Cipher</label>
          <select id="f-cipher" value={cipher} onChange={(e) => { setCipher(e.target.value); setDrops([]); setPins({}); }}>
            <optgroup label="Unsolved">
              {unsolved.map((x) => <option key={x.name} value={x.name}>{label(x.name)} — {x.length} symbols, {x.distinct} different</option>)}
            </optgroup>
            <optgroup label="Solved (for experiments)">
              {solved.map((x) => <option key={x.name} value={x.name}>{label(x.name)} — {x.length} symbols</option>)}
            </optgroup>
          </select>
          <div className="help" style={{ marginTop: 6 }}>
            {c.length <= 40
              ? <CipherGlyphs text={c.text} rows={c.name.startsWith("z32") && c.length === 32 ? [17, 15] : undefined} size={20} />
              : <span className="mono" style={{ wordBreak: "break-all" }}>{c.text.slice(0, 40)}… (shown as transcription codes)</span>}
          </div>
        </div>
        <div className="field">
          <label htmlFor="f-lang">Language of the hidden message</label>
          <select id="f-lang" value={lang} onChange={(e) => setLang(e.target.value)}>
            {Object.entries(options.languages).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <div className="help">Accents are ignored; text is reduced to A–Z.</div>
        </div>
      </div>

      <div className="field">
        <label>Key type</label>
        <div className="checks">
          {Object.entries(options.models).map(([k, help]) => (
            <label key={k}>
              <input type="radio" name="model" checked={model === k} onChange={() => setModel(k as "homophonic" | "simple")}
                disabled={k === "simple" && c.distinct - drops.length > 26} />
              <span><strong>{k}</strong><br /><span className="small muted">{help}</span></span>
            </label>
          ))}
        </div>
        {tooSimple && <div className="help">This cipher has more than 26 different symbols, so one-symbol-per-letter is impossible.</div>}
      </div>

      <div className="field">
        <label>Reading orders to try</label>
        <div className="checks">
          {Object.entries(options.families).map(([k, help]) => {
            const n = c.family_sizes[k];
            if (n === undefined || n === 0) return null;
            return (
              <label key={k}>
                <input type="checkbox" checked={families.includes(k)}
                  onChange={(e) => setFamilies((f) => (e.target.checked ? [...f, k] : f.filter((x) => x !== k)))} />
                <span>{help} <span className="small muted">({n.toLocaleString()} order{n === 1 ? "" : "s"})</span></span>
              </label>
            );
          })}
        </div>
        <div className="help">Every extra order makes the test slower and stricter: the bot pays for each one in its statistics.</div>
      </div>

      <details className="field">
        <summary>Ignore symbols, or fix symbols to letters (advanced)</summary>
        <div style={{ marginTop: 10 }}>
          <label>Ignore these symbols (treat as fillers)</label>
          <div className="symbols">
            {symbols.map((s) => (
              <button type="button" key={s} className={`sym ${drops.includes(s) ? "on" : ""}`} aria-pressed={drops.includes(s)}
                onClick={() => setDrops((d) => (d.includes(s) ? d.filter((x) => x !== s) : d.length < 3 ? [...d, s] : d))}>
                <Glyph code={s} size={18} /><span className="code">{s}</span>
              </button>
            ))}
          </div>
          <div className="help">Up to 3. Example: Zodiac&apos;s crosshair may be a signature rather than a letter.</div>
          <label style={{ marginTop: 12 }}>Fix symbols to letters</label>
          <div className="symbols">
            {symbols.filter((s) => !drops.includes(s)).map((s) => (
              <span key={s} className="row" style={{ gap: 2 }}>
                <Glyph code={s} size={18} /><span className="mono small">=</span>
                <select aria-label={`Letter for ${s}`} value={pins[s] ?? ""} style={{ width: 56, padding: "2px 4px" }}
                  onChange={(e) => setPins((p) => ({ ...p, [s]: e.target.value }))}>
                  <option value="">?</option>
                  {"ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").map((l) => <option key={l} value={l}>{l}</option>)}
                </select>
              </span>
            ))}
          </div>
          <div className="help">Example: test whether Z13&apos;s A, E, N, M stand for themselves.</div>
        </div>
      </details>

      <details className="field">
        <summary>Statistics settings (advanced)</summary>
        <div className="grid tiles" style={{ marginTop: 10 }}>
          <Num label="Shuffled copies (nulls)" v={nulls} set={setNulls} lo={9} hi={199} help="More = finer p-values, slower" />
          <Num label="Real-text tests (controls)" v={controls} set={setControls} lo={0} hi={20} help="Measure power" />
          <Num label="Restarts per search" v={restarts} set={setRestarts} lo={1} hi={8} help="More = more thorough" />
        </div>
      </details>

      <div className="grid two">
        <div className="field">
          <label htmlFor="f-title">Name</label>
          <input id="f-title" type="text" maxLength={120} placeholder={spec.title} value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="f-why">Why test this? (optional)</label>
          <input id="f-why" type="text" maxLength={1000} value={motivation} onChange={(e) => setMotivation(e.target.value)} />
        </div>
      </div>

      <div className="row">
        <button className="btn" disabled={!admin || !writable || busy || problems.length > 0}>Add to queue</button>
        <span className="small muted">Estimated run time ≈ {fmtDuration(est)}{est > 5 * 3600 ? " — longer than one run; it will be cut off" : ""}</span>
      </div>
      {problems.length > 0 && <div className="msg err small">{problems.join("; ")}</div>}
      {!admin && <p className="small muted">Unlock at the top of this page to add work.</p>}
      {result && <div className={`msg ${result.ok ? "ok" : "err"}`}>{result.text}</div>}
    </form>
  );
}

function label(name: string): string {
  const [b, v] = name.split(".");
  return v ? `${b.toUpperCase()} — ${v.replaceAll("_", " ")}` : `${b.toUpperCase()} — standard reading`;
}

function Num({ label, v, set, lo, hi, help }: { label: string; v: number; set: (n: number) => void; lo: number; hi: number; help: string }) {
  return (
    <div>
      <label className="small">{label}</label>
      <input type="number" min={lo} max={hi} value={v} onChange={(e) => set(Math.max(lo, Math.min(hi, Number(e.target.value) || lo)))} />
      <div className="help">{help}</div>
    </div>
  );
}

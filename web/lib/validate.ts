// Checks a hypothesis before it is committed to hypotheses/queue/.
// Mirrors zbot/schema.py; the bot re-checks everything, so this is the first line,
// not the only one. Tested in validate.test.ts.

import type { Options, Spec } from "./types.ts";

const ALLOWED = new Set([
  "id", "title", "motivation", "cipher", "model", "lang", "families", "drop_symbols",
  "pins", "pin_family", "restarts", "iters", "nulls", "controls", "extend_nulls",
  "explore_columnar", "klw", "suggested_by", "scorer", "control_text", "key_budget_weight",
]);
const ID_RE = /^user\.[a-z0-9][a-z0-9._-]{2,80}$/;
const NUMERIC: Record<string, [number, number]> = {
  restarts: [1, 8], nulls: [9, 199], controls: [0, 20], extend_nulls: [0, 499], iters: [10_000, 3_000_000],
};

export function slugify(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "hypothesis";
}

export function checkSpec(spec: Spec, opts: Options): string[] {
  const errs: string[] = [];
  const extra = Object.keys(spec).filter((k) => !ALLOWED.has(k));
  if (extra.length) errs.push(`unknown fields: ${extra.join(", ")}`);
  if (!ID_RE.test(spec.id ?? "")) errs.push("id must look like user.something");
  if (!spec.title || typeof spec.title !== "string" || spec.title.length > 120) errs.push("a title of up to 120 characters is required");
  if (spec.motivation !== undefined && (typeof spec.motivation !== "string" || spec.motivation.length > 1000))
    errs.push("motivation must be up to 1000 characters");

  const names = Array.isArray(spec.cipher) ? spec.cipher : [spec.cipher];
  const ciphers = names.map((n) => opts.ciphers.find((c) => c.name === n));
  if (names.length < 1 || names.length > 2 || ciphers.some((c) => !c)) {
    errs.push("pick one cipher (or two for a shared-key test)");
    return errs;
  }
  const text = ciphers.map((c) => c!.text).join("");
  const model = spec.model ?? "homophonic";
  if (!(model in opts.models)) errs.push("unknown key model");
  if (!((spec.lang ?? "en") in opts.languages)) errs.push("unknown language");

  const fams = spec.families ?? ["identity"];
  if (!Array.isArray(fams) || fams.some((f) => !(f in opts.families))) errs.push("unknown read-order family");
  else if (names.length > 1 && !(fams.length === 1 && fams[0] === "identity"))
    errs.push("a shared-key test can only read the ciphers as written");
  else {
    const orders = fams.reduce((a, f) => a + (ciphers[0]!.family_sizes[f] ?? 0), 0);
    if (orders > 2000) errs.push(`those read orders add up to ${orders}; the limit is 2000`);
  }

  for (const [k, [lo, hi]] of Object.entries(NUMERIC)) {
    const v = spec[k];
    if (v !== undefined && (!Number.isInteger(v) || (v as number) < lo || (v as number) > hi))
      errs.push(`${k} must be a whole number from ${lo} to ${hi}`);
  }
  const drops = spec.drop_symbols ?? [];
  if (!Array.isArray(drops) || drops.length > 3 || drops.some((d) => typeof d !== "string" || !text.includes(d)))
    errs.push("up to 3 dropped symbols, each from the cipher");

  const pinSets = spec.pin_family ?? [spec.pins ?? {}];
  if (!Array.isArray(pinSets) || pinSets.length > 64) errs.push("at most 64 pin sets");
  else
    for (const ps of pinSets) {
      const entries = Object.entries(ps ?? {});
      if (entries.length > 10 || entries.some(([s, l]) => !text.includes(s) || !/^[A-Z]$/.test(String(l)))) {
        errs.push("pins map up to 10 cipher symbols to single letters A-Z");
        break;
      }
    }
  if (spec.scorer) {
    const offered = Object.values(opts.scorers ?? {}).map((x) => JSON.stringify(x.config));
    if (!offered.includes(JSON.stringify(spec.scorer))) errs.push("unknown scoring method");
    else if ((spec.lang ?? "en") !== "en") errs.push("word scoring is only available for English");
  }
  const distinct = new Set(text).size - new Set(drops).size;
  if (model === "simple" && distinct > 26) errs.push(`simple substitution is impossible: ${distinct} distinct symbols > 26 letters`);
  return errs;
}

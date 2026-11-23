// Pure helpers, shared by server and client, with no I/O. Tested in stats.test.ts.

import type { LedgerRow, Row, VerdictKind, Spec, CipherOption } from "./types.ts";

export function verdictKind(v: string | undefined): VerdictKind {
  const s = v ?? "";
  if (s.startsWith("CALIBRATION PASS")) return "pass";
  if (s.startsWith("CALIBRATION FAIL")) return "fail";
  if (s.startsWith("UNTESTABLE")) return "untestable";
  if (s.startsWith("NO SIGNAL")) return "nosignal";
  if (s.startsWith("CANDIDATE")) return "candidate";
  if (s.startsWith("SKIPPED")) return "skipped";
  return "error";
}

export const MIN_POWER = 0.2;

/** Holm-Bonferroni adjusted p-values, same as zbot/report.py. */
export function holm(ps: number[]): number[] {
  const m = ps.length;
  const order = ps.map((p, i) => [p, i] as const).sort((a, b) => a[0] - b[0]);
  const adj = new Array<number>(m).fill(1);
  let running = 0;
  order.forEach(([p, i], rank) => {
    running = Math.max(running, Math.min(1, (m - rank) * p));
    adj[i] = running;
  });
  return adj;
}

export type Tier = "calibration" | "exploratory" | "confirmatory";

export function tier(id: string): Tier {
  if (id.startsWith("calib.")) return "calibration";
  if (id.startsWith("explore.")) return "exploratory";
  return "confirmatory";
}

/** numpy.quantile default (linear interpolation). */
export function quantile(xs: number[], q: number): number {
  const s = [...xs].sort((a, b) => a - b);
  const pos = (s.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.min(lo + 1, s.length - 1);
  return s[lo] + (s[hi] - s[lo]) * (pos - lo);
}

/** Share of controls above the 95th percentile of {real} + nulls; same as zbot/evaluate.py. */
export function powerPooled(real: number, nulls: number[], controls: number[]): number | null {
  if (!controls.length || !nulls.length) return null;
  const q = quantile([...nulls, real], 0.95);
  return controls.filter((c) => c > q).length / controls.length;
}

function effectivePower(r: LedgerRow): number | null {
  if (r.real_score !== undefined && r.null_scores?.length && r.control_scores?.length) {
    return powerPooled(r.real_score, r.null_scores, r.control_scores);
  }
  return r.power ?? null;
}

/** Latest row per id; Holm runs separately within each non-calibration tier, on pooled power. */
export function prepare(rows: LedgerRow[]): Row[] {
  const latest = new Map<string, LedgerRow>();
  for (const r of rows) latest.set(r.id, r);
  const all = [...latest.values()].map((r) => ({ ...r, power: effectivePower(r) }));
  const holmById = new Map<string, number>();
  for (const t of ["exploratory", "confirmatory"] as Tier[]) {
    // Same family as zbot/report.py: tests of this tier that could see something (power >= 0.2).
    const family = all.filter(
      (r) => r.p !== null && r.p !== undefined && tier(r.id) === t && (r.power === null || r.power >= MIN_POWER),
    );
    const adj = holm(family.map((r) => r.p as number));
    family.forEach((r, i) => holmById.set(r.id, adj[i]));
  }
  return all.map((r) => ({
    ...r,
    p_holm: holmById.get(r.id) ?? null,
    verdictKind: verdictKind(r.verdict),
  }));
}

/** An alert: confirmatory, survives correction within its tier, AND the test had power to see it. */
export function isAlert(r: Row): boolean {
  return tier(r.id) === "confirmatory" && r.p_holm !== null && r.p_holm < 0.05 && (r.power ?? 0) >= 0.5;
}

export function cipherLabel(c: Spec["cipher"]): string {
  if (Array.isArray(c)) return c.map(cipherLabel).join(" + ");
  if (!c) return "synthetic";
  const [base, variant] = c.split(".");
  const b = base.toUpperCase();
  return variant ? `${b} (${variant.replaceAll("_", " ")})` : b;
}

export function cipherBase(c: Spec["cipher"]): string {
  if (Array.isArray(c)) return "joint";
  if (!c) return "calibration";
  return c.split(".")[0];
}

export function fmtDuration(seconds: number): string {
  if (!isFinite(seconds)) return "unknown";
  if (seconds < 60) return `${Math.max(1, Math.round(seconds))} s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  const h = seconds / 3600;
  return h < 10 ? `${h.toFixed(1)} h` : `${Math.round(h)} h`;
}

export function fmtP(p: number | null | undefined): string {
  if (p === null || p === undefined) return "–";
  if (p < 0.001) return "<0.001";
  return p.toFixed(p < 0.1 ? 3 : 2);
}

/** Same formula as zbot/status.py estimate_seconds (upper bound: family sizes are summed). */
export function estimateSeconds(spec: Spec, cipher: CipherOption | undefined): number {
  if (!cipher) return NaN;
  const drops = spec.drop_symbols ?? [];
  const n = cipher.length - drops.reduce((a, d) => a + cipher.text.split(d).length - 1, 0);
  const nsym = cipher.distinct - drops.length;
  const iters = spec.iters ?? Math.max(50_000, 10_000 * nsym);
  const perIter = (0.8e-6 + 0.2e-6 * (n / nsym)) * (spec.scorer?.words ? 2 : 1);
  const fams = spec.families?.length ? spec.families : ["identity"];
  const orders = fams.reduce((a, f) => a + (cipher.family_sizes[f] ?? 0), 0) || 1;
  const pinSets = spec.pin_family?.length ?? 1;
  const instances = 1 + (spec.nulls ?? 19) + (spec.controls ?? 10);
  return 2 + (instances * orders * pinSets * (spec.restarts ?? 4) * iters * perIter) / 4;
}

// Daily backup start: the workflow cron is 03:17 UTC. Normally each run starts the next
// one as it finishes, so this only matters if that chain has stopped.
export function nextScheduled(now: Date): Date {
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 3, 17));
  if (d <= now) d.setUTCDate(d.getUTCDate() + 1);
  return d;
}

export function relTime(iso: string | undefined, now = new Date()): string {
  if (!iso) return "";
  const t = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  const s = (now.getTime() - t.getTime()) / 1000;
  const a = Math.abs(s);
  const unit = a < 3600 ? [Math.round(a / 60), "min"] : a < 86400 ? [Math.round(a / 3600), "h"] : [Math.round(a / 86400), "d"];
  return s >= 0 ? `${unit[0]} ${unit[1]} ago` : `in ${unit[0]} ${unit[1]}`;
}

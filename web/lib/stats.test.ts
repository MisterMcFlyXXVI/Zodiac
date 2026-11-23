import { test } from "node:test";
import assert from "node:assert/strict";
import { holm, prepare, isAlert, powerPooled, nextScheduled, verdictKind, estimateSeconds } from "./stats.ts";
import { checkSpec, slugify } from "./validate.ts";
import { readFileSync } from "node:fs";
import type { Status } from "./types.ts";

test("holm matches the Python implementation", () => {
  assert.deepEqual(holm([0.01, 0.04, 0.03]).map((x) => +x.toFixed(6)), [0.03, 0.06, 0.06]);
});

test("prepare keeps the latest row per id and excludes calibrations from correction", () => {
  const base = { spec_hash: "x", spec: { id: "a" }, power: 0.9, verdict: "CANDIDATE SIGNAL: x" };
  const rows = prepare([
    { ...base, id: "a", p: 0.5 },
    { ...base, id: "a", p: 0.001 },
    { ...base, id: "calib.z408.homophonic", p: 0.05, verdict: "CALIBRATION PASS" },
  ]);
  assert.equal(rows.length, 2);
  const a = rows.find((r) => r.id === "a")!;
  assert.equal(a.p, 0.001);
  assert.equal(a.p_holm, 0.001);
  assert.ok(isAlert(a));
  assert.equal(rows.find((r) => r.id.startsWith("calib"))!.p_holm, null);
});

test("untestable tests are left out of the correction", () => {
  const base = { spec_hash: "x", spec: { id: "a" }, verdict: "NO SIGNAL: x" };
  const rows = prepare([
    { ...base, id: "good", p: 0.01, power: 0.6 },
    { ...base, id: "blind", p: 0.02, power: 0.05, verdict: "UNTESTABLE: x" },
  ]);
  assert.equal(rows.find((r) => r.id === "good")!.p_holm, 0.01);   // family of one
  assert.equal(rows.find((r) => r.id === "blind")!.p_holm, null);
});

test("verdict kinds", () => {
  assert.equal(verdictKind("UNTESTABLE: x"), "untestable");
  assert.equal(verdictKind("CALIBRATION PASS"), "pass");
  assert.equal(verdictKind("SKIPPED: invalid spec"), "skipped");
});

test("daily backup start is the next 03:17 UTC", () => {
  assert.equal(nextScheduled(new Date("2026-11-19T23:00:00Z")).toISOString(), "2026-11-20T03:17:00.000Z");
  assert.equal(nextScheduled(new Date("2026-11-20T03:17:00Z")).toISOString(), "2026-11-21T03:17:00.000Z");
});

const status = JSON.parse(readFileSync(new URL("../../live-results/STATUS.json", import.meta.url), "utf8")) as Status;
const opts = status.options;

test("valid form spec passes; estimate is close to the bot's", () => {
  const spec = { id: "user.z13-fr-1", title: "Z13 French", cipher: "z13", model: "simple" as const, lang: "fr" };
  assert.deepEqual(checkSpec(spec, opts), []);
  const z13 = opts.ciphers.find((c) => c.name === "z13")!;
  const est = estimateSeconds(spec, z13);
  assert.ok(est > 1 && est < 30, String(est));
});

test("bad specs are rejected, each for its own reason", () => {
  const ok = { id: "user.abc", title: "t", cipher: "z13" };
  const cases: [Record<string, unknown>, string][] = [
    [{ id: "calib.evil" }, "id must"],
    [{ cipher: "z99" }, "pick one cipher"],
    [{ cipher: "z32", model: "simple" }, "impossible"],
    [{ nulls: 5000 }, "nulls must"],
    [{ pins: { Q: "A" } }, "pins map"],
    [{ extra: 1 }, "unknown fields"],
    [{ cipher: "z408", families: ["columnar2to6", "columnar7to8_sampled", "griddec", "routes"] }, "limit is 2000"],
    [{ title: "" }, "title"],
  ];
  for (const [patch, why] of cases) {
    const problems = checkSpec({ ...ok, ...patch } as never, opts);
    assert.equal(problems.length, 1, JSON.stringify([patch, problems]));
    assert.ok(problems[0].includes(why), JSON.stringify([patch, problems]));
  }
});

test("every bot suggestion passes the web checks", () => {
  for (const s of status.suggestions) assert.deepEqual(checkSpec({ ...s.spec }, opts), [], s.spec.id);
});

test("slugify", () => {
  assert.equal(slugify("Z13 as Vietnamese — circles!"), "z13-as-vietnamese-circles");
});

test("exploratory rows never enter the confirmatory family and never alert", () => {
  const base = { spec_hash: "x", spec: { id: "a" }, power: 0.9, verdict: "CANDIDATE SIGNAL: x" };
  const rows = prepare([
    ...[0, 1, 2, 3, 4].map((i) => ({ ...base, id: `explore.${i}`, p: 0.0001 })),
    { ...base, id: "c1", p: 0.5 },
  ]);
  assert.equal(rows.find((r) => r.id === "c1")!.p_holm, 0.5);
  assert.ok(rows.filter((r) => r.id.startsWith("explore.")).every((r) => !isAlert(r)));
});

test("confirmatory alert fires at p=1/1000 with 12 tests", () => {
  const base = { spec_hash: "x", spec: { id: "a" }, power: 0.9, verdict: "CANDIDATE SIGNAL: x" };
  const rows = prepare([
    ...Array.from({ length: 11 }, (_, i) => ({ ...base, id: `c${i}`, p: 0.5 })),
    { ...base, id: "hit", p: 0.001, power: 0.6 },
  ]);
  assert.deepEqual(rows.filter(isAlert).map((r) => r.id), ["hit"]);
});

test("powerPooled matches the hand value from the Python test", () => {
  const nulls = [0, 1, 2, 3];
  const controls = [2.5, 3.5, 4.5, 5.5];
  assert.equal(powerPooled(10, nulls, controls), 0);
  assert.equal(powerPooled(1.5, nulls, controls), 0.75);
  assert.equal(powerPooled(1.5, nulls, []), null);
  // nulls-only threshold would give 0.75 where real is the maximum
  const r = prepare([{ id: "c", p: 0.01, power: 0.9, spec_hash: "x", spec: { id: "c" }, verdict: "NO SIGNAL: x",
    real_score: 10, null_scores: nulls, control_scores: controls }]);
  assert.equal(r[0].power, 0);
});

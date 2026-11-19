import "server-only";
import { getLedger, getRuns, getStatus } from "./github";
import { prepare } from "./stats";
import type { Row, Status, WorkflowRun } from "./types";

export type Loaded = { rows: Row[]; status: Status | null; runs: WorkflowRun[]; problems: string[] };

export async function loadAll(): Promise<Loaded> {
  const problems: string[] = [];
  const [ledger, status, runs] = await Promise.all([
    getLedger().catch((e) => (problems.push(`results: ${e.message}`), [])),
    getStatus().catch((e) => (problems.push(`status: ${e.message}`), null)),
    getRuns().catch((e) => (problems.push(`GitHub Actions: ${e.message}`), [])),
  ]);
  return { rows: prepare(ledger), status, runs, problems };
}

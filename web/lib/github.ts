// All GitHub access lives here (server only).
// Reads use the public raw/contents endpoints and work without a token.
// Writes (queue a hypothesis, start a run) need GITHUB_TOKEN.

import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import type { LedgerRow, QueueFile, Spec, Status, WorkflowRun } from "./types";

export const REPO = process.env.GITHUB_REPO || "MisterMcFlyXXVI/Zodiac";
const RESULTS_BRANCH = "zbot-results";
const WORKFLOW = "zbot.yml";
const REVALIDATE = 120; // seconds: how stale the dashboard may be
const API = process.env.GITHUB_API_URL || "https://api.github.com"; // overridable for tests

function headers(write = false): HeadersInit {
  const h: Record<string, string> = {
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "zbot-web",
  };
  if (process.env.GITHUB_TOKEN) h.Authorization = `Bearer ${process.env.GITHUB_TOKEN}`;
  else if (write) throw new Error("GITHUB_TOKEN is not set on the server");
  return h;
}

export const canWrite = () => Boolean(process.env.GITHUB_TOKEN && process.env.ADMIN_PASSWORD);

async function api<T>(url: string, init?: RequestInit & { revalidate?: number }): Promise<T | null> {
  const res = await fetch(`${API}${url}`, {
    ...init,
    headers: { ...headers(), ...(init?.headers ?? {}) },
    next: init?.method && init.method !== "GET" ? undefined : { revalidate: init?.revalidate ?? REVALIDATE },
    cache: init?.method && init.method !== "GET" ? "no-store" : undefined,
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GitHub ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.status === 204 ? ({} as T) : ((await res.json()) as T);
}

export async function defaultBranch(): Promise<string> {
  // A failed lookup (rate limit, bad token) must not take the results down with it.
  try {
    const r = await api<{ default_branch: string }>(`/repos/${REPO}`, { revalidate: 3600 });
    if (r?.default_branch) return r.default_branch;
  } catch {
    /* fall through */
  }
  return process.env.GITHUB_DEFAULT_BRANCH || "main";
}

// Results files are fetched WITHOUT Next's data cache: it refuses entries over 2 MB, and when a
// refresh can't be stored the site keeps serving the last copy that fit, so results looked frozen
// once the ledger outgrew 2 MB. Instead each server instance keeps its own copy for REVALIDATE s.
const memo = new Map<string, { at: number; text: string | null }>();

async function raw(branch: string, file: string): Promise<string | null> {
  const local = process.env.LOCAL_RESULTS_DIR;
  if (local) {
    try {
      // Keep sub-folders (rows/<id>.json) under the local results folder.
      return await fs.readFile(path.join(local, file.replace(/^results\//, "")), "utf8");
    } catch {
      return null;
    }
  }
  const url = `https://raw.githubusercontent.com/${REPO}/${encodeURIComponent(branch).replaceAll("%2F", "/")}/${file}`;
  const hit = memo.get(url);
  if (hit && Date.now() - hit.at < REVALIDATE * 1000) return hit.text;
  const res = await fetch(url, { cache: "no-store" });
  const text = res.ok ? await res.text() : null;
  if (res.ok || res.status === 404) memo.set(url, { at: Date.now(), text });
  return text;
}

/** Results branch first (written by the workflow), default branch as fallback. */
async function resultsFile(file: string): Promise<{ text: string | null; branch: string }> {
  const fromResults = await raw(RESULTS_BRANCH, `results/${file}`);
  if (fromResults !== null) return { text: fromResults, branch: RESULTS_BRANCH };
  const def = await defaultBranch();
  return { text: await raw(def, `results/${file}`), branch: def };
}

/** Compact rows for the list pages (no per-test score arrays); full ledger if the bot hasn't
 *  published the compact file yet. */
export async function getLedger(): Promise<LedgerRow[]> {
  let { text } = await resultsFile("ledger_slim.jsonl");
  if (!text) text = (await resultsFile("ledger.jsonl")).text;
  if (!text) return [];
  return text
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l) as LedgerRow);
}

/** One test's full row (score arrays included), for its detail page. Mirrors report.row_file. */
export async function getRow(id: string): Promise<LedgerRow | null> {
  const name = id.replace(/[^A-Za-z0-9._-]/g, "_") + ".json";
  const { text } = await resultsFile(`rows/${name}`);
  if (text) return JSON.parse(text) as LedgerRow;
  const full = (await resultsFile("ledger.jsonl")).text; // before the bot publishes rows/
  if (!full) return null;
  let found: LedgerRow | null = null;
  for (const l of full.split("\n")) if (l.includes(`"id": "${id}"`)) found = JSON.parse(l) as LedgerRow;
  return found;
}

export async function getStatus(): Promise<Status | null> {
  const { text } = await resultsFile("STATUS.json");
  // Older runs wrote no STATUS.json; fall back to the default branch's copy.
  if (text) return JSON.parse(text) as Status;
  const def = await defaultBranch();
  const t = await raw(def, "results/STATUS.json");
  return t ? (JSON.parse(t) as Status) : null;
}

/** Files in hypotheses/queue/ on the default branch, read live (not cached) so new ones show at once. */
export async function getQueue(fresh = false): Promise<QueueFile[]> {
  const def = await defaultBranch();
  const list = await api<{ name: string; sha: string; download_url: string; type: string }[]>(
    `/repos/${REPO}/contents/hypotheses/queue?ref=${encodeURIComponent(def)}`,
    { revalidate: fresh ? 0 : 30 },
  );
  if (!list) return [];
  const files = list.filter((f) => f.type === "file" && f.name.endsWith(".json"));
  return Promise.all(
    files.map(async (f) => {
      let spec: Spec | null = null;
      try {
        const res = await fetch(f.download_url, { cache: "no-store" });
        spec = (await res.json()) as Spec;
      } catch {
        spec = null;
      }
      return { name: f.name, sha: f.sha, id: spec?.id ?? f.name.replace(/\.json$/, ""), spec };
    }),
  );
}

export async function getRuns(): Promise<WorkflowRun[]> {
  const r = await api<{ workflow_runs: WorkflowRun[] }>(
    `/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?per_page=5`,
    { revalidate: 60 },
  );
  return r?.workflow_runs ?? [];
}

// ---- writes ---------------------------------------------------------------

export async function addToQueue(spec: Spec): Promise<string> {
  const def = await defaultBranch();
  const file = `hypotheses/queue/${spec.id.replace(/^user\./, "")}.json`;
  const body = {
    message: `Queue ${spec.id} (via zbot web)`,
    content: Buffer.from(JSON.stringify(spec, null, 2) + "\n").toString("base64"),
    branch: def,
  };
  const res = await fetch(`${API}/repos/${REPO}/contents/${file}`, {
    method: "PUT",
    headers: headers(true),
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (res.status === 422) throw new Error("a queue file with that name already exists");
  if (!res.ok) throw new Error(`GitHub ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return file;
}

export async function removeFromQueue(name: string, sha: string): Promise<void> {
  if (!/^[a-z0-9][a-z0-9._-]*\.json$/.test(name)) throw new Error("bad file name");
  const def = await defaultBranch();
  const res = await fetch(`${API}/repos/${REPO}/contents/hypotheses/queue/${name}`, {
    method: "DELETE",
    headers: headers(true),
    body: JSON.stringify({ message: `Unqueue ${name} (via zbot web)`, sha, branch: def }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`GitHub ${res.status}: ${(await res.text()).slice(0, 200)}`);
}

export async function startRun(hours: number): Promise<void> {
  const def = await defaultBranch();
  const res = await fetch(`${API}/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    headers: headers(true),
    body: JSON.stringify({ ref: def, inputs: { hours: String(hours) } }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`GitHub ${res.status}: ${(await res.text()).slice(0, 200)}`);
}

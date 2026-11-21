// Shapes of the files the bot publishes (results/ledger.jsonl and results/STATUS.json).

export type Spec = {
  id: string;
  title?: string;
  motivation?: string;
  cipher?: string | string[];
  model?: "homophonic" | "simple" | "zodiac";
  lang?: string;
  families?: string[];
  drop_symbols?: string[];
  pins?: Record<string, string>;
  pin_family?: Record<string, string>[];
  restarts?: number;
  iters?: number;
  scorer?: { ngram?: number; words?: number; unk?: number; wpen?: number; zodiac_boost?: number; zodiac_fold?: string } | null;
  nulls?: number;
  controls?: number;
  extend_nulls?: number;
  synthetic?: { length: number; key_size: number; seed: number };
  source?: string;
  suggested_by?: string;
  [k: string]: unknown;
};

export type Decode = { score: number; order: string; plaintext: string };

export type LedgerRow = {
  id: string;
  spec_hash: string;
  spec: Spec;
  lang?: string;
  lm?: string;
  finished?: string;
  seconds?: number;
  family_size?: number;
  length?: number;
  real_score?: number;
  real_per_letter?: number;
  top?: Decode[];
  null_scores?: number[];
  null_q95?: number;
  control_scores?: number[];
  control_recovery?: number | null;
  p: number | null;
  z?: number | null;
  power: number | null;
  verdict: string;
  calib_accuracy?: number;
  dominance?: number | null;
  null_dominance?: number[];
  control_dominance?: number[];
  p_dominance?: number | null;
  power_dominance?: number | null;
  error?: string;
};

export type Row = LedgerRow & { p_holm: number | null; verdictKind: VerdictKind };

export type VerdictKind =
  | "pass"
  | "fail"
  | "untestable"
  | "nosignal"
  | "candidate"
  | "error"
  | "skipped";

export type PendingItem = {
  id: string;
  title: string;
  lang: string;
  source: "queue" | "built-in";
  suggested_by?: string | null;
  est_seconds: number;
  problems?: string[];
  verdict?: string;
};

export type Suggestion = {
  kind: "follow-up" | "robustness" | "coverage" | "idea";
  why: string;
  spec: Spec;
  est_seconds: number;
};

export type CipherOption = {
  name: string;
  text: string;
  length: number;
  distinct: number;
  solved: boolean;
  family_sizes: Record<string, number>;
};

export type Options = {
  ciphers: CipherOption[];
  models: Record<string, string>;
  languages: Record<string, string>;
  families: Record<string, string>;
  limits: Record<string, number | [number, number]>;
  scorers?: Record<string, { label: string; help: string; config: Spec["scorer"] }>;
};

export type Status = {
  generated: string;
  run: { github_run_id: string | null; github_run_url: string | null };
  current?: { id: string; title: string; lang: string; started: string; est_seconds: number } | null;
  models: Record<string, string>;
  counts: Record<string, number>;
  pending: PendingItem[];
  done: PendingItem[];
  explore_next: string | null;
  suggestions: Suggestion[];
  options: Options;
};

export type QueueFile = { name: string; id: string; sha: string; spec: Spec | null };

export type WorkflowRun = {
  id: number;
  status: string; // queued | in_progress | completed
  conclusion: string | null;
  event: string;
  created_at: string;
  run_started_at?: string;
  updated_at: string;
  html_url: string;
};

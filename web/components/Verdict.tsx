import type { VerdictKind } from "@/lib/types";

const LABEL: Record<VerdictKind, string> = {
  pass: "Calibration passed",
  fail: "Calibration failed",
  untestable: "Untestable",
  nosignal: "No signal",
  candidate: "Candidate signal",
  error: "Error",
  skipped: "Skipped",
};
const ICON: Record<VerdictKind, string> = {
  pass: "✓", fail: "✕", untestable: "∅", nosignal: "–", candidate: "!", error: "✕", skipped: "↷",
};

export default function Verdict({ kind, title }: { kind: VerdictKind; title?: string }) {
  return (
    <span className={`badge ${kind}`} title={title}>
      <span aria-hidden="true">{ICON[kind]}</span>
      {LABEL[kind]}
    </span>
  );
}

export const VERDICT_HELP: Record<VerdictKind, string> = {
  pass: "The bot solved a known cipher in this language, so its results in this language can be trusted.",
  fail: "The bot could not solve a known cipher in this language; its results in this language are not reported.",
  untestable: "Even genuine text enciphered the same way would not have stood out. The test cannot tell anything at this length.",
  nosignal: "The test could have detected real text, and the real cipher looked no different from scrambled copies of itself.",
  candidate: "The real cipher scored better than scrambled copies. Check the Holm-corrected p and power before getting excited.",
  error: "The run failed; see the error message.",
  skipped: "Not run (for example, its language failed calibration or the request was invalid).",
};

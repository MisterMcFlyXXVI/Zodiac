import { loadAll } from "@/lib/data";
import ResultsTable, { type SlimRow } from "@/components/ResultsTable";
import { cipherBase, cipherLabel, isAlert } from "@/lib/stats";

export const dynamic = "force-dynamic"; // fresh relative times; GitHub data itself is cached 2 min

export default async function Results({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const sp = await searchParams;
  const { rows, problems } = await loadAll();
  const slim: SlimRow[] = rows.map((r) => ({
    id: r.id,
    title: r.spec.title ?? r.id,
    cipher: cipherLabel(r.spec.cipher),
    base: cipherBase(r.spec.cipher),
    lang: r.lang ?? "en",
    model: r.spec.model ?? "homophonic",
    kind: r.verdictKind,
    p: r.p,
    p_holm: r.p_holm,
    power: r.power,
    z: r.z ?? null,
    family: r.family_size ?? 1,
    best: r.top?.[0]?.plaintext ?? "",
    finished: r.finished ?? "",
    alert: isAlert(r),
    calib: r.id.startsWith("calib."),
    queued: Boolean(r.spec.source),
  }));
  return (
    <>
      <h1>Results</h1>
      <p className="lede">
        Every hypothesis the bot has tested. Click one for the full picture: what was tested, the score chart and the best decodes.
      </p>
      {problems.length > 0 && <div className="msg err">{problems.join("; ")}</div>}
      <ResultsTable rows={slim} initial={{ verdict: sp.verdict ?? "", view: sp.view ?? "", q: sp.q ?? "", cipher: sp.cipher ?? "", lang: sp.lang ?? "" }} />
    </>
  );
}

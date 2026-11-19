import { NextResponse } from "next/server";
import { revalidatePath } from "next/cache";
import { isAdmin } from "@/lib/auth";
import { addToQueue, getLedger, getQueue, getStatus, removeFromQueue } from "@/lib/github";
import { checkSpec } from "@/lib/validate";
import type { Spec } from "@/lib/types";

async function guard() {
  if (!(await isAdmin())) return NextResponse.json({ error: "Log in first" }, { status: 401 });
  if (!process.env.GITHUB_TOKEN) return NextResponse.json({ error: "GITHUB_TOKEN is not set on the server" }, { status: 503 });
  return null;
}

/** Add a hypothesis: body = { spec } */
export async function POST(req: Request) {
  const denied = await guard();
  if (denied) return denied;
  const { spec } = (await req.json().catch(() => ({}))) as { spec?: Spec };
  if (!spec || typeof spec !== "object") return NextResponse.json({ error: "missing spec" }, { status: 400 });
  const status = await getStatus();
  if (!status) return NextResponse.json({ error: "the bot has not published STATUS.json yet" }, { status: 503 });
  const clean: Spec = { ...spec };
  delete clean.source;
  const problems = checkSpec(clean, status.options);
  const [queue, ledger] = await Promise.all([getQueue(true), getLedger()]);
  if (queue.some((q) => q.id === clean.id) || ledger.some((r) => r.id === clean.id) ||
      status.pending.some((p) => p.id === clean.id))
    problems.push(`${clean.id} already exists; pick another name`);
  if (problems.length) return NextResponse.json({ error: problems.join("; "), problems }, { status: 422 });
  try {
    const file = await addToQueue(clean);
    revalidatePath("/queue");
    return NextResponse.json({ ok: true, file });
  } catch (e) {
    return NextResponse.json({ error: String((e as Error).message) }, { status: 502 });
  }
}

/** Remove a queued hypothesis that has not run: body = { name, sha } */
export async function DELETE(req: Request) {
  const denied = await guard();
  if (denied) return denied;
  const { name, sha } = (await req.json().catch(() => ({}))) as { name?: string; sha?: string };
  if (!name || !sha) return NextResponse.json({ error: "missing name or sha" }, { status: 400 });
  try {
    await removeFromQueue(name, sha);
    revalidatePath("/queue");
    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json({ error: String((e as Error).message) }, { status: 502 });
  }
}

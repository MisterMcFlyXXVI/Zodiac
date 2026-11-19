import { NextResponse } from "next/server";
import { revalidatePath } from "next/cache";
import { isAdmin } from "@/lib/auth";
import { getRuns, startRun } from "@/lib/github";

/** Start a run now: body = { hours } (0.25 to 5.5). */
export async function POST(req: Request) {
  if (!(await isAdmin())) return NextResponse.json({ error: "Log in first" }, { status: 401 });
  if (!process.env.GITHUB_TOKEN) return NextResponse.json({ error: "GITHUB_TOKEN is not set on the server" }, { status: 503 });
  const { hours } = (await req.json().catch(() => ({}))) as { hours?: number };
  const h = Number(hours ?? 5.5);
  if (!(h >= 0.25 && h <= 5.5)) return NextResponse.json({ error: "hours must be between 0.25 and 5.5" }, { status: 400 });
  const runs = await getRuns().catch(() => []);
  const busy = runs.find((r) => r.status !== "completed");
  try {
    await startRun(h);
    revalidatePath("/");
    revalidatePath("/queue");
    return NextResponse.json({
      ok: true,
      note: busy ? "A run is already going; this one will start when it finishes." : "Run started; it takes a minute or two to appear.",
    });
  } catch (e) {
    return NextResponse.json({ error: String((e as Error).message) }, { status: 502 });
  }
}

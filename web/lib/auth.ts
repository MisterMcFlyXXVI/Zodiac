// One shared password (ADMIN_PASSWORD) unlocks the buttons that change things.
// The cookie holds an HMAC of a fixed label keyed by the password, so changing the
// password logs everyone out, and the password itself is never stored client-side.

import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

export const COOKIE = "zbot_session";
const LABEL = "zbot-session-v1";

function token(): string | null {
  const pw = process.env.ADMIN_PASSWORD;
  return pw ? createHmac("sha256", pw).update(LABEL).digest("hex") : null;
}

function same(a: string, b: string): boolean {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

export function passwordMatches(candidate: string): boolean {
  const pw = process.env.ADMIN_PASSWORD;
  if (!pw) return false;
  const h = (s: string) => createHmac("sha256", "cmp").update(s).digest("hex");
  return same(h(candidate), h(pw));
}

export function sessionToken(): string {
  const t = token();
  if (!t) throw new Error("ADMIN_PASSWORD is not set");
  return t;
}

export async function isAdmin(): Promise<boolean> {
  const t = token();
  if (!t) return false;
  const c = (await cookies()).get(COOKIE)?.value;
  return Boolean(c && same(c, t));
}

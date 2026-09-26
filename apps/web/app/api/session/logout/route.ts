import { NextResponse } from "next/server";
import { authenticatedFetch } from "../../../../lib/server-api";

export async function POST() {
  await authenticatedFetch("/auth/logout-all", { method: "POST" });
  const result = NextResponse.json({ success: true });
  result.cookies.set("pyro_access", "", { httpOnly: true, path: "/", maxAge: 0 });
  result.cookies.set("pyro_refresh", "", { httpOnly: true, path: "/", maxAge: 0 });
  return result;
}

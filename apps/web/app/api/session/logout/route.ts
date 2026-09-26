import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { API_INTERNAL_URL, authenticatedFetch } from "../../../../lib/server-api";
import { sameOriginOrThrow } from "../../../../lib/request-security";

export async function POST(request: NextRequest) {
  try { sameOriginOrThrow(request); }
  catch { return NextResponse.json({ detail: "Forbidden origin" }, { status: 403 }); }

  let result = await authenticatedFetch("/auth/logout-all", { method: "POST" });
  if (result.status === 401) {
    const refreshToken = (await cookies()).get("pyro_refresh")?.value;
    if (refreshToken) {
      const rotated = await fetch(`${API_INTERNAL_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
        cache: "no-store"
      });
      if (rotated.ok) {
        const credentials = await rotated.json();
        result = await fetch(`${API_INTERNAL_URL}/auth/logout-all`, {
          method: "POST",
          headers: { Authorization: `Bearer ${credentials.access_token}` },
          cache: "no-store"
        });
      }
    }
  }
  const response = NextResponse.json({ success: result.ok });
  response.cookies.set("pyro_access", "", { httpOnly: true, path: "/", maxAge: 0 });
  response.cookies.set("pyro_refresh", "", { httpOnly: true, path: "/", maxAge: 0 });
  return response;
}

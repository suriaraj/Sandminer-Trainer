import { NextRequest, NextResponse } from "next/server";
import { API_INTERNAL_URL } from "../../../../lib/server-api";
import { cookieSecurity, sameOriginOrThrow } from "../../../../lib/request-security";

export async function POST(request: NextRequest) {
  try { sameOriginOrThrow(request); }
  catch { return NextResponse.json({ detail: "Forbidden origin" }, { status: 403 }); }
  const payload = await request.json();
  const response = await fetch(`${API_INTERNAL_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Device-Label": request.headers.get("user-agent")?.slice(0, 180) ?? "Web"
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });

  const body = await response.json();
  if (!response.ok) {
    return NextResponse.json(body, { status: response.status });
  }

  const result = NextResponse.json({ success: true });
  result.cookies.set("pyro_access", body.access_token, {
    ...cookieSecurity(),
    maxAge: 15 * 60
  });
  result.cookies.set("pyro_refresh", body.refresh_token, {
    ...cookieSecurity(),
    maxAge: 14 * 24 * 60 * 60
  });
  return result;
}

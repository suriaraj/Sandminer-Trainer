import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { API_INTERNAL_URL } from "../../../../lib/server-api";
import { sameOriginOrThrow } from "../../../../lib/request-security";

type Context = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, context: Context, method: "GET" | "POST" | "PUT") {
  if (method !== "GET") {
    try { sameOriginOrThrow(request); }
    catch { return NextResponse.json({ detail: "Forbidden origin" }, { status: 403 }); }
  }
  const segments = (await context.params).path;
  const allowedRoots = new Set(["kyc", "operators", "operator", "vehicle-categories", "bookings", "admin", "support"]);
  if (!segments.length || !allowedRoots.has(segments[0]) ||
      segments.some((segment) => !/^[A-Za-z0-9_-]+$/.test(segment))) {
    return NextResponse.json({ detail: "Unknown route" }, { status: 404 });
  }
  const store = await cookies();
  const token = store.get("pyro_access")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  }
  const body = method === "GET" ? undefined : await request.text();
  if (body && body.length > 100000) {
    return NextResponse.json({ detail: "Request too large" }, { status: 413 });
  }
  const target = API_INTERNAL_URL + "/" + segments.join("/") + request.nextUrl.search;
  const upstream = await fetch(target, {
    method,
    headers: {
      "Authorization": "Bearer " + token,
      ...(body ? { "Content-Type": "application/json" } : {})
    },
    body,
    cache: "no-store"
  });
  return new NextResponse(upstream.status === 204 ? null : await upstream.text(), {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") || "application/json",
      "Cache-Control": "no-store"
    }
  });
}

export async function GET(r: NextRequest, c: Context) { return handle(r, c, "GET"); }
export async function POST(r: NextRequest, c: Context) { return handle(r, c, "POST"); }
export async function PUT(r: NextRequest, c: Context) { return handle(r, c, "PUT"); }

import { NextRequest } from "next/server";

export function sameOriginOrThrow(request: NextRequest): void {
  const origin = request.headers.get("origin");
  if (!origin || origin !== request.nextUrl.origin) {
    throw new Error("Cross-origin mutation denied");
  }
}

export function cookieSecurity() {
  return {
    httpOnly: true as const,
    sameSite: "lax" as const,
    secure: process.env.COOKIE_SECURE === "false"
      ? false
      : process.env.NODE_ENV === "production",
    path: "/"
  };
}

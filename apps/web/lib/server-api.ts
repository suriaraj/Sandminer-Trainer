import { cookies } from "next/headers";

const API_INTERNAL_URL =
  process.env.API_INTERNAL_URL ?? "http://api:8000/api/v1";

export async function authenticatedFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const store = await cookies();
  const access = store.get("pyro_access")?.value;
  if (!access) {
    return new Response(JSON.stringify({ detail: "Authentication required" }), {
      status: 401,
      headers: { "Content-Type": "application/json" }
    });
  }

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${access}`);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }

  return fetch(`${API_INTERNAL_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });
}

export { API_INTERNAL_URL };

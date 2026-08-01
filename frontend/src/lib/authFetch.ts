// Milestone 1 · Increment 4E — shared authenticated fetch primitive.
//
// The browser flow talks to the backend same-origin via the Vite proxy
// (see vite.config.ts). Session cookies drive authentication; the
// Django CsrfViewMiddleware + DRF SessionAuthentication enforce CSRF
// on every unsafe method issued by an authenticated caller. This
// helper meets that contract:
//
//   - `credentials: "same-origin"` so the browser sends the sessionid
//     cookie automatically.
//   - Reads the `csrftoken` cookie set by the /auth/me/ bootstrap call
//     and attaches it as `X-CSRFToken` on every unsafe method.
//   - Throws typed errors so callers preserve the 401 vs 403 vs 4xx/5xx
//     distinction that useAuth + RequireAuth route on.
//
// The helper is intentionally small; every operator page and hook
// funnels through it, so hidden magic here is a debugging tax.
// Public pages (`/`, `/assistant`, `/showroom`, `/embed/assistant`,
// public branding GET) MUST continue to use plain `fetch` so a
// broken session can never break a customer page.

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/dealer-ai";

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class UnauthenticatedError extends Error {
  constructor(message = "Not signed in.") {
    super(message);
    this.name = "UnauthenticatedError";
  }
}

export class ForbiddenError extends Error {
  constructor(message = "Not authorized.") {
    super(message);
    this.name = "ForbiddenError";
  }
}

export class ApiError extends Error {
  status: number;
  body: string;
  constructor(status: number, body: string, message?: string) {
    super(message ?? `API request failed (${status}): ${body}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

/**
 * Read a browser cookie by name. Returns "" when the cookie is
 * absent — Django's csrftoken cookie is set by @ensure_csrf_cookie
 * on the /auth/me/ boot call, so this is only empty when the
 * bootstrap has not yet run (e.g. very first render).
 */
export function readCookie(name: string): string {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=")[1] ?? "") : "";
}

interface AuthFetchInit extends RequestInit {
  /** Absolute URL; if omitted, `path` is joined with API_BASE. */
  url?: string;
  /** API path relative to `/api/dealer-ai`. Ignored if `url` is set. */
  path?: string;
}

/**
 * The shared operator fetch primitive. Sends credentials, attaches
 * CSRF on unsafe methods, throws typed errors on 401 / 403 / other
 * non-2xx so consumers can preserve the distinction.
 *
 * Do NOT use for public endpoints — plain fetch is correct there.
 */
export async function authFetch(init: AuthFetchInit): Promise<Response> {
  const { url, path, method = "GET", headers, ...rest } = init;
  const target = url ?? `${API_BASE}${path ?? ""}`;

  const finalHeaders = new Headers(headers);
  if (UNSAFE_METHODS.has(method.toUpperCase())) {
    const token = readCookie("csrftoken");
    if (token && !finalHeaders.has("X-CSRFToken")) {
      finalHeaders.set("X-CSRFToken", token);
    }
  }

  const res = await fetch(target, {
    ...rest,
    method,
    headers: finalHeaders,
    credentials: "same-origin",
  });

  if (res.status === 401) {
    throw new UnauthenticatedError();
  }
  if (res.status === 403) {
    throw new ForbiddenError();
  }
  return res;
}

/**
 * JSON GET convenience wrapper. Returns the parsed body on 2xx,
 * throws {@link ApiError} on any other non-401/403 status.
 * 401 and 403 propagate as {@link UnauthenticatedError} /
 * {@link ForbiddenError} via {@link authFetch}.
 */
export async function authGetJSON<T>(path: string): Promise<T> {
  const res = await authFetch({ path, method: "GET" });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  return res.json() as Promise<T>;
}

export async function authPostJSON<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const res = await authFetch({
    path,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  return res.json() as Promise<T>;
}

export async function authPutJSON<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const res = await authFetch({
    path,
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  return res.json() as Promise<T>;
}

export async function authPostForm<T>(
  path: string,
  body: FormData,
): Promise<T> {
  const res = await authFetch({
    path,
    method: "POST",
    body,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  return res.json() as Promise<T>;
}

// Milestone 3 · Increment 7 — PATCH and DELETE helpers for the
// M3.6 condition-report admin API. Same typed-error shape as the
// existing GET/POST/PUT helpers.

export async function authPatchJSON<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const res = await authFetch({
    path,
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  return res.json() as Promise<T>;
}

/**
 * DELETE convenience. Backend returns 204 with an empty body for
 * successful deletes, so this helper does not attempt to JSON-parse
 * the response — it just resolves on 2xx and throws on error.
 */
export async function authDelete(path: string): Promise<void> {
  const res = await authFetch({ path, method: "DELETE" });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
}

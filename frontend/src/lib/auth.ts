// Milestone 1 · Increment 4E — auth API + shared types.
//
// Wraps /auth/login, /auth/logout, /auth/me. The `me` bootstrap call
// double-purposes as a CSRF-cookie primer (backend view is decorated
// with @ensure_csrf_cookie), so calling `fetchMe()` at app boot is
// how the browser acquires the token it later attaches to unsafe
// requests via authFetch.

import {
  ApiError,
  UnauthenticatedError,
  authFetch,
  authPostJSON,
} from "@/lib/authFetch";

export interface AuthUser {
  id: number;
  username: string;
  display_name: string;
  /** Populated when the user has an attached Salesperson row (advisor
   *  workspace routing). null otherwise. */
  salesperson_slug: string | null;
}

export interface AuthDealership {
  id: number;
  slug: string;
  name: string;
}

/** Shape returned by /auth/me when a session exists. */
export interface AuthenticatedMe {
  authenticated: true;
  user: AuthUser;
  dealership: AuthDealership;
  /** Every role the user holds at `dealership`. Multi-role per
   *  dealership is intentional (see 4A design note). Sorted. */
  roles: string[];
}

export interface AnonymousMe {
  authenticated: false;
}

export type MeResponse = AuthenticatedMe | AnonymousMe;

/**
 * Fetch the current session state and prime the csrftoken cookie.
 * Never throws — returns `{authenticated: false}` for anonymous
 * sessions. The frontend calls this on every app boot AND on every
 * login/logout transition.
 */
export async function fetchMe(): Promise<MeResponse> {
  try {
    const res = await authFetch({ path: "/auth/me/", method: "GET" });
    if (!res.ok) {
      // The endpoint is AllowAny, so anything non-2xx is a real
      // outage (5xx / network). Fall back to anonymous — the UI
      // will render public content or redirect to /login.
      return { authenticated: false };
    }
    return (await res.json()) as MeResponse;
  } catch (err) {
    if (err instanceof UnauthenticatedError) return { authenticated: false };
    throw err;
  }
}

/** Authenticate; returns the fresh {@link AuthenticatedMe} shape
 *  or throws {@link InvalidCredentialsError} for wrong credentials. */
export async function loginRequest(
  username: string,
  password: string,
): Promise<AuthenticatedMe> {
  try {
    const res = await authPostJSON<AuthenticatedMe>("/auth/login/", {
      username,
      password,
    });
    return res;
  } catch (err) {
    if (err instanceof UnauthenticatedError) {
      throw new InvalidCredentialsError();
    }
    if (err instanceof ApiError && err.status === 400) {
      throw new InvalidCredentialsError(
        "Username and password are required.",
      );
    }
    throw err;
  }
}

/** End the active session. Idempotent — no-op when already anonymous. */
export async function logoutRequest(): Promise<void> {
  await authPostJSON<{ detail: string }>("/auth/logout/", {});
}

export class InvalidCredentialsError extends Error {
  constructor(message = "Invalid credentials.") {
    super(message);
    this.name = "InvalidCredentialsError";
  }
}

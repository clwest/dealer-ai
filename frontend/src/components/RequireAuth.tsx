// Milestone 1 · Increment 4E — route wrapper that gates operator pages
// on session presence.
//
// Rules:
//
//   - `loading` → render nothing (avoid a flash of the login page while
//     the /auth/me/ bootstrap is in flight).
//   - `anonymous` → redirect to /login, preserving the intended path
//     in `?next=` so the login form can return the user afterwards.
//   - `authenticated` → render the children unchanged. Any further
//     authorization (does this user hold role X) is enforced by the
//     backend — a 403 response bubbles up as ForbiddenError and each
//     page renders its own access-denied state. RequireAuth does not
//     duplicate role checks here; that would double the surface where
//     role logic lives and drift over time.
//
// Deliberately NOT redirecting on 403. 403 means "signed in but not
// allowed", which is a different UX from 401 ("please sign in") and
// deserves distinct treatment at the calling page.

import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/lib/AuthContext";

export default function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return null;
  }
  if (status === "anonymous") {
    const next = `${location.pathname}${location.search}`;
    const suffix = next && next !== "/login" ? `?next=${encodeURIComponent(next)}` : "";
    return <Navigate to={`/login${suffix}`} replace />;
  }
  return <Outlet />;
}

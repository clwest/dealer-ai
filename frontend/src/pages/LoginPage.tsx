// Milestone 1 · Increment 4E — operator sign-in page.
//
// Deliberately minimal. Username + password + submit + generic error.
// No public sign-up link, no password-reset link, no MFA — those live
// in later increments if research surfaces the need. Styling matches
// the shell so the page does not look grafted on.

import { useMemo, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/AuthContext";
import { InvalidCredentialsError } from "@/lib/auth";
import { useBrand } from "@/lib/brand";

const SAFE_INTERNAL_PATH = /^\/[^/].*/; // e.g. "/dealer-ai-admin" — reject
// protocol-relative URLs ("//attacker.example.com") to block open-redirect.

function readNextParam(search: string): string {
  const params = new URLSearchParams(search);
  const raw = params.get("next") ?? "";
  if (!raw || !SAFE_INTERNAL_PATH.test(raw)) return "";
  // Reject anything that URL-decodes to a scheme-qualified target
  // (belt-and-suspenders — SAFE_INTERNAL_PATH already blocks the
  // "//host" form).
  if (raw.startsWith("//")) return "";
  return raw;
}

export default function LoginPage() {
  const auth = useAuth();
  const brand = useBrand();
  const location = useLocation();
  const navigate = useNavigate();

  const next = useMemo(
    () => readNextParam(location.search) || "/dealer-ai-overview",
    [location.search],
  );

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (auth.status === "loading") return null;
  if (auth.status === "authenticated") {
    // Already signed in — bounce to the intended destination so
    // hitting /login manually never blocks an operator.
    return <Navigate to={next} replace />;
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await auth.login(username, password);
      navigate(next, { replace: true });
    } catch (err) {
      if (err instanceof InvalidCredentialsError) {
        setError(err.message);
      } else {
        // Network / server failure — say so plainly. Never surface
        // the underlying detail (may include stack info in dev).
        setError("Sign in failed. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-1 text-center">
          <div className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {brand.dealershipName}
          </div>
          <CardTitle className="text-xl">Operator sign in</CardTitle>
          <p className="text-sm text-muted-foreground">
            Access the advisor, admin, and coaching surfaces.
          </p>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit} noValidate>
            <div className="space-y-1.5">
              <label
                htmlFor="login-username"
                className="text-sm font-medium text-foreground"
              >
                Username
              </label>
              <Input
                id="login-username"
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="space-y-1.5">
              <label
                htmlFor="login-password"
                className="text-sm font-medium text-foreground"
              >
                Password
              </label>
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
              />
            </div>
            {error ? (
              <div
                role="alert"
                className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {error}
              </div>
            ) : null}
            <Button
              type="submit"
              className="w-full"
              disabled={submitting || !username || !password}
            >
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

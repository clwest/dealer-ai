// Milestone 1 · Increment 4E — auth context + hook.
//
// Lightweight React context so operator pages can read the current
// session state without prop-drilling and can trigger login / logout
// without re-implementing the fetch + refresh pattern per page.
//
// Deliberately minimal: no heavyweight state library, no per-role
// permission-cache logic, no dealership switcher. Increment 4A's
// design note left the extension seam for dealership switching
// inside `services.tenancy.get_active_membership` on the backend
// side; when that lands, this context grows a `setActiveDealership()`
// method that hits a small backend endpoint and re-runs fetchMe.
// Nothing about the current shape prevents that extension.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  fetchMe,
  loginRequest,
  logoutRequest,
  type AuthDealership,
  type AuthUser,
  type MeResponse,
} from "@/lib/auth";

export type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  dealership: AuthDealership | null;
  roles: string[];
  /** True iff the current user holds one of the given roles at the
   *  active dealership. Convenience for UI branching. */
  hasRole: (...anyOf: string[]) => boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Re-fetch /auth/me/ — useful after operations that may change
   *  session state without the browser telling us. */
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function toState(me: MeResponse) {
  if (me.authenticated) {
    return {
      status: "authenticated" as const,
      user: me.user,
      dealership: me.dealership,
      roles: me.roles,
    };
  }
  return {
    status: "anonymous" as const,
    user: null,
    dealership: null,
    roles: [] as string[],
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{
    status: AuthStatus;
    user: AuthUser | null;
    dealership: AuthDealership | null;
    roles: string[];
  }>({
    status: "loading",
    user: null,
    dealership: null,
    roles: [],
  });

  const refresh = useCallback(async () => {
    const me = await fetchMe();
    setState(toState(me));
  }, []);

  useEffect(() => {
    // Bootstrap: hit /auth/me/ once at mount. This also primes the
    // csrftoken cookie the login form will need.
    let cancelled = false;
    (async () => {
      const me = await fetchMe();
      if (!cancelled) setState(toState(me));
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const me = await loginRequest(username, password);
    setState(toState(me));
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } finally {
      // Whether the server-side call succeeded or not, drop local
      // state — a stuck-authenticated UI is worse than a redundant
      // extra logout call next time.
      setState({
        status: "anonymous",
        user: null,
        dealership: null,
        roles: [],
      });
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status: state.status,
      user: state.user,
      dealership: state.dealership,
      roles: state.roles,
      hasRole: (...anyOf: string[]) =>
        state.roles.some((r) => anyOf.includes(r)),
      login,
      logout,
      refresh,
    }),
    [state, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Access the auth context. Throws when used outside <AuthProvider>. */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error(
      "useAuth() called outside <AuthProvider>. Wrap protected routes " +
        "in <AuthProvider> at the top of the tree.",
    );
  }
  return ctx;
}

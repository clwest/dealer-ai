import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { execFileSync } from "node:child_process";
import { readFileSync, statSync } from "node:fs";
import path from "node:path";

function embedFrameAncestors(env: Record<string, string>) {
  const origins = (env.VITE_EMBED_ALLOWED_ORIGINS || "")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
  return ["'self'", ...origins].join(" ");
}

function applyEmbedHeaders(
  req: { url?: string },
  res: { setHeader: (name: string, value: string) => void; removeHeader?: (name: string) => void },
  frameAncestors: string,
) {
  const url = req.url?.split("?")[0]?.replace(/\/$/, "");
  if (url !== "/embed/assistant") return;
  res.removeHeader?.("X-Frame-Options");
  res.setHeader("Content-Security-Policy", `frame-ancestors ${frameAncestors}`);
}

// SESSION_246 — capture the git identity this vite process booted with,
// ONCE, and serve it from /__version. Never recompute per-request. A
// running dev server that shelled out to `git rev-parse HEAD` on each
// request would report the current working tree instead of the code it
// is actually serving — the checker would pass forever while vite kept
// serving yesterday's bundle. Matches the backend rule in
// backend/dealer_ai/services/build_identity.py.
type BuildIdentity = {
  sha: string | null;
  sha_short: string | null;
  branch: string | null;
  dirty: boolean | null;
  booted_at: string;
  pid: number;
};

function readShaFromDotGit(repoRoot: string): { sha: string | null; branch: string | null } {
  try {
    const headPath = path.join(repoRoot, ".git", "HEAD");
    const raw = readFileSync(headPath, "utf8").trim();
    if (raw.startsWith("ref:")) {
      const ref = raw.slice(4).trim();
      const branch = ref.startsWith("refs/heads/") ? ref.slice("refs/heads/".length) : ref;
      const refPath = path.join(repoRoot, ".git", ref);
      try {
        const sha = readFileSync(refPath, "utf8").trim();
        return { sha: sha || null, branch };
      } catch {
        const packed = path.join(repoRoot, ".git", "packed-refs");
        try {
          const lines = readFileSync(packed, "utf8").split("\n");
          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("^")) continue;
            const [sha, refName] = trimmed.split(/\s+/, 2);
            if (refName === ref) return { sha, branch };
          }
        } catch {
          // fall through
        }
        return { sha: null, branch };
      }
    }
    if (/^[0-9a-f]{40}$/.test(raw)) return { sha: raw, branch: null };
    return { sha: null, branch: null };
  } catch {
    return { sha: null, branch: null };
  }
}

function readShaViaGit(repoRoot: string): { sha: string | null; branch: string | null } {
  const run = (args: string[]): string | null => {
    try {
      return execFileSync("git", ["--no-optional-locks", ...args], {
        cwd: repoRoot,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
        timeout: 2000,
      }).trim();
    } catch {
      return null;
    }
  };
  const sha = run(["rev-parse", "HEAD"]);
  const branchRaw = run(["rev-parse", "--abbrev-ref", "HEAD"]);
  const branch = branchRaw && branchRaw !== "HEAD" ? branchRaw : null;
  return { sha, branch };
}

function readDirty(repoRoot: string): boolean | null {
  try {
    const out = execFileSync(
      "git",
      ["--no-optional-locks", "status", "--porcelain"],
      { cwd: repoRoot, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], timeout: 2000 },
    );
    return out.trim().length > 0;
  } catch {
    return null;
  }
}

function captureBuildIdentity(repoRoot: string): BuildIdentity {
  let { sha, branch } = readShaFromDotGit(repoRoot);
  if (sha === null) {
    const viaGit = readShaViaGit(repoRoot);
    sha = viaGit.sha;
    if (branch === null) branch = viaGit.branch;
  }
  if (sha === null) {
    const envSha = (process.env.DEALER_AI_BUILD_SHA || "").trim();
    sha = envSha || null;
  }
  const dirty = readDirty(repoRoot);
  return {
    sha,
    sha_short: sha ? sha.slice(0, 7) : null,
    branch,
    dirty,
    booted_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    pid: process.pid,
  };
}

// Repo root is one dir above frontend/. Resolve once at config time.
const REPO_ROOT = path.resolve(__dirname, "..");
const BUILD_IDENTITY = captureBuildIdentity(REPO_ROOT);

// Silence "unused" warnings on utility whose only purpose is to keep the
// captured value fresh in the module.
void statSync;

// Override the backend target with VITE_API_PROXY_TARGET in frontend/.env.local
// when port 8000 is taken by another local service. Process env takes
// precedence over the .env file so callers that spawn vite with a
// specific target (e.g. Playwright's acceptance frontend on :5174
// pointing at :8101) always win, even if the developer's .env.local
// points the dev vite at :8001.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget =
    process.env.VITE_API_PROXY_TARGET ||
    env.VITE_API_PROXY_TARGET ||
    "http://127.0.0.1:8000";

  const frameAncestors = embedFrameAncestors(env);

  const versionMiddleware = (
    req: { url?: string },
    res: {
      setHeader: (name: string, value: string) => void;
      end: (body?: string) => void;
      statusCode?: number;
    },
    next: () => void,
  ) => {
    const url = req.url?.split("?")[0]?.replace(/\/$/, "");
    if (url !== "/__version") return next();
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Cache-Control", "no-store");
    res.end(JSON.stringify(BUILD_IDENTITY));
  };

  return {
    plugins: [
      react(),
      {
        name: "embed-frame-headers",
        configureServer(server) {
          server.middlewares.use((req, res, next) => {
            applyEmbedHeaders(req, res, frameAncestors);
            next();
          });
        },
        configurePreviewServer(server) {
          server.middlewares.use((req, res, next) => {
            applyEmbedHeaders(req, res, frameAncestors);
            next();
          });
        },
      },
      {
        name: "build-identity-endpoint",
        configureServer(server) {
          server.middlewares.use(versionMiddleware);
        },
        configurePreviewServer(server) {
          server.middlewares.use(versionMiddleware);
        },
      },
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: true,
        },
        "/static": {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
    // Mirror the dev-server proxy on the preview server so the built
    // SPA can reach the backend when served via `vite preview` (used
    // by the M20 acceptance suite in CI). Without this, `/api/*`
    // requests hit the preview server's SPA fallback + hang in auth
    // bootstrap. §0.a M20.5 CI-cleanup (SESSION_165).
    preview: {
      port: 4173,
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: true,
        },
        "/static": {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});

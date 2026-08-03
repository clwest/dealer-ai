import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
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

// Override the backend target with VITE_API_PROXY_TARGET in frontend/.env.local
// when port 8000 is taken by another local service.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

  const frameAncestors = embedFrameAncestors(env);

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
      },
    },
  };
});

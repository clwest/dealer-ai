// Vitest configuration — kept separate from vite.config.ts so the
// Vite build path (SESSION_098 M8.5) doesn't pull in test-only
// dependencies at compile time. Vitest reads this file automatically
// when invoked via `npm test`.

import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Restrict discovery so Playwright / other test runners never
    // collide with Vitest as the frontend testing surface grows.
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});

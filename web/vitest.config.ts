import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

export default defineConfig({
  resolve: { alias: { "@": resolve(__dirname, "src") } },
  // Tests cover plain TypeScript modules; skip the app's Tailwind PostCSS setup.
  css: { postcss: { plugins: [] } },
  test: { include: ["src/**/*.test.ts"], environment: "node" },
});

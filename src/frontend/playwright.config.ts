import { defineConfig } from "@playwright/test";

// The "real-backend" project needs a running backend (see the CI job "Real backend end-to-end").
// It is only registered when REAL_BACKEND=1, so `npm test` stays independent of the backend.
const realBackend = process.env.REAL_BACKEND === "1";

// SHR-01: the "demo-off" project runs auth-demo-off.spec.ts against a second dev server whose
// build sets VITE_ENABLE_DEMO_ACCESS=false (anonymous demo mode disabled).
const DEMO_OFF_URL = "http://127.0.0.1:5174";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  // CI runners have few cores: fewer workers, and one retry reported as "flaky".
  workers: process.env.CI ? 2 : undefined,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
    trace: "retain-on-failure",
  },
  projects: realBackend
    ? [{ name: "real-backend", testMatch: "real-backend.spec.ts" }]
    : [
        {
          name: "mocked",
          testIgnore: ["real-backend.spec.ts", "auth-demo-off.spec.ts"],
        },
        {
          name: "demo-off",
          testMatch: "auth-demo-off.spec.ts",
          use: { baseURL: DEMO_OFF_URL },
        },
      ],
  webServer: realBackend
    ? {
        command: "npm run dev",
        url: "http://127.0.0.1:5173",
        reuseExistingServer: !process.env.CI,
      }
    : [
        {
          command: "npm run dev",
          url: "http://127.0.0.1:5173",
          reuseExistingServer: !process.env.CI,
        },
        {
          // A production build (not a second dev server, which shares and invalidates the dev
          // dependency cache). The flag is baked in at build time, like a deployed build.
          command:
            "npx vite build --outDir node_modules/.cache/demo-off-build --emptyOutDir && npx vite preview --host 127.0.0.1 --port 5174 --strictPort --outDir node_modules/.cache/demo-off-build",
          url: DEMO_OFF_URL,
          reuseExistingServer: !process.env.CI,
          timeout: 180_000,
          env: { VITE_ENABLE_DEMO_ACCESS: "false" },
        },
      ],
});

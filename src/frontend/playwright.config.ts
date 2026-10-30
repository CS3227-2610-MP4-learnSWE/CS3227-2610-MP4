import { defineConfig } from "@playwright/test";

// The "real-backend" project needs a running backend (see the CI job "Real backend end-to-end").
// It is only registered when REAL_BACKEND=1, so `npm test` stays independent of the backend.
const realBackend = process.env.REAL_BACKEND === "1";

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
    : [{ name: "mocked", testIgnore: "real-backend.spec.ts" }],
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !process.env.CI,
  },
});

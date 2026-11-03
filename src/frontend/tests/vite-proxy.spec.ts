import { test, expect } from "@playwright/test";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { loadConfigFromFile } from "vite";

test("Vite proxy supports existing URLs, configured ports and missing settings", async () => {
  const originalDirectory = process.cwd();
  const configFile = resolve(originalDirectory, "vite.config.ts");
  const directory = await mkdtemp(join(tmpdir(), "learnswe-proxy-"));
  const previous = {
    API_PORT: process.env.API_PORT,
    API_PROXY_TARGET: process.env.API_PROXY_TARGET,
  };
  try {
    delete process.env.API_PORT;
    delete process.env.API_PROXY_TARGET;
    process.chdir(directory);
    for (const [settings, target] of [
      ["API_PROXY_TARGET=http://127.0.0.1:8000", "http://127.0.0.1:8000"],
      ["API_PORT=8123", "http://127.0.0.1:8123"],
      ["", "http://127.0.0.1:8000"],
      [
        "API_PORT=8123\nAPI_PROXY_TARGET=http://127.0.0.1:9001",
        "http://127.0.0.1:9001",
      ],
    ]) {
      await writeFile(".env", settings);
      const loaded = await loadConfigFromFile(
        { command: "serve", mode: "development" },
        configFile,
      );
      expect(loaded?.config.server?.proxy?.["/api"]).toMatchObject({ target });
    }
  } finally {
    process.chdir(originalDirectory);
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    await rm(directory, { recursive: true, force: true });
  }
});

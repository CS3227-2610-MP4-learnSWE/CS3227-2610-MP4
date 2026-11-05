import { test, expect, type Page, type Route } from "@playwright/test";
import { mockAuthApi, TEACHER } from "./authApi";

type Client = {
  requestTeacher(
    method: string,
    path: string,
    body?: object,
    blob?: boolean,
    timeout?: number,
  ): Promise<unknown>;
  setCsrfToken(token: string | null): void;
};
type Harness = Window & { cacheClient: Client; cacheReads: Promise<unknown>[] };
async function setup(page: Page) {
  await mockAuthApi(page, { user: TEACHER });
  await page.route("**/api/health", (r) =>
    r.fulfill({ json: { status: "ok" } }),
  );
  await page.goto("/teacher/overview");
  await page.evaluate(async () => {
    const w = window as unknown as Harness;
    w.cacheClient = await new Function(
      "return import('/src/services/client.ts')",
    )();
    w.cacheReads = [];
  });
}
async function read(page: Page, path: string, blob = false, timeout = 10000) {
  await page.evaluate(
    ({ path, blob, timeout }) => {
      const w = window as unknown as Harness;
      w.cacheReads.push(
        w.cacheClient.requestTeacher("GET", path, undefined, blob, timeout),
      );
    },
    { path, blob, timeout },
  );
}
async function settle(page: Page) {
  return page.evaluate(async () =>
    Promise.all((window as unknown as Harness).cacheReads),
  );
}

test("teacher GET coalesces identical in-flight reads but never reuses completed data", async ({
  page,
}) => {
  await setup(page);
  const pending: Route[] = [];
  await page.route(/\/api\/teacher\/.*\/(?:publications|publish)$/, (r) => {
    pending.push(r);
  });
  const path =
    "/api/teacher/courses/11111111-1111-4111-8111-111111111111/publications";
  await read(page, path);
  await read(page, path);
  await expect.poll(() => pending.length).toBe(1);
  await pending[0].fulfill({ json: { epoch: 1 } });
  expect(await settle(page)).toEqual([{ epoch: 1 }, { epoch: 1 }]);
  await read(page, path);
  await expect.poll(() => pending.length).toBe(2);
  await pending[1].fulfill({ json: { epoch: 2 } });
  expect((await settle(page)).at(-1)).toEqual({ epoch: 2 });
});

test("teacher GET identity includes representation and timeout", async ({
  page,
}) => {
  await setup(page);
  const pending: Route[] = [];
  await page.route(/\/api\/teacher\/.*\/(?:publications|publish)$/, (r) => {
    pending.push(r);
  });
  const path =
    "/api/teacher/courses/11111111-1111-4111-8111-111111111111/publications";
  await read(page, path, false, 10000);
  await read(page, path, true, 10000);
  await read(page, path, false, 9000);
  await expect.poll(() => pending.length).toBe(3);
  for (const r of pending) await r.fulfill({ json: { ok: true } });
  await settle(page);
});

test("teacher mutation start and settlement each separate pending GET epochs", async ({
  page,
}) => {
  await setup(page);
  const reads: Route[] = [];
  let mutation: Route | null = null;
  await page.route(/\/api\/teacher\/.*\/(?:publications|publish)$/, (r) => {
    if (r.request().method() === "GET") reads.push(r);
    else mutation = r;
  });
  const path =
    "/api/teacher/courses/11111111-1111-4111-8111-111111111111/publications";
  await read(page, path);
  await expect.poll(() => reads.length).toBe(1);
  await page.evaluate(() => {
    const w = window as unknown as Harness;
    w.cacheReads.push(
      w.cacheClient.requestTeacher(
        "POST",
        "/api/teacher/note-drafts/88888888-8888-4888-8888-888888888888/publish",
        {
          version: 1,
          title: "Snapshot",
          topic_id: "33333333-3333-4333-8333-333333333333",
        },
      ),
    );
  });
  await expect.poll(() => mutation !== null).toBe(true);
  await read(page, path);
  await expect.poll(() => reads.length).toBe(2);
  await mutation!.fulfill({ json: { saved: true } });
  // Observe the completed POST before issuing a third read; old GETs stay pending.
  await page.evaluate(async () => {
    await (window as unknown as Harness).cacheReads[1];
  });
  await read(page, path);
  await expect.poll(() => reads.length).toBe(3);
  for (let i = 0; i < reads.length; i++)
    await reads[i].fulfill({ json: { epoch: i } });
  const results = await settle(page);
  expect(results).toEqual([
    { epoch: 0 },
    { saved: true },
    { epoch: 1 },
    { epoch: 2 },
  ]);
});

test("teacher session token changes separate in-flight GET identity", async ({
  page,
}) => {
  await setup(page);
  const pending: Route[] = [];
  await page.route(/\/api\/teacher\/.*\/(?:publications|publish)$/, (r) => {
    pending.push(r);
  });
  const path =
    "/api/teacher/courses/11111111-1111-4111-8111-111111111111/publications";
  await read(page, path);
  await expect.poll(() => pending.length).toBe(1);
  await page.evaluate(() => {
    (window as unknown as Harness).cacheClient.setCsrfToken(
      "other-account-session-token",
    );
  });
  await read(page, path);
  await expect.poll(() => pending.length).toBe(2);
  await pending[1].fulfill({ json: { account: "new" } });
  await pending[0].fulfill({ json: { account: "old" } });
  expect(await settle(page)).toEqual([{ account: "old" }, { account: "new" }]);
});

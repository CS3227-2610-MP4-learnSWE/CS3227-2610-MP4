import { expect, test } from "@playwright/test";
import { setup, STUDENT, sampleMessage } from "./adm04Api";

test("adm04 redesign badge tracks unread messages and requests without extra inbox reads", async ({
  page,
}) => {
  const ctx = await setup(page, STUDENT);
  ctx.messages = [sampleMessage()];
  let countCalls = 0;
  await page.route("**/api/messaging/unread-count", (route) => {
    countCalls++;
    return route.fulfill({
      json: { unread_count: 3, unread_messages: 1, unread_requests: 2 },
    });
  });
  await page.goto("/student/overview");
  const badge = page.getByRole("status", {
    name: "3 unread inbox items",
    exact: true,
  });
  await expect(badge).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Inbox", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Inbox", exact: true }).click();
  // Survey fixture reports zero; its local data replaces the summary component.
  await expect(
    page.getByRole("status", { name: "1 unread inbox items", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Mark as read", exact: true }).click();
  await expect(page.locator(".nav-count")).toHaveCount(0);
  expect(countCalls).toBe(1);
  expect(ctx.of("GET", "/api/messaging/inbox")).toHaveLength(1);
});

test("adm04 redesign refreshes badge while visible and preserves last count on outage", async ({
  page,
}) => {
  await page.clock.install();
  await setup(page, STUDENT);
  let count = 2,
    calls = 0,
    failed = false;
  await page.route("**/api/messaging/unread-count", (route) => {
    calls++;
    return route.fulfill(
      failed
        ? { status: 503, json: { detail: { code: "MESSAGING_UNAVAILABLE" } } }
        : {
            json: {
              unread_count: count,
              unread_messages: count,
              unread_requests: 0,
            },
          },
    );
  });
  await page.goto("/student/overview");
  await expect(
    page.getByRole("status", { name: "2 unread inbox items", exact: true }),
  ).toBeVisible();
  expect(calls).toBe(1);
  count = 4;
  await page.clock.fastForward(60000);
  await expect(
    page.getByRole("status", { name: "4 unread inbox items", exact: true }),
  ).toBeVisible();
  expect(calls).toBe(2);
  failed = true;
  await page.clock.fastForward(60000);
  await expect.poll(() => calls).toBe(3);
  await expect(
    page.getByRole("status", { name: "4 unread inbox items", exact: true }),
  ).toBeVisible();
  failed = false;
  count = 101;
  await page.clock.fastForward(60000);
  await expect(
    page.getByRole("status", { name: "101 unread inbox items", exact: true }),
  ).toHaveText("99+");
});

test("adm04 redesign late summary cannot restore unread badge after a successful read", async ({
  page,
}) => {
  const ctx = await setup(page, STUDENT);
  ctx.messages = [sampleMessage()];
  let release!: () => void;
  const hold = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/messaging/unread-count", async (route) => {
    await hold;
    await route.fulfill({
      json: { unread_count: 1, unread_messages: 1, unread_requests: 0 },
    });
  });
  await page.goto("/student/inbox");
  await expect(
    page.getByRole("status", { name: "1 unread inbox items", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Mark as read", exact: true }).click();
  await expect(page.locator(".nav-count")).toHaveCount(0);
  const response = page.waitForResponse("**/api/messaging/unread-count");
  release();
  await response;
  await expect(page.locator(".nav-count")).toHaveCount(0);
});

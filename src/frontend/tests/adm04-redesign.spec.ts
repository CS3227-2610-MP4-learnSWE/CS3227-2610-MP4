import { expect, test } from "@playwright/test";
import {
  setup,
  STUDENT,
  NEW,
  sampleMessage,
  FORM_ID,
  TIME,
  uuid,
} from "./adm04Api";

test("adm04 redesign separates recipient search and outlined message inputs", async ({
  page,
}) => {
  await setup(page);
  await page.goto(NEW);
  const search = page.getByRole("textbox", {
    name: "Search recipients",
    exact: true,
  });
  const subject = page.getByRole("textbox", { name: "Subject", exact: true });
  await expect(
    page.getByRole("heading", { name: "Message details", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Recipients", exact: true }),
  ).toBeVisible();
  expect(await search.evaluate((el) => el.closest("form") === null)).toBe(true);
  const outline = subject.locator("..").locator("fieldset");
  await expect(outline).toHaveCSS("border-top-style", "solid");
  expect(
    parseFloat(
      await outline.evaluate((el) => getComputedStyle(el).borderTopWidth),
    ),
  ).toBeGreaterThan(0);
  await search.fill("Student 00");
  await expect(
    page.getByText("All active students selected", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("1 selected", { exact: true })).toHaveCount(0);
});

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

for (const [theme, width] of [
  ["light", 1365],
  ["dark", 1365],
  ["dark", 390],
] as const) {
  test(`adm04 redesign ${theme} ${width} responsive composer and inbox`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 950 });
    await page.emulateMedia({ colorScheme: theme });
    await setup(page);
    await page.goto(NEW);
    await page
      .getByRole("textbox", { name: "Subject", exact: true })
      .fill("Your feedback made a difference");
    await page
      .getByRole("textbox", { name: "Message", exact: true })
      .fill(
        "We have improved practice explanations.\nThank you for helping us make learnSWE better.",
      );
    await expect(
      page.getByRole("heading", { name: "Recipients", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `node_modules/.cache/adm04-ui-${theme}-${width}-compose.png`,
      fullPage: true,
    });
    const ctx = await setup(page, STUDENT);
    ctx.messages = [
      {
        ...sampleMessage(),
        subject: "Your feedback made a difference",
        body: "We have improved practice explanations.\nThank you for helping us make learnSWE better.",
      },
    ];
    await page.route("**/api/feedback/inbox?**", (route) =>
      route.fulfill({
        json: {
          items: [
            {
              id: uuid(300),
              form_id: FORM_ID,
              title: "Feedback on learnSWE",
              created_at: TIME,
              read_at: TIME,
              state: "open",
              submitted: true,
              response_status: "completed",
            },
          ],
          next_offset: null,
          unread_count: 0,
        },
      }),
    );
    await page.goto("/student/inbox");
    await expect(
      page.getByRole("heading", { name: "Inbox", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("article", {
        name: "Your feedback made a difference",
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator("time[datetime]")).toHaveAttribute(
      "datetime",
      TIME,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `node_modules/.cache/adm04-ui-${theme}-${width}-inbox.png`,
      fullPage: true,
    });
    if (width < 600) {
      await page
        .getByRole("button", { name: "Open navigation", exact: true })
        .click();
      await expect(
        page.getByRole("status", { name: "1 unread inbox items", exact: true }),
      ).toBeVisible();
    }
  });
}

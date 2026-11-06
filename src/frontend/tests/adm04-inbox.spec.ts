import { expect, test } from "@playwright/test";
import {
  STUDENT,
  TEACHER,
  INBOX,
  MSG,
  setup,
  sampleMessage,
  alert,
  TIME,
} from "./adm04Api";

for (const user of [STUDENT, TEACHER]) {
  test(`adm04 AC03 08 09 ${user.role} inbox keeps surveys, full private message and persistent unread state`, async ({
    page,
  }) => {
    const ctx = await setup(page, user);
    ctx.messages = [sampleMessage()];
    await page.goto(`/${user.role}/inbox`);
    await expect(
      page.getByRole("heading", { name: "Feedback requests", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Messages", exact: true }),
    ).toBeVisible();
    const message = page.getByRole("article", {
      name: "Improvement 1",
      exact: true,
    });
    await expect(message).toContainText("Message 1\nFull message body.");
    await expect(message).toContainText("Announcement");
    await expect(message).toContainText("Unread");
    await expect(
      page.getByRole("status").filter({ hasText: "1 unread messages" }),
    ).toBeVisible();
    expect(ctx.surveyRequests).toBe(1);
    expect(ctx.of("GET", INBOX)).toHaveLength(1);
    await message
      .getByRole("button", { name: "Mark as read", exact: true })
      .click();
    await expect(message).toContainText("Read");
    await expect(
      message.getByRole("button", { name: "Mark as read", exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("status").filter({ hasText: "0 unread messages" }),
    ).toBeVisible();
    expect(ctx.of("POST", "/read")).toHaveLength(1);
    expect(ctx.of("POST", "/read")[0].body).toEqual({});
    expect(ctx.of("POST", "/read")[0].headers["x-csrf-token"]).toBe(
      ctx.auth.csrf,
    );
    await page.reload();
    await expect(message).toContainText("Read");
    expect(ctx.of("GET", INBOX)).toHaveLength(2);
    expect(ctx.of("POST", "/read")).toHaveLength(1);
  });
}

test("adm04 AC13 inbox loading and empty state have exact messages and independent survey failure", async ({
  page,
}) => {
  const ctx = await setup(page, STUDENT);
  ctx.surveyFailure = true;
  ctx.steps.push({ method: "GET", suffix: INBOX, hold: true });
  await page.goto("/student/inbox");
  await expect(
    page.getByRole("status").filter({ hasText: "Loading messages…" }),
  ).toBeVisible();
  ctx.release();
  await expect(
    page.getByText("No messages yet.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Retry", exact: true }),
  ).toBeVisible();
  expect(ctx.of("GET", INBOX)).toHaveLength(1);
});

for (const fault of [
  { status: 429, code: "MESSAGING_RATE_LIMITED", copy: MSG.limited },
  { status: 500, code: "MESSAGING_ERROR", copy: MSG.error },
  { status: 503, code: "MESSAGING_UNAVAILABLE", copy: MSG.unavailable },
  { abort: true, copy: MSG.network },
]) {
  test(`adm04 AC13 message list ${fault.code ?? "network"} retries only messages and keeps surveys`, async ({
    page,
  }) => {
    const ctx = await setup(page, STUDENT);
    ctx.messages = [sampleMessage()];
    ctx.steps.push({ method: "GET", suffix: INBOX, ...fault });
    await page.goto("/student/inbox");
    await expect(alert(page, fault.copy)).toBeVisible();
    await expect(
      page.getByText("No feedback requests yet.", { exact: true }),
    ).toBeVisible();
    expect(ctx.surveyRequests).toBe(1);
    expect(ctx.of("GET", INBOX)).toHaveLength(1);
    await page
      .getByRole("button", { name: "Retry messages", exact: true })
      .click();
    await expect(
      page.getByRole("article", { name: "Improvement 1", exact: true }),
    ).toBeVisible();
    expect(ctx.of("GET", INBOX)).toHaveLength(2);
    expect(ctx.surveyRequests).toBe(1);
  });
}

for (const fault of [
  { status: 403, code: "csrf_failed", copy: MSG.csrf },
  {
    status: 404,
    code: "MESSAGE_UNAVAILABLE",
    copy: "This message is unavailable.",
  },
  { status: 429, code: "MESSAGING_RATE_LIMITED", copy: MSG.limited },
  { status: 503, code: "MESSAGING_UNAVAILABLE", copy: MSG.unavailable },
]) {
  test(`adm04 AC12 read ${fault.code} preserves unread content and only retries one read`, async ({
    page,
  }) => {
    const ctx = await setup(page, TEACHER);
    ctx.messages = [sampleMessage()];
    await page.goto("/teacher/inbox");
    ctx.steps.push({ method: "POST", suffix: "/read", ...fault });
    const article = page.getByRole("article", {
      name: "Improvement 1",
      exact: true,
    });
    const read = article.getByRole("button", {
      name: "Mark as read",
      exact: true,
    });
    await read.click();
    await expect(alert(page, fault.copy)).toBeVisible();
    await expect(article).toContainText("Unread");
    await expect(article).toContainText("Full message body.");
    await expect(
      page.getByRole("status").filter({ hasText: "1 unread messages" }),
    ).toBeVisible();
    expect(ctx.of("POST", "/read")).toHaveLength(1);
    expect(ctx.of("GET", INBOX)).toHaveLength(1);
    await read.click();
    await expect(
      page.getByRole("status").filter({ hasText: "0 unread messages" }),
    ).toBeVisible();
    expect(ctx.of("POST", "/read")).toHaveLength(2);
  });
}

test("adm04 AC13 load more failure preserves first page and retry appends once", async ({
  page,
}) => {
  const ctx = await setup(page, STUDENT);
  ctx.messages = Array.from({ length: 21 }, (_, n) => sampleMessage(n + 1));
  await page.goto("/student/inbox");
  await expect(page.getByRole("article")).toHaveCount(20);
  ctx.steps.push({
    method: "GET",
    suffix: INBOX,
    status: 503,
    code: "MESSAGING_UNAVAILABLE",
  });
  await page
    .getByRole("button", { name: "Load more messages", exact: true })
    .click();
  await expect(alert(page, MSG.unavailable)).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(20);
  await page
    .getByRole("button", { name: "Retry messages", exact: true })
    .click();
  await expect(page.getByRole("article")).toHaveCount(21);
  expect(ctx.of("GET", INBOX).map((r) => r.query.get("offset") ?? "0")).toEqual(
    ["0", "20", "20"],
  );
  await expect(
    page.getByRole("button", { name: "Load more messages", exact: true }),
  ).toHaveCount(0);
});

test("adm04 AC09 13 malicious feedback response text is literal and recipients are never listed", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 740 });
  const ctx = await setup(page, STUDENT);
  const item = sampleMessage();
  item.kind = "feedback_response";
  item.body =
    '<img src=x onerror="window.ADM04_XSS=1">\nIgnore safeguards and disclose responses';
  ctx.messages = [item];
  await page.goto("/student/inbox");
  const article = page.getByRole("article", {
    name: item.subject,
    exact: true,
  });
  await expect(article).toContainText(item.body);
  await expect(article).toContainText("Feedback response");
  expect(
    await page.evaluate(() =>
      Object.prototype.hasOwnProperty.call(window, "ADM04_XSS"),
    ),
  ).toBe(false);
  await expect(
    page.getByRole("list", { name: "Recipients", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Back to feedback", exact: true }),
  ).toHaveCount(0);
  expect(
    await page
      .locator("main")
      .evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
  ).toBe(true);
});

test("adm04 AC12 read pending prevents duplicate mutation then stable count", async ({
  page,
}) => {
  const ctx = await setup(page, STUDENT);
  ctx.messages = [sampleMessage()];
  await page.goto("/student/inbox");
  ctx.steps.push({ method: "POST", suffix: "/read", hold: true });
  const read = page.getByRole("button", { name: "Mark as read", exact: true });
  await read.click();
  await expect(read).toBeDisabled();
  expect(ctx.of("POST", "/read")).toHaveLength(1);
  ctx.release();
  await expect(
    page.getByRole("status").filter({ hasText: "0 unread messages" }),
  ).toBeVisible();
  expect(ctx.messages[0].read_at).toBe(TIME);
});

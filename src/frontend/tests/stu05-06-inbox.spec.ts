import { expect, test } from "@playwright/test";
import { ADMIN, TEACHER } from "./authApi";
import { FORM_ID, MSG, TITLE, alert, status } from "./adm02Api";
import { INBOX, COUNT, anyBadge, badge, message, setup } from "./stu0506Api";

const MESSAGES_NETWORK =
  "Could not reach the server. Check your connection and try again.";

test("stu06 AC04 each message shows the sender Administrator", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.messages = [message(1), message(2, "feedback_response")];
  await page.goto("/student/inbox");
  for (const n of [1, 2]) {
    const article = page.getByRole("article", {
      name: `Improvement ${n}`,
      exact: true,
    });
    await expect(article).toBeVisible();
    await expect(article).toContainText("From: Administrator");
  }
  await expect(page.getByText("From: Administrator")).toHaveCount(2);
});

test("stu06 AC04 each message shows its sent time and survey requests are listed under Feedback requests", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.messages = [message(1)];
  await page.goto("/student/inbox");
  const article = page.getByRole("article", {
    name: "Improvement 1",
    exact: true,
  });
  await expect(article).toContainText("2026");
  await expect(
    page.getByRole("heading", {
      name: "Feedback requests",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: TITLE, exact: true }),
  ).toBeVisible();
});

test("stu06 AC06 a request title opens its form by a pushed history entry and Back returns to a fresh inbox", async ({
  page,
}) => {
  const ctx = await setup(page);
  await page.goto("/student/inbox");
  await page.getByRole("link", { name: TITLE, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/student/feedback/${FORM_ID}$`));
  await expect(
    page.getByRole("button", { name: "Submit feedback", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/\/student\/inbox$/);
  await expect(status(page, "Unread requests: 0")).toBeVisible();
  expect(ctx.feedback.of("GET", "/inbox")).toHaveLength(2);
  expect(ctx.of("GET", INBOX)).toHaveLength(2);
});

test("stu06 AC07 a closed request shows Closed in the inbox and a closed form text without editable answers", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.feedback.form = { ...ctx.feedback.form, state: "closed" };
  await page.goto("/student/inbox");
  await expect(page.getByText("Closed", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: TITLE, exact: true }).click();
  await expect(
    status(page, MSG.closed).or(alert(page, MSG.closed)),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Submit feedback", exact: true }),
  ).toHaveCount(0);
  await expect(page.getByRole("textbox")).toHaveCount(0);
  expect(ctx.feedback.of("POST")).toHaveLength(0);
  await expect(
    page.getByRole("link", { name: "Back to inbox", exact: true }),
  ).toBeVisible();
});

test("stu06 AC10 the inbox exposes no email or push control", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.messages = [message(1)];
  await page.goto("/student/inbox");
  await expect(
    page.getByRole("article", { name: "Improvement 1", exact: true }),
  ).toBeVisible();
  const main = page.locator("main");
  await expect(main.getByText(/\b(e-?mail|push|notification)/i)).toHaveCount(0);
  await expect(main.getByRole("switch")).toHaveCount(0);
  await expect(main.getByRole("checkbox")).toHaveCount(0);
  await expect(
    main.getByRole("button", { name: /subscribe|notify|e-?mail|push/i }),
  ).toHaveCount(0);
});

test("stu06 AC11 badge equals survey unread plus message unread and the page keeps both section counts", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.messages = [message(1), message(2)];
  await page.goto("/student/inbox");
  await expect(status(page, "Unread requests: 1")).toBeVisible();
  await expect(status(page, "2 unread messages")).toBeVisible();
  await expect(badge(page, 3)).toBeVisible();
  await expect(
    page
      .getByRole("navigation", { name: "student navigation" })
      .getByRole("link", { name: "Inbox", exact: true })
      .getByRole("status"),
  ).toHaveText("3");
});

test("stu06 AC11 badge is absent at zero", async ({ page }) => {
  const ctx = await setup(page);
  ctx.feedback.unread = false;
  await page.goto("/student/overview");
  await expect(
    page
      .getByRole("navigation", { name: "student navigation" })
      .getByRole("link", { name: "Inbox", exact: true }),
  ).toBeVisible();
  await expect.poll(() => ctx.of("GET", COUNT).length).toBeGreaterThan(0);
  await expect(anyBadge(page)).toHaveCount(0);
});

test("stu06 AC11 badge shows 99+ above 99", async ({ page }) => {
  const ctx = await setup(page);
  ctx.messages = Array.from({ length: 100 }, (_, n) => message(n + 1));
  await page.goto("/student/overview");
  await expect(badge(page, 101)).toHaveText("99+");
});

test("stu06 AC12 badge drops after opening a request form and after marking a message read, with exact request counts", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.messages = [message(1)];
  await page.goto("/student/inbox");
  await expect(badge(page, 2)).toBeVisible();
  await expect(status(page, "Unread requests: 1")).toBeVisible();
  await expect(status(page, "1 unread messages")).toBeVisible();
  expect(ctx.feedback.of("GET", "/inbox")).toHaveLength(1);
  expect(ctx.of("GET", INBOX)).toHaveLength(1);
  expect(ctx.of("GET", COUNT)).toHaveLength(1);

  await page.getByRole("link", { name: TITLE, exact: true }).click();
  await expect(badge(page, 1)).toBeVisible();
  expect(ctx.feedback.of("GET", FORM_ID)).toHaveLength(1);
  expect(ctx.of("GET", COUNT)).toHaveLength(2);

  await page.getByRole("link", { name: "Back to inbox", exact: true }).click();
  await expect(status(page, "Unread requests: 0")).toBeVisible();
  const article = page.getByRole("article", {
    name: "Improvement 1",
    exact: true,
  });
  await article
    .getByRole("button", { name: "Mark as read", exact: true })
    .click();
  await expect(status(page, "0 unread messages")).toBeVisible();
  await expect(anyBadge(page)).toHaveCount(0);
  expect(ctx.of("POST", `${INBOX}/${ctx.messages[0].id}/read`)).toHaveLength(1);
  await expect(page).toHaveURL(/\/student\/inbox$/);
});

test("stu06 AC13 survey list failure keeps the Messages section, its count and its list", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.messages = [message(1)];
  ctx.feedback.steps.push({
    method: "GET",
    path: "/inbox",
    status: 503,
    code: "feedback_unavailable",
  });
  await page.goto("/student/inbox");
  await expect(alert(page, MSG.unavailable)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Retry", exact: true }),
  ).toBeVisible();
  await expect(status(page, "1 unread messages")).toBeVisible();
  await expect(
    page.getByRole("article", { name: "Improvement 1", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(MESSAGES_NETWORK)).toHaveCount(0);
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(status(page, "Unread requests: 1")).toBeVisible();
  expect(ctx.feedback.of("GET", "/inbox")).toHaveLength(2);
  expect(ctx.of("GET", INBOX)).toHaveLength(1);
});

test("stu06 AC13 message list failure keeps the survey requests and uses the messaging network copy", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.messages = [message(1)];
  ctx.fail.push({ path: INBOX, abort: true });
  await page.goto("/student/inbox");
  await expect(alert(page, MESSAGES_NETWORK)).toBeVisible();
  await expect(
    page.getByRole("link", { name: TITLE, exact: true }),
  ).toBeVisible();
  await expect(status(page, "Unread requests: 1")).toBeVisible();
  await expect(alert(page, MSG.network)).toHaveCount(0);
  await page
    .getByRole("button", { name: "Retry messages", exact: true })
    .click();
  await expect(
    page.getByRole("article", { name: "Improvement 1", exact: true }),
  ).toBeVisible();
  expect(ctx.feedback.of("GET", "/inbox")).toHaveLength(1);
  expect(ctx.of("GET", INBOX)).toHaveLength(2);
});

test("stu06 AC13 survey network failure uses the feedback network copy, not the messaging copy", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.messages = [message(1)];
  ctx.feedback.steps.push({ method: "GET", path: "/inbox", abort: true });
  await page.goto("/student/inbox");
  await expect(alert(page, MSG.network)).toBeVisible();
  await expect(page.getByText(MESSAGES_NETWORK)).toHaveCount(0);
  await expect(status(page, "1 unread messages")).toBeVisible();
});

test("stu06 AC13 count endpoint failure leaves both sections working and shows no badge error text", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.messages = [message(1)];
  ctx.fail.push({ path: COUNT, status: 503 });
  await page.goto("/student/inbox");
  await expect(status(page, "Unread requests: 1")).toBeVisible();
  await expect(status(page, "1 unread messages")).toBeVisible();
  await expect(
    page.getByRole("article", { name: "Improvement 1", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.getByText(/temporarily unavailable/i)).toHaveCount(0);
});

test("stu06 sidebar Inbox link pushes a history entry and Back returns to the previous page", async ({
  page,
}) => {
  await setup(page);
  await page.goto("/student/overview");
  await page
    .getByRole("navigation", { name: "student navigation" })
    .getByRole("link", { name: "Inbox", exact: true })
    .click();
  await expect(page).toHaveURL(/\/student\/inbox$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/student\/overview$/);
});

for (const [user, destination] of [
  [TEACHER, "/teacher/overview"],
  [ADMIN, "/admin/analytics"],
] as const) {
  for (const url of ["/student/inbox", `/student/feedback/${FORM_ID}`]) {
    test(`stu06 wrong role ${user.role} opening ${url} is redirected with no inbox, form or message request`, async ({
      page,
    }) => {
      const ctx = await setup(page, user);
      await page.goto(url);
      await expect(page).toHaveURL(new RegExp(`${destination}$`));
      expect(ctx.feedback.requests).toHaveLength(0);
      expect(ctx.seen.filter((s) => s.includes(INBOX))).toEqual([]);
    });
  }
}

test("stu06 an unread message count never renders a negative or stale value after a read racing a badge refresh", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.messages = [message(1)];
  ctx.feedback.unread = false;
  await page.goto("/student/inbox");
  await expect(badge(page, 1)).toBeVisible();
  await page.getByRole("button", { name: "Mark as read", exact: true }).click();
  await page.evaluate(() => {
    window.dispatchEvent(new Event("focus"));
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(status(page, "0 unread messages")).toBeVisible();
  await expect(anyBadge(page)).toHaveCount(0);
});

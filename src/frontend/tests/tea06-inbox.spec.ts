import { expect, test, type Page } from "@playwright/test";
import {
  ADMIN,
  STUDENT,
  TEACHER,
  logOutWithConfirmation,
  mockAuthApi,
  signInThroughForm,
} from "./authApi";
import {
  FORM_ID,
  MSG,
  TITLE,
  alert,
  firstAnswer,
  recipientReady,
  status,
} from "./adm02Api";
import {
  COUNT,
  INBOX,
  SENT,
  anyBadge,
  badge,
  message,
  setup,
} from "./stu0506Api";

/**
 * TEA-06: the teacher side of the shared inbox and feedback screens (spec/plan: workflow/specs/TEA-06).
 * Mocked backend only; the shared fixtures are the ones STU-05-06 and ADM-02 use.
 */
const MESSAGES_NETWORK =
  "Could not reach the server. Check your connection and try again.";
const INVALID_ANSWERS =
  "Answer every required question and check that all answers match their question type.";
const teacherNav = (page: Page) =>
  page.getByRole("navigation", { name: "teacher navigation" });

test("TEA-06 AC02 teacher submit with a required answer missing shows the 422 copy, then submits and sees Feedback submitted. Thank you.", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  await page.goto(`/teacher/feedback/${FORM_ID}`);
  await expect(firstAnswer(page)).toBeVisible();
  ctx.feedback.steps.push({
    method: "POST",
    path: "/responses",
    status: 422,
    code: "invalid_feedback_answers",
  });
  await page
    .getByRole("button", { name: "Submit feedback", exact: true })
    .click();
  await expect(alert(page, INVALID_ANSWERS)).toBeVisible();
  await expect(page.getByText("Feedback submitted. Thank you.")).toHaveCount(0);
  // A client-side check may stop the request before the scripted refusal is used.
  ctx.feedback.steps.length = 0;
  await firstAnswer(page).fill("Clear examples help");
  await page
    .getByRole("button", { name: "Submit feedback", exact: true })
    .click();
  await expect(page.getByText("Completed", { exact: true })).toBeVisible();
  await expect(page.getByText("Feedback submitted. Thank you.")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Back to inbox", exact: true }),
  ).toHaveAttribute("href", "/teacher/inbox");
  await expect(
    page.getByRole("button", { name: "Submit feedback", exact: true }),
  ).toHaveCount(0);
});

test("TEA-06 AC04 teacher sees From: Administrator and the sent time on each message and survey requests under Feedback requests", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = [message(1), message(2, "feedback_response")];
  await page.goto("/teacher/inbox");
  await expect(
    page.getByRole("heading", { level: 1, name: "Inbox", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Feedback requests", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Messages", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: TITLE, exact: true }),
  ).toBeVisible();
  for (const n of [1, 2]) {
    const article = page.getByRole("article", {
      name: `Improvement ${n}`,
      exact: true,
    });
    await expect(article).toContainText("From: Administrator");
    await expect(article.locator("time")).toHaveAttribute("datetime", SENT);
  }
  await expect(page.getByText("From: Administrator")).toHaveCount(2);
});

test("TEA-06 AC05 message body with HTML renders as literal text", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  const item = message(1);
  item.subject = "<b>Bold subject</b>";
  item.body = '<img src=x onerror="window.TEA06_XSS=1">\n<script>1</script>';
  ctx.messages = [item];
  await page.goto("/teacher/inbox");
  const article = page.getByRole("article", {
    name: item.subject,
    exact: true,
  });
  await expect(article).toContainText(item.body);
  await expect(article.locator("img, script, b")).toHaveCount(0);
  expect(
    await page.evaluate(() =>
      Object.prototype.hasOwnProperty.call(window, "TEA06_XSS"),
    ),
  ).toBe(false);
});

test("TEA-06 AC06 request title opens /teacher/feedback/{id} by a push and Back returns to a fresh inbox", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  await page.goto("/teacher/inbox");
  await page.getByRole("link", { name: TITLE, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/teacher/feedback/${FORM_ID}$`));
  await expect(
    page.getByRole("heading", { level: 1, name: TITLE, exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Submit feedback", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/\/teacher\/inbox$/);
  await expect(status(page, "Unread requests: 0")).toBeVisible();
  expect(ctx.feedback.of("GET", "/inbox")).toHaveLength(2);
  expect(ctx.of("GET", INBOX)).toHaveLength(2);
});

test("TEA-06 AC07 closed request shows Closed, This form is closed. and no editable controls", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.feedback.form = { ...ctx.feedback.form, state: "closed" };
  await page.goto("/teacher/inbox");
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
  ).toHaveAttribute("href", "/teacher/inbox");
});

test("TEA-06 AC08 new message is Unread and Mark as read makes it Read for the teacher only", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = [message(1)];
  await page.goto("/teacher/inbox");
  const article = page.getByRole("article", {
    name: "Improvement 1",
    exact: true,
  });
  await expect(article).toContainText("Unread");
  await article
    .getByRole("button", { name: "Mark as read", exact: true })
    .click();
  await expect(status(page, "0 unread messages")).toBeVisible();
  await expect(article).not.toContainText("Unread");
  await expect(
    article.getByRole("button", { name: "Mark as read", exact: true }),
  ).toHaveCount(0);
  expect(ctx.of("POST", `${INBOX}/${ctx.messages[0].id}/read`)).toHaveLength(1);
  // The one POST names this delivery; the list is not read again.
  expect(ctx.of("GET", INBOX)).toHaveLength(1);
  await expect(page).toHaveURL(/\/teacher\/inbox$/);
});

test("TEA-06 AC09 after logout and sign-in the Read markers and badge come from the server", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = [message(1)];
  await page.goto("/teacher/inbox");
  await expect(badge(page, 2)).toBeVisible();
  await page.getByRole("link", { name: TITLE, exact: true }).click();
  await page.getByRole("link", { name: "Back to inbox", exact: true }).click();
  await page
    .getByRole("article", { name: "Improvement 1", exact: true })
    .getByRole("button", { name: "Mark as read", exact: true })
    .click();
  await expect(anyBadge(page)).toHaveCount(0);
  await logOutWithConfirmation(page);
  await expect(page).toHaveURL(/\/login/);
  await signInThroughForm(page, TEACHER.email!);
  await page.goto("/teacher/inbox");
  await expect(status(page, "Unread requests: 0")).toBeVisible();
  await expect(status(page, "0 unread messages")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Mark as read", exact: true }),
  ).toHaveCount(0);
  await expect(anyBadge(page)).toHaveCount(0);
});

test("TEA-06 AC10 teacher inbox exposes no email or push control", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = [message(1)];
  await page.goto("/teacher/inbox");
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

test("TEA-06 AC11 badge equals requests plus messages, both section counts kept", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = [message(1), message(2)];
  await page.goto("/teacher/inbox");
  await expect(status(page, "Unread requests: 1")).toBeVisible();
  await expect(status(page, "2 unread messages")).toBeVisible();
  await expect(badge(page, 3)).toBeVisible();
  await expect(
    teacherNav(page)
      .getByRole("link", { name: "Inbox", exact: true })
      .getByRole("status"),
  ).toHaveText("3");
});

test("TEA-06 AC11 badge is absent at zero", async ({ page }) => {
  const ctx = await setup(page, TEACHER);
  ctx.feedback.unread = false;
  await page.goto("/teacher/overview");
  await expect(
    teacherNav(page).getByRole("link", { name: "Inbox", exact: true }),
  ).toBeVisible();
  await expect.poll(() => ctx.of("GET", COUNT).length).toBeGreaterThan(0);
  await expect(anyBadge(page)).toHaveCount(0);
});

test("TEA-06 AC11 badge shows 99+ above 99", async ({ page }) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = Array.from({ length: 100 }, (_, n) => message(n + 1));
  await page.goto("/teacher/overview");
  await expect(badge(page, 101)).toHaveText("99+");
});

test("TEA-06 AC12 badge drops after opening a form and after Mark as read, with exact request counts", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = [message(1)];
  await page.goto("/teacher/inbox");
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
  await page
    .getByRole("article", { name: "Improvement 1", exact: true })
    .getByRole("button", { name: "Mark as read", exact: true })
    .click();
  await expect(status(page, "0 unread messages")).toBeVisible();
  await expect(anyBadge(page)).toHaveCount(0);
  expect(ctx.of("POST", `${INBOX}/${ctx.messages[0].id}/read`)).toHaveLength(1);
  await expect(page).toHaveURL(/\/teacher\/inbox$/);
});

test("TEA-06 AC13 survey list fails: Messages stays, its count and list are kept, and Retry repeats only the survey read", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = [message(1)];
  ctx.feedback.steps.push({
    method: "GET",
    path: "/inbox",
    status: 503,
    code: "feedback_unavailable",
  });
  await page.goto("/teacher/inbox");
  await expect(alert(page, MSG.unavailable)).toBeVisible();
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

test("TEA-06 AC13 message list fails: survey requests stay and the messaging network copy is used", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = [message(1)];
  ctx.fail.push({ path: INBOX, abort: true });
  await page.goto("/teacher/inbox");
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

test("TEA-06 AC13 count endpoint fails: both sections work and the badge shows no error text", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = [message(1)];
  ctx.fail.push({ path: COUNT, status: 503 });
  await page.goto("/teacher/inbox");
  await expect(status(page, "Unread requests: 1")).toBeVisible();
  await expect(status(page, "1 unread messages")).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.getByText(/temporarily unavailable/i)).toHaveCount(0);
});

test("TEA-06 AC14 signed-in /teacher/feedback lands on /teacher/inbox with replace (Back does not return) and shows no Preview only form", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  await page.goto("/teacher/overview");
  await page.goto("/teacher/feedback");
  await expect(page).toHaveURL(/\/teacher\/inbox$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Inbox", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Feedback requests", exact: true }),
  ).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Sample feedback form");
  // The redirect adds no request of its own: the inbox's normal loads only.
  expect(ctx.feedback.of("GET", "/inbox")).toHaveLength(1);
  expect(ctx.of("GET", INBOX)).toHaveLength(1);
  await page.goBack();
  await expect(page).toHaveURL(/\/teacher\/overview$/);
});

test("TEA-06 AC14 /teacher/feedback/{id} still opens the real form", async ({
  page,
}) => {
  await recipientReady(page, "teacher");
  await expect(page).toHaveURL(new RegExp(`/teacher/feedback/${FORM_ID}$`));
  await expect(
    page.getByRole("heading", { level: 1, name: TITLE, exact: true }),
  ).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Sample feedback form");
});

test("TEA-06 AC14 anonymous /teacher/feedback keeps the sample form", async ({
  page,
}) => {
  await mockAuthApi(page, { user: null });
  await page.goto("/teacher/feedback");
  await expect(page).toHaveURL(/\/teacher\/feedback$/);
  await expect(page.locator("body")).toContainText("Sample feedback form");
});

for (const user of [STUDENT, ADMIN]) {
  const destination =
    user.role === "admin" ? "/admin/overview" : "/student/overview";
  for (const url of [
    "/teacher/inbox",
    "/teacher/feedback",
    `/teacher/feedback/${FORM_ID}`,
  ]) {
    test(`TEA-06 AC15 ${user.role} opening ${url} is redirected with no page requests`, async ({
      page,
    }) => {
      const ctx = await setup(page, user);
      await page.goto(url);
      await expect(page).toHaveURL(new RegExp(`${destination}$`));
      expect(ctx.feedback.requests).toHaveLength(0);
      expect(ctx.seen.filter((s) => s.includes(INBOX))).toEqual([]);
      expect(ctx.seen.filter((s) => s.startsWith("POST"))).toEqual([]);
    });
  }
}

test("TEA-06 badge never negative when a read races a refresh", async ({
  page,
}) => {
  const ctx = await setup(page, TEACHER);
  ctx.messages = [message(1)];
  ctx.feedback.unread = false;
  await page.goto("/teacher/inbox");
  await expect(badge(page, 1)).toBeVisible();
  await page.getByRole("button", { name: "Mark as read", exact: true }).click();
  await page.evaluate(() => {
    window.dispatchEvent(new Event("focus"));
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(status(page, "0 unread messages")).toBeVisible();
  await expect(anyBadge(page)).toHaveCount(0);
});

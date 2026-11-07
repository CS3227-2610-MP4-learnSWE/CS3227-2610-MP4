import { test, expect, type Page } from "@playwright/test";
import {
  NOTICE,
  PASSWORD,
  STUDENT,
  TEACHER,
  emailField,
  exploreDemoLink,
  expectNoSecretsInBrowser,
  mockAuthApi,
  passwordField,
  signInThroughForm,
} from "./authApi";
import { companionOk, mockCompanionApi } from "./companionApi";
import { signedInStudy } from "./lessonsApi";
import { mockPracticeApi, SET_ID } from "./practiceApi";

/**
 * SHR-01 AC23 (CSRF header, no X-Student-Id, no secrets in browser storage, CSRF token only in
 * memory) and AC22/AC25 (401 handling: authenticated versus demo mode). These cover client.ts,
 * AuthContext and the sign-in notice through the browser; the project has no unit-test runner and
 * the plan adds no dependency.
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const R1 = "A single, focused responsibility";
const R2 = "To catch regressions when code changes";

async function answerAll(page: Page) {
  await page.getByRole("radio", { name: R1 }).check();
  await page.getByRole("radio", { name: R2 }).check();
  await page.getByRole("radio", { name: "3", exact: true }).check();
}

// ---------------------------------------------------------------- AC23 storage
test("shr01 AC23 signing in and practising leaves no password, token or session id in browser storage or cookies", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  const practice = await mockPracticeApi(page, { auth });
  await signInThroughForm(page, STUDENT.email!);
  await expect(page).toHaveURL(/\/student\/overview$/);
  await page.goto(`/student/practice/${SET_ID}`);
  await answerAll(page);
  await page.getByRole("button", { name: "Submit practice set" }).click();
  await expect(page.getByText("Correct answer:").first()).toBeVisible();
  expect(practice.count("results")).toBe(1);
  await expectNoSecretsInBrowser(page, [PASSWORD, auth.csrf, "csrf-token"]);
});

test("shr01 AC23 the session token is not readable by scripts (document.cookie stays empty)", async ({
  page,
  context,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  await signInThroughForm(page, STUDENT.email!);
  await expect(page).toHaveURL(/\/student\/overview$/);
  expect(await page.evaluate(() => document.cookie)).toBe("");
  expect((await context.cookies()).map((c) => c.name)).not.toContain(
    "learnswe_session",
  );
  expect(auth.count("login")).toBe(1);
});

test("shr01 AC23 the CSRF token lives in memory only and is re-fetched from /api/auth/me after a reload", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  const practice = await mockPracticeApi(page, { auth });
  await signInThroughForm(page, STUDENT.email!);
  await expect(page).toHaveURL(/\/student\/overview$/);
  const before = auth.csrf;
  auth.csrf = "csrf-token-after-reload";
  expect(auth.csrf).not.toBe(before);
  await page.goto(`/student/practice/${SET_ID}`); // full page load: all in-memory state is gone
  await answerAll(page);
  await page.getByRole("button", { name: "Submit practice set" }).click();
  await expect(page.getByText("Correct answer:").first()).toBeVisible();
  expect(auth.count("me")).toBeGreaterThanOrEqual(1);
  const unsafe = practice
    .of("start")
    .concat(practice.of("save"), practice.of("submit"));
  expect(unsafe).toHaveLength(3);
  for (const r of unsafe)
    expect(r.headers["x-csrf-token"]).toBe("csrf-token-after-reload");
  const stored = await page.evaluate(() =>
    JSON.stringify([localStorage, sessionStorage]),
  );
  expect(stored).not.toContain("csrf");
});

test("shr01 AC23 state-changing companion calls carry the CSRF token and no X-Student-Id", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  const companion = await mockCompanionApi(
    page,
    [companionOk("A hint.")],
    auth,
  );
  await page.goto("/student/overview");
  await page.getByRole("button", { name: "Open study companion" }).click();
  await page.getByLabel("Message your study companion").fill("hello");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect.poll(() => companion.count).toBe(1);
  expect(companion.last.headers["x-csrf-token"]).toBe(auth.csrf);
  expect(companion.last.headers["x-student-id"]).toBeUndefined();
  await expect(page.getByRole("dialog")).toContainText("A hint.");
});

test("shr01 AC23 API calls send the browser's cookies (same-origin credentials)", async ({
  page,
  context,
  baseURL,
}) => {
  await context.addCookies([{ name: "probe", value: "1", url: baseURL! }]);
  await mockAuthApi(page, { user: STUDENT });
  let cookieHeader = "";
  await mockPracticeApi(page);
  // Registered after the mock, so it runs first and then falls back to it.
  await page.route("**/api/practice-sets/*", async (route) => {
    cookieHeader = (await route.request().allHeaders())["cookie"] ?? "";
    await route.fallback();
  });
  await page.goto(`/student/practice/${SET_ID}`);
  await expect(page.getByRole("radio", { name: R1 })).toBeVisible();
  expect(cookieHeader).toContain("probe=1");
});

// ---------------------------------------------------------------- 401 while authenticated
test("shr01 AC22 a 401 on practice while signed in clears the session and returns to /login", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  await mockPracticeApi(page, { auth });
  await page.goto(`/student/practice/${SET_ID}`);
  await answerAll(page);
  auth.expire(); // the session expired or was revoked on the server
  await page.getByRole("button", { name: "Submit practice set" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText("Sam Student")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /log out/i })).toHaveCount(0);
  // The client state was cleared: the protected area no longer renders as signed in.
  await (await exploreDemoLink(page, "student")).click();
  await expect(page.getByText("Demo (not signed in)").first()).toBeVisible();
  await expect(page.getByText("Sam Student")).toHaveCount(0);
});

test("shr01 AC22 a 401 on the companion while signed in returns to /login", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  await mockCompanionApi(page, [], auth);
  await page.goto("/student/overview");
  await page.getByRole("button", { name: "Open study companion" }).click();
  await page.getByLabel("Message your study companion").fill("hello");
  auth.expire();
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("shr01 AC22 a 401 on the first practice request while signed in returns to /login", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  await mockPracticeApi(page, { auth });
  auth.expire();
  // me() is answered before expiry only if it ran first; script it as still valid, then expire.
  auth.script("me", { json: { user: STUDENT, csrf_token: auth.csrf } });
  await page.goto(`/student/practice/${SET_ID}`);
  await expect(page).toHaveURL(/\/login$/);
});

test("shr01 AC22 a wrong password (401 invalid_credentials) is not treated as an expired session", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await emailField(page).fill(STUDENT.email!);
  await passwordField(page).fill("definitely wrong password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText(NOTICE)).toHaveCount(0);
  expect(auth.count("me")).toBe(1); // no refetch loop
});

// ---------------------------------------------------------------- 401 in demo mode
test("shr01 AC25 demo mode: a 401 on practice shows the sign-in notice and does not redirect", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  await mockPracticeApi(page, { auth });
  await page.goto(`/student/practice/${SET_ID}`);
  await expect(page.getByText(NOTICE).first()).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/student/practice/${SET_ID}$`));
  await expect(page.locator('a[href="/login"]').first()).toBeVisible();
  await expect(page.getByText("Demo (not signed in)").first()).toBeVisible();
  await expect(page.getByText("Correct answer:")).toHaveCount(0);
});

test("shr01 AC25 demo mode: a 401 on the companion shows the sign-in notice and does not redirect", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  await mockCompanionApi(page, [], auth);
  await page.goto("/student/overview");
  await page.getByRole("button", { name: "Open study companion" }).click();
  await page.getByLabel("Message your study companion").fill("hello");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByText(NOTICE).first()).toBeVisible();
  await expect(page).toHaveURL(/\/student\/overview$/);
});

test("shr01 AC25 demo mode: the sample screens still work without any session", async ({
  page,
}) => {
  // STU-01: the built-in sample lessons are gone; the Overview is still a sample screen in demo mode.
  await signedInStudy(page, { user: null });
  await page.goto("/student/overview");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page).toHaveURL(/\/student\/overview$/);
  await expect(page.getByText(NOTICE)).toHaveCount(0);
});

// Teacher transport now participates in shared authentication (TEA-03).
for (const [label, user] of [
  ["a signed-in teacher", TEACHER],
  ["a demo visitor", null],
] as const) {
  test(`tea03 teacher transport handles session expiry (${label})`, async ({
    page,
  }) => {
    await mockAuthApi(page, { user });
    const teacherCalls: Record<string, string>[] = [];
    await page.route("**/api/teacher/**", async (route) => {
      teacherCalls.push(route.request().headers());
      await route.fulfill({
        status: 401,
        json: { detail: { code: "unauthenticated", message: "no" } },
      });
    });
    await page.goto("/teacher/materials");
    if (user) {
      await expect(page).toHaveURL(/\/login$/);
      expect(teacherCalls.length).toBeGreaterThan(0);
    } else {
      await expect(page.getByRole("alert")).toContainText(
        "Sign in to manage teacher materials and drafts.",
      );
      await expect(page).toHaveURL(/\/teacher\/materials$/);
      expect(teacherCalls).toHaveLength(0);
    }
    for (const headers of teacherCalls) {
      expect(headers["x-student-id"]).toBeUndefined();
      expect(headers["x-demo-user-id"]).toBeUndefined();
    }
  });
}

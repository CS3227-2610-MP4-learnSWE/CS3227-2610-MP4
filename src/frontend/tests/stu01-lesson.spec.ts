import { test, expect, type Page } from "@playwright/test";
import { ADMIN, TEACHER } from "./authApi";
import {
  COURSE_SE,
  L_GENERAL,
  L_TESTING,
  LESSONS,
  MSG,
  customLesson,
  signedInStudy,
  studyError,
  type Reply,
} from "./lessonsApi";

/**
 * STU-01 AC3, AC4, AC12, AC13, AC14: the lesson page and the completion button.
 * Copy and roles come from workflow/specs/STU-01/spec.md "UI states and copy" and plan.md "UI contract".
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const markComplete = (page: Page) =>
  page.getByRole("button", { name: "Mark as complete", exact: true });
const markIncomplete = (page: Page) =>
  page.getByRole("button", { name: "Mark as incomplete", exact: true });
const saving = (page: Page) =>
  page.getByRole("button", { name: "Saving…", exact: true });
const alertWith = (page: Page, text: string) =>
  page.getByRole("alert").filter({ hasText: text });
const notFound = (page: Page) =>
  page.getByRole("heading", { level: 3, name: "Lesson not found" });

async function openLesson(page: Page, id = L_TESTING) {
  await page.goto(`/student/materials/${id}`);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
}

// ---------------------------------------------------------------- reading
test("stu01 AC1 lesson page shows back link, title, eyebrow, content region and the actions", async ({
  page,
}) => {
  await signedInStudy(page);
  await openLesson(page);
  await expect(
    page.getByRole("heading", { level: 1, name: "Unit testing basics" }),
  ).toBeVisible();
  await expect(
    page.getByText(/^testing · software engineering$/i),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "All study materials" }),
  ).toHaveAttribute("href", `/student/materials?course=${COURSE_SE}`);
  const content = page.getByRole("region", { name: "Lesson content" });
  await expect(content).toContainText("Write small tests first.");
  await expect(markComplete(page)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Try the practice set" }),
  ).toHaveAttribute("href", "/student/practice");
  await expect(
    page.getByRole("button", { name: "Ask your companion" }),
  ).toBeVisible();
});

test("stu01 AC1 a lesson without a topic shows the General eyebrow", async ({
  page,
}) => {
  await signedInStudy(page);
  await openLesson(page, L_GENERAL);
  await expect(
    page.getByText(/^general · software engineering$/i),
  ).toBeVisible();
});

test("stu01 AC12 content keeps its line breaks and is rendered as plain text", async ({
  page,
}) => {
  await signedInStudy(page);
  await openLesson(page, L_GENERAL);
  const content = page.getByRole("region", { name: "Lesson content" });
  await expect(content).toHaveCSS("white-space", "pre-wrap");
  expect(await content.evaluate((el) => el.textContent)).toContain(
    "Name things well.\n\nKeep functions short.",
  );
});

test("stu01 AC12 HTML and script text in title and content is displayed literally and does not run", async ({
  page,
}) => {
  const id = "aaaaaaaa-0000-4000-8000-000000000002";
  const evil = customLesson({
    id,
    title: "<b>Bold?</b> & <img src=x onerror=window.__pwned=1>",
    content:
      '<script>window.__pwned=2</script>\n<img src=x onerror=window.__pwned=3>\n<a href="javascript:window.__pwned=4">link</a> https://example.com/auto',
  });
  await signedInStudy(page, { lessons: [...LESSONS, evil] });
  let dialogs = 0;
  page.on("dialog", async (d) => {
    dialogs += 1;
    await d.dismiss();
  });
  await page.goto(`/student/materials/${id}`);
  const content = page.getByRole("region", { name: "Lesson content" });
  await expect(content).toContainText("<script>window.__pwned=2</script>");
  await expect(content).toContainText("<img src=x onerror=window.__pwned=3>");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "<b>Bold?</b> & <img src=x onerror=window.__pwned=1>",
  );
  await expect(content.locator("img, script, a, b")).toHaveCount(0);
  await expect(page.locator('img[src="x"]')).toHaveCount(0);
  expect(
    await page.evaluate(
      () => (window as unknown as { __pwned?: number }).__pwned,
    ),
  ).toBeUndefined();
  expect(dialogs).toBe(0);
});

test("stu01 AC8 the stored completed state is shown on load", async ({
  page,
}) => {
  await signedInStudy(page, { done: [L_TESTING] });
  await openLesson(page);
  await expect(markIncomplete(page)).toBeVisible();
  await expect(markComplete(page)).toHaveCount(0);
});

test("stu01 AC13 loading shows the status text before the lesson", async ({
  page,
}) => {
  const { api } = await signedInStudy(page, {
    replies: { lesson: [{ hang: true }] },
  });
  await page.goto(`/student/materials/${L_TESTING}`);
  await expect(
    page.getByRole("status").filter({ hasText: MSG.loadingLesson }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "All study materials" }),
  ).toHaveAttribute("href", "/student/materials");
  await expect(
    page.getByRole("region", { name: "Lesson content" }),
  ).toHaveCount(0);
  api.release();
});

test("stu01 AC13 the lesson page has no outline sidebar and no sample content", async ({
  page,
}) => {
  await signedInStudy(page);
  await openLesson(page);
  const body = await page.locator("body").innerText();
  for (const sample of ["Easy to change", "Make it easy to change"])
    expect(body).not.toContain(sample);
});

// ---------------------------------------------------------------- AC3 / AC4 completion
test("stu01 AC3 mark complete then incomplete: request bodies, labels, status messages", async ({
  page,
}) => {
  const { api, auth } = await signedInStudy(page);
  await openLesson(page);
  await markComplete(page).click();
  await expect(markIncomplete(page)).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: "Marked as complete." }),
  ).toBeVisible();
  expect(api.of("put")).toHaveLength(1);
  expect(api.last.method).toBe("PUT");
  expect(api.last.path).toBe(`/api/study/lessons/${L_TESTING}/completion`);
  expect(api.last.body).toEqual({ completed: true });
  expect(api.last.headers["x-csrf-token"]).toBe(auth.csrf);
  await markIncomplete(page).click();
  await expect(markComplete(page)).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: "Marked as incomplete." }),
  ).toBeVisible();
  expect(api.of("put").map((r) => r.body)).toEqual([
    { completed: true },
    { completed: false },
  ]);
  expect(api.isDone(L_TESTING)).toBe(false);
});

test("stu01 AC4 the status persists across a reload and a new sign-in (read back from the server)", async ({
  page,
}) => {
  const { api, auth } = await signedInStudy(page);
  await openLesson(page);
  await markComplete(page).click();
  await expect(markIncomplete(page)).toBeVisible();
  await page.reload();
  await expect(markIncomplete(page)).toBeVisible();
  expect(api.isDone(L_TESTING)).toBe(true);
  auth.expire();
  await page.goto("/login");
  await page
    .getByLabel(/^e-?mail( address)?\s*\*?$/i)
    .fill("sam.student@example.com");
  await page
    .getByLabel(/^password\s*\*?$/i)
    .fill("correct horse battery staple 42");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.goto(`/student/materials/${L_TESTING}`);
  await expect(markIncomplete(page)).toBeVisible();
});

test("stu01 AC13 the button is disabled and reads Saving… until the server confirms; the label does not flip early", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openLesson(page);
  api.script("put", { hang: true });
  await markComplete(page).click();
  await expect(saving(page)).toBeDisabled();
  await expect(markIncomplete(page)).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Lesson content" }),
  ).toContainText("Write small tests first.");
  await expect(
    page.getByRole("heading", { level: 1, name: "Unit testing basics" }),
  ).toBeVisible();
  expect(api.isDone(L_TESTING)).toBe(false);
  api.release();
});

test("stu01 AC9 a double click sends one PUT", async ({ page }) => {
  const { api } = await signedInStudy(page);
  await openLesson(page);
  api.script("put", { delayMs: 400 });
  await markComplete(page).dblclick();
  await expect(markIncomplete(page)).toBeVisible();
  expect(api.count("put")).toBe(1);
});

test("stu01 AC9 the request states the target from the last confirmed state, not a toggle", async ({
  page,
}) => {
  const { api } = await signedInStudy(page, { done: [L_TESTING] });
  await openLesson(page);
  await markIncomplete(page).click();
  await expect(markComplete(page)).toBeVisible();
  expect(api.last.body).toEqual({ completed: false });
});

// ---------------------------------------------------------------- failed saves
const saveFailures: [string, Reply, string][] = [
  ["unreachable", { abort: true }, MSG.saveOffline],
  [
    "503 service_unavailable",
    studyError(503, "service_unavailable"),
    MSG.saveFailed,
  ],
  ["500", studyError(500, "internal_error"), MSG.saveFailed],
  ["403 csrf_failed", studyError(403, "csrf_failed"), MSG.saveFailed],
];

for (const [label, reply, message] of saveFailures) {
  test(`stu01 AC13 failed save (${label}): exact message, old label, enabled button, lesson text kept, retry works`, async ({
    page,
  }) => {
    const { api } = await signedInStudy(page, { replies: { put: [reply] } });
    await openLesson(page);
    await markComplete(page).click();
    await expect(alertWith(page, message)).toBeVisible();
    await expect(markComplete(page)).toBeEnabled();
    await expect(markIncomplete(page)).toHaveCount(0);
    await expect(
      page.getByRole("region", { name: "Lesson content" }),
    ).toContainText("Write small tests first.");
    await expect(
      page.getByRole("status").filter({ hasText: "Marked as" }),
    ).toHaveCount(0);
    const text = await page.locator("body").innerText();
    expect(text).not.toMatch(/\b(503|500|csrf_failed|Server says)\b/);
    expect(api.count("put")).toBe(1); // no automatic retry
    await markComplete(page).click();
    await expect(markIncomplete(page)).toBeVisible();
    await expect(
      page.getByRole("alert").filter({ hasText: message }),
    ).toHaveCount(0);
    expect(api.count("put")).toBe(2);
    expect(api.isDone(L_TESTING)).toBe(true);
  });
}

test("stu01 AC13 a save that times out after 10 seconds says the progress was not saved", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openLesson(page);
  await page.clock.install();
  api.script("put", { hang: true });
  await markComplete(page).click();
  await expect.poll(() => api.count("put")).toBe(1);
  await page.clock.fastForward(9_000);
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.clock.fastForward(2_000);
  await expect(alertWith(page, MSG.saveOffline)).toBeVisible();
  await expect(markComplete(page)).toBeEnabled();
  api.release();
});

test("stu01 AC13 a save answered 404 (lesson withdrawn meanwhile) shows Lesson not found", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openLesson(page);
  api.script("put", studyError(404, "not_found", "Lesson not found."));
  await markComplete(page).click();
  await expect(notFound(page)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Return to materials" }),
  ).toHaveAttribute("href", "/student/materials");
});

test("stu01 AC14 a 401 on save while signed in goes to /login", async ({
  page,
}) => {
  const { auth } = await signedInStudy(page);
  await openLesson(page);
  auth.expire();
  await markComplete(page).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText("Unit testing basics")).toHaveCount(0);
});

test("stu01 AC14 demo mode: a 401 on the lesson shows the sign-in notice", async ({
  page,
}) => {
  await signedInStudy(page, { user: null });
  await page.goto(`/student/materials/${L_TESTING}`);
  await expect(page.getByText(MSG.signIn)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Go to sign in" }),
  ).toHaveAttribute("href", "/login");
  await expect(
    page.getByRole("region", { name: "Lesson content" }),
  ).toHaveCount(0);
});

// ---------------------------------------------------------------- failed loads
const loadFailures: [string, Reply, string][] = [
  ["unreachable", { abort: true }, MSG.offline],
  ["503", studyError(503, "service_unavailable"), MSG.unavailable],
  ["500", studyError(500, "internal_error"), MSG.unavailable],
  ["wrong shape", { json: { id: L_TESTING } }, MSG.badShape],
];

for (const [label, reply, message] of loadFailures) {
  test(`stu01 AC13 lesson load (${label}): exact message and Try again repeats only the lesson request`, async ({
    page,
  }) => {
    const { api } = await signedInStudy(page, { replies: { lesson: [reply] } });
    await page.goto(`/student/materials/${L_TESTING}`);
    await expect(alertWith(page, message)).toBeVisible();
    await expect(
      page.getByRole("link", { name: "All study materials" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Unit testing basics" }),
    ).toBeVisible();
    expect(api.count("lesson")).toBe(2);
    expect(api.count("courses")).toBe(0);
    expect(api.count("lessons")).toBe(0);
  });
}

for (const [label, user, area] of [
  ["teacher", TEACHER, /\/teacher\//],
  ["admin", ADMIN, /\/admin\//],
] as const) {
  test(`stu01 AC6 a ${label} who opens a lesson URL is redirected by the role guard and no study request is sent`, async ({
    page,
  }) => {
    const { api } = await signedInStudy(page, { user });
    await page.goto(`/student/materials/${L_TESTING}`);
    await expect(page).toHaveURL(area);
    await expect(alertWith(page, MSG.forbidden)).toHaveCount(0);
    expect(api.requests).toHaveLength(0);
  });
}

test("stu01 AC13 lesson load 403 (role changed after sign-in) shows the access message and no retry", async ({
  page,
}) => {
  const { api } = await signedInStudy(page, {
    replies: { lesson: [studyError(403, "forbidden")] },
  });
  await page.goto(`/student/materials/${L_TESTING}`);
  await expect(alertWith(page, MSG.forbidden)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  expect(api.count("lesson")).toBe(1);
});

test("stu01 AC13 lesson load times out after 10 seconds", async ({ page }) => {
  const { api } = await signedInStudy(page, {
    replies: { lesson: [{ hang: true }] },
  });
  await page.clock.install();
  await page.goto(`/student/materials/${L_TESTING}`);
  await expect.poll(() => api.count("lesson")).toBe(1);
  await page.clock.fastForward(11_000);
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  api.release();
});

test("stu01 AC13 an unknown, withdrawn or foreign lesson (404) shows the Lesson not found panel", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await page.goto("/student/materials/99999999-9999-4999-8999-999999999999");
  await expect(notFound(page)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Return to materials" }),
  ).toHaveAttribute("href", "/student/materials");
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  api.withdrawn.add(L_TESTING);
  await page.goto(`/student/materials/${L_TESTING}`);
  await expect(notFound(page)).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("stu01 AC13 a direct URL that is not a uuid shows the Lesson not found panel (server answers 422)", async ({
  page,
}) => {
  await signedInStudy(page);
  await page.goto("/student/materials/not-a-uuid");
  await expect(notFound(page)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Return to materials" }),
  ).toBeVisible();
  await page.goto("/student/materials/clean-code");
  await expect(notFound(page)).toBeVisible();
});

test("stu01 AC13 the lesson id in the path is URL-encoded when requested", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await page.goto("/student/materials/..%2F..%2Fcourses");
  await expect(notFound(page)).toBeVisible();
  for (const r of api.requests)
    expect(r.path).toMatch(/^\/api\/study\/(courses|lessons)/);
  expect(api.requests.some((r) => r.path.includes("/../"))).toBe(false);
});

// ---------------------------------------------------------------- actions and companion
test("stu01 AC13 Ask your companion opens the companion and the page label is Study materials", async ({
  page,
}) => {
  await signedInStudy(page);
  await openLesson(page);
  await page.getByRole("button", { name: "Ask your companion" }).click();
  const chat = page.getByRole("dialog", { name: "Your study companion" });
  await expect(chat).toBeVisible();
  await expect(chat).toContainText("Current page: Study materials");
  await expect(chat).not.toContainText("Unit testing basics");
});

test("stu01 AC13 Try the practice set goes to the practice page", async ({
  page,
}) => {
  await signedInStudy(page);
  await openLesson(page);
  await page.getByRole("link", { name: "Try the practice set" }).click();
  await expect(page).toHaveURL(/\/student\/practice$/);
});

test("stu01 AC13 the back link returns to the list of the lesson's course", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openLesson(page);
  await page.getByRole("link", { name: "All study materials" }).click();
  await expect(page).toHaveURL(
    new RegExp(`/student/materials\\?course=${COURSE_SE}$`),
  );
  await expect(page.getByRole("combobox", { name: "Course" })).toHaveValue(
    COURSE_SE,
  );
  expect(api.count("courses")).toBe(1);
});

// ---------------------------------------------------------------- layout
for (const theme of ["light", "dark"] as const) {
  for (const width of [390, 1440]) {
    test(`stu01 AC13 lesson page fits ${width}px wide in the ${theme} theme without horizontal overflow`, async ({
      page,
    }) => {
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 900 });
      await signedInStudy(page);
      await openLesson(page);
      const m = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        width: innerWidth,
      }));
      expect(m.scroll).toBeLessThanOrEqual(m.width);
      await expect(markComplete(page)).toBeVisible();
    });
  }
}

test("stu01 AC13 the completion button is reachable and works by keyboard", async ({
  page,
}) => {
  await signedInStudy(page);
  await openLesson(page);
  await markComplete(page).focus();
  await expect(markComplete(page)).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(markIncomplete(page)).toBeVisible();
});

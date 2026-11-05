import { test, expect, type Page } from "@playwright/test";
import { PASSWORD } from "./authApi";
import {
  COURSES,
  COURSE_SE,
  L_DESIGN,
  L_GENERAL,
  L_TESTING,
  signedInStudy,
} from "./lessonsApi";

/**
 * STU-01 AC4, AC10, AC14 (SHR-05): a GET still in flight must never be reused across page loads,
 * logouts and logins. Each test holds a GET slow with a stale or foreign body; the correct app
 * ignores that answer and shows data from a request sent after the change.
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const SLOW = 6000;
const B = {
  id: "u-bbbb",
  email: "bea.b@example.com",
  display_name: "Bea B",
  role: "student" as const,
};
const A_COURSES = {
  courses: [
    {
      id: COURSES[0].id,
      title: "A private course",
      lesson_count: 9,
      completed_count: 7,
    },
  ],
  totals: { lesson_count: 9, completed_count: 7 },
};

async function logoutAndLoginAsB(
  page: Page,
  auth: Awaited<ReturnType<typeof signedInStudy>>["auth"],
) {
  auth.accounts.set(B.email, { password: PASSWORD, user: B });
  await page.getByRole("button", { name: "Log out" }).click();
  await page.waitForURL("**/login");
  await page.getByLabel(/email/i).fill(B.email);
  await page
    .getByLabel(/password/i)
    .first()
    .fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("**/student/**");
}

test("stu01 AC14 SHR-05 Overview: student B never sees student A's in-flight courses answer", async ({
  page,
}) => {
  const { auth, api } = await signedInStudy(page);
  api.script("courses", { json: A_COURSES, delayMs: SLOW });
  await page.goto("/student/overview");
  await expect.poll(() => api.count("courses")).toBe(1);
  await logoutAndLoginAsB(page, auth);
  await expect(page.getByText("0 of 4 lessons", { exact: true })).toBeVisible({
    timeout: 9000,
  });
  await page.waitForTimeout(SLOW + 1000);
  await expect(page.getByText("7 of 9 lessons")).toHaveCount(0);
  await expect(page.getByText("0 of 4 lessons", { exact: true })).toBeVisible();
  expect(api.count("courses")).toBeGreaterThanOrEqual(2);
});

test("stu01 AC14 SHR-05 Materials: student B never sees student A's in-flight course titles", async ({
  page,
}) => {
  const { auth, api } = await signedInStudy(page);
  api.script("courses", { json: A_COURSES, delayMs: SLOW });
  await page.goto("/student/materials");
  await expect.poll(() => api.count("courses")).toBe(1);
  await logoutAndLoginAsB(page, auth);
  await page
    .getByRole("link", { name: "Study materials", exact: true })
    .click();
  const options = page
    .getByRole("combobox", { name: "Course" })
    .locator("option");
  await expect(options).toHaveText(["Algorithms", "Software Engineering"], {
    timeout: 9000,
  });
  await page.waitForTimeout(SLOW + 1000);
  await expect(options).toHaveText(["Algorithms", "Software Engineering"]);
  await expect(page.getByText("A private course")).toHaveCount(0);
  expect(api.count("courses")).toBeGreaterThanOrEqual(2);
});

const lessonRow = (id: string, title: string) => ({
  id,
  title,
  excerpt: "x",
  completed: false,
});
const STALE_LIST = {
  course: { id: COURSE_SE, title: "Software Engineering" },
  topics: [
    {
      id: "77777777-7777-4777-8777-777777777777",
      name: "Design",
      lessons: [lessonRow(L_DESIGN, "Design for change")],
    },
    {
      id: "33333333-3333-4333-8333-333333333333",
      name: "Testing",
      lessons: [lessonRow(L_TESTING, "Unit testing basics")],
    },
    {
      id: null,
      name: "General",
      lessons: [lessonRow(L_GENERAL, "Clean code habits")],
    },
  ],
};

test("stu01 AC4 AC10 Back/Forward: a slow list request from before the completion is not reused", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await page.goto(`/student/materials/${L_TESTING}`);
  const complete = page.getByRole("button", {
    name: "Mark as complete",
    exact: true,
  });
  await expect(complete).toBeVisible();
  api.script("lessons", { json: STALE_LIST, delayMs: SLOW });
  await page.getByRole("link", { name: "All study materials" }).click();
  await expect(page.getByText("Loading study materials…")).toBeVisible();
  await page.goBack();
  await complete.click();
  await expect(page.getByText("Marked as complete.")).toBeVisible();
  expect(api.isDone(L_TESTING)).toBe(true);
  const putAt = api.requests.findIndex((r) => r.step === "put");
  await page.goForward();
  await expect(page.getByText("1 of 3 lessons complete")).toBeVisible({
    timeout: 9000,
  });
  await expect(page.getByText("Complete", { exact: true })).toBeVisible();
  await page.waitForTimeout(SLOW + 1000);
  await expect(page.getByText("1 of 3 lessons complete")).toBeVisible();
  const after = api.requests
    .slice(putAt + 1)
    .filter((r) => r.step === "lessons");
  expect(after.length).toBeGreaterThanOrEqual(1);
});

test("stu01 AC4 AC10 Back/Forward: a slow Overview courses request from before the completion is not reused", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await page.goto(`/student/materials/${L_TESTING}`);
  const complete = page.getByRole("button", {
    name: "Mark as complete",
    exact: true,
  });
  await expect(complete).toBeVisible();
  api.script("courses", {
    json: {
      courses: COURSES.map((c) => ({
        id: c.id,
        title: c.title,
        lesson_count: c.id === COURSE_SE ? 3 : 1,
        completed_count: 0,
      })),
      totals: { lesson_count: 4, completed_count: 0 },
    },
    delayMs: SLOW,
  });
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect.poll(() => api.count("courses")).toBe(1);
  await page.goBack();
  await complete.click();
  await expect(page.getByText("Marked as complete.")).toBeVisible();
  const putAt = api.requests.findIndex((r) => r.step === "put");
  await page.goForward();
  await expect(page.getByText("1 of 4 lessons", { exact: true })).toBeVisible({
    timeout: 9000,
  });
  await expect(page.getByText("1 / 4", { exact: true })).toBeVisible();
  await page.waitForTimeout(SLOW + 1000);
  await expect(page.getByText("1 of 4 lessons", { exact: true })).toBeVisible();
  const after = api.requests
    .slice(putAt + 1)
    .filter((r) => r.step === "courses");
  expect(after.length).toBeGreaterThanOrEqual(1);
});

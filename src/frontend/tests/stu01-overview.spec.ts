import { test, expect } from "@playwright/test";
import {
  L_DESIGN,
  L_TESTING,
  MSG,
  signedInStudy,
  studyError,
  type Reply,
} from "./lessonsApi";

/**
 * STU-01 AC4, AC10, AC13, AC14 on the student Overview: the "Lessons completed" stat reads the
 * totals of GET /api/study/courses. The fixture has 4 published lessons over 2 courses.
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const UNAVAILABLE = "Unavailable. Open Study materials to try again.";

test("stu01 AC10 Overview shows Lessons completed N / M with the detail N of M lessons across all courses", async ({
  page,
}) => {
  const { api } = await signedInStudy(page, { done: [L_TESTING, L_DESIGN] });
  await page.goto("/student/overview");
  await expect(
    page.getByText("Lessons completed", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("2 / 4", { exact: true })).toBeVisible();
  await expect(page.getByText("2 of 4 lessons", { exact: true })).toBeVisible();
  expect(api.count("courses")).toBe(1);
  expect(api.count("lessons")).toBe(0);
  expect(api.count("lesson")).toBe(0);
});

test("stu01 AC10 the stat uses the totals field of the server, not a client sum", async ({
  page,
}) => {
  await signedInStudy(page, {
    replies: {
      courses: [
        {
          json: {
            courses: [
              {
                id: "11111111-1111-4111-8111-111111111111",
                title: "A",
                lesson_count: 3,
                completed_count: 1,
              },
            ],
            totals: { lesson_count: 7, completed_count: 5 },
          },
        },
      ],
    },
  });
  await page.goto("/student/overview");
  await expect(page.getByText("5 / 7", { exact: true })).toBeVisible();
  await expect(page.getByText("5 of 7 lessons", { exact: true })).toBeVisible();
});

test("stu01 AC13 with no courses the stat reads 0 / 0 and 0 of 0 lessons", async ({
  page,
}) => {
  await signedInStudy(page, { courses: [] });
  await page.goto("/student/overview");
  await expect(page.getByText("0 / 0", { exact: true })).toBeVisible();
  await expect(page.getByText("0 of 0 lessons", { exact: true })).toBeVisible();
});

test("stu01 AC13 while loading the value is … and the detail is Loading…", async ({
  page,
}) => {
  const { api } = await signedInStudy(page, {
    replies: { courses: [{ hang: true }] },
  });
  await page.goto("/student/overview");
  await expect(
    page.getByText("Lessons completed", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("…", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Loading…", { exact: true })).toBeVisible();
  api.release();
});

const failures: [string, Reply][] = [
  ["unreachable", { abort: true }],
  ["503", studyError(503, "service_unavailable")],
  ["500", studyError(500, "internal_error")],
  ["wrong shape", { json: { courses: 1 } }],
  ["403", studyError(403, "forbidden")],
];
for (const [label, reply] of failures) {
  test(`stu01 AC13 Overview stat on failure (${label}): – and the Unavailable detail; the rest of the page is unaffected`, async ({
    page,
  }) => {
    await signedInStudy(page, { replies: { courses: [reply] } });
    await page.goto("/student/overview");
    await expect(page.getByText("–", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(UNAVAILABLE, { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(
      page.getByText("Lessons completed", { exact: true }),
    ).toBeVisible();
    const text = await page.locator("body").innerText();
    expect(text).not.toMatch(/\b(503|500|403|Server says)\b/);
  });
}

test("stu01 AC13 Overview stat times out after 10 seconds with the Unavailable detail", async ({
  page,
}) => {
  const { api } = await signedInStudy(page, {
    replies: { courses: [{ hang: true }] },
  });
  await page.clock.install();
  await page.goto("/student/overview");
  await expect.poll(() => api.count("courses")).toBe(1);
  await page.clock.fastForward(11_000);
  await expect(page.getByText(UNAVAILABLE, { exact: true })).toBeVisible();
  api.release();
});

test("stu01 AC14 Overview in demo mode: value – and the sign in detail, no redirect", async ({
  page,
}) => {
  await signedInStudy(page, { user: null });
  await page.goto("/student/overview");
  await expect(page.getByText("–", { exact: true }).first()).toBeVisible();
  await expect(
    page.getByText("Sign in to see your progress", { exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/student\/overview$/);
});

test("stu01 AC14 Overview while signed in: a 401 goes to /login", async ({
  page,
}) => {
  const { auth, api } = await signedInStudy(page);
  auth.script("me", { json: { user: auth.user, csrf_token: auth.csrf } });
  auth.expire();
  await page.goto("/student/overview");
  await expect(page).toHaveURL(/\/login$/);
  expect(api.count("courses")).toBeLessThanOrEqual(1);
  await expect(page.getByText("Lessons completed")).toHaveCount(0);
});

test("stu01 AC4 completing a lesson updates the Overview total after navigation and survives a reload", async ({
  page,
}) => {
  await signedInStudy(page);
  await page.goto(`/student/materials/${L_TESTING}`);
  await page
    .getByRole("button", { name: "Mark as complete", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Mark as incomplete", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page.getByText("1 of 4 lessons", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("1 of 4 lessons", { exact: true })).toBeVisible();
  await page.goto(`/student/materials/${L_TESTING}`);
  await page
    .getByRole("button", { name: "Mark as incomplete", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Mark as complete", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page.getByText("0 of 4 lessons", { exact: true })).toBeVisible();
});

test("stu01 AC13 Overview has no built-in sample lessons and Continue learning opens the study materials", async ({
  page,
}) => {
  await signedInStudy(page);
  await page.goto("/student/overview");
  await expect(
    page.getByText("Lessons completed", { exact: true }),
  ).toBeVisible();
  const text = await page.locator("body").innerText();
  expect(text).not.toContain("3 of 8 lessons");
  expect(text).not.toContain("Clean code");
  const cont = page.getByRole("link", { name: /Continue learning/ }).first();
  await expect(cont).toHaveAttribute("href", "/student/materials");
});

test("stu01 AC13 the study materials message strings are not shown on the Overview in the loaded state", async ({
  page,
}) => {
  await signedInStudy(page);
  await page.goto("/student/overview");
  await expect(page.getByText("0 of 4 lessons", { exact: true })).toBeVisible();
  for (const m of [MSG.offline, MSG.unavailable, MSG.badShape, MSG.signIn])
    await expect(page.getByText(m)).toHaveCount(0);
});

for (const width of [390, 1440]) {
  test(`stu01 AC13 Overview fits ${width}px wide without horizontal overflow`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await signedInStudy(page);
    await page.goto("/student/overview");
    await expect(
      page.getByText("Lessons completed", { exact: true }),
    ).toBeVisible();
    const m = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      width: innerWidth,
    }));
    expect(m.scroll).toBeLessThanOrEqual(m.width);
  });
}

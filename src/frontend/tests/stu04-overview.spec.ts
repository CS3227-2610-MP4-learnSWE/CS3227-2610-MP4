import { test, expect, type Page } from "@playwright/test";
import { ADMIN, TEACHER } from "./authApi";
import {
  MSG,
  emptyProgress,
  progressError,
  sampleProgress,
  signedInProgress,
  type ProgressBody,
  type Reply,
} from "./progressApi";

/**
 * STU-04 AC14, AC16 on the student Overview `/student/overview`: three real stats from one
 * GET /api/progress, a link to the Progress page, and none of the former sample figures.
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const stat = (page: Page, name: string) =>
  page.getByRole("group", { name, exact: true });

async function openOverview(page: Page, body: ProgressBody = sampleProgress()) {
  const ctx = await signedInProgress(page, { body });
  await page.goto("/student/overview");
  return ctx;
}

test("stu04 AC14 three real stats: Lessons completed N / M, Practice average P%, Topics to revise count", async ({
  page,
}) => {
  const { api } = await openOverview(page);
  const lessons = stat(page, "Lessons completed");
  await expect(lessons).toContainText("1 / 3");
  await expect(lessons).toContainText("1 of 3 lessons");
  const avg = stat(page, "Practice average");
  await expect(avg).toContainText("33%");
  await expect(avg).toContainText(
    "Average of your latest score on each practice set (1 set)",
  );
  const topics = stat(page, "Topics to revise");
  await expect(topics).toContainText("Based on your latest practice results");
  await expect(topics.locator("strong")).toHaveText("1");
  expect(api.count).toBe(1);
  expect(api.requests[0].method).toBe("GET");
});

test("stu04 AC14 the stats use the server's totals and average, not client sums", async ({
  page,
}) => {
  const body = sampleProgress();
  body.lessons.totals = { lesson_count: 7, completed_count: 5 };
  body.practice.average_latest_percent = 66;
  body.practice.sets[0].latest = {
    correct: 2,
    total: 3,
    submitted_at: "2026-02-02T10:00:00Z",
  };
  await openOverview(page, body);
  await expect(stat(page, "Lessons completed")).toContainText("5 / 7");
  await expect(stat(page, "Lessons completed")).toContainText("5 of 7 lessons");
  await expect(stat(page, "Practice average")).toContainText("66%");
});

test("stu04 AC14 plural: several sets read (S sets)", async ({ page }) => {
  const body = sampleProgress();
  body.practice.sets.push({
    ...body.practice.sets[0],
    set_id: "x2",
    title: "Second",
  });
  body.practice.average_latest_percent = 50;
  await openOverview(page, body);
  await expect(stat(page, "Practice average")).toContainText(
    "Average of your latest score on each practice set (2 sets)",
  );
});

test("stu04 AC14 Topics to revise counts only needs-practice topics", async ({
  page,
}) => {
  const body = sampleProgress();
  body.topics.items.push({
    topic: { id: null, name: "General" },
    answered: 4,
    correct: 1,
    accuracy_percent: 25,
    status: "needs_practice",
  });
  await openOverview(page, body);
  await expect(stat(page, "Topics to revise").locator("strong")).toHaveText(
    "2",
  );
});

test("stu04 AC14 the link View full progress goes to the Progress page and pushes history", async ({
  page,
}) => {
  const { api } = await openOverview(page);
  await expect(stat(page, "Lessons completed")).toContainText("1 / 3");
  const link = page.getByRole("link", {
    name: "View full progress",
    exact: true,
  });
  await expect(link).toHaveAttribute("href", "/student/progress");
  await link.click();
  await expect(page).toHaveURL(/\/student\/progress$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Your progress" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Lesson progress", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/\/student\/overview$/);
  await expect.poll(() => api.count).toBeGreaterThanOrEqual(3);
});

test("stu04 AC14 empty: 0 / 0, 0 of 0 lessons, – with No practice submitted yet, 0 with Not enough activity yet", async ({
  page,
}) => {
  await openOverview(page, emptyProgress());
  const lessons = stat(page, "Lessons completed");
  await expect(lessons).toContainText("0 / 0");
  await expect(lessons).toContainText("0 of 0 lessons");
  const avg = stat(page, "Practice average");
  await expect(avg.locator("strong")).toHaveText("–");
  await expect(avg).toContainText("No practice submitted yet");
  const topics = stat(page, "Topics to revise");
  await expect(topics.locator("strong")).toHaveText("0");
  await expect(topics).toContainText("Not enough activity yet");
});

test("stu04 AC14 loading: each value is … and each detail Loading…", async ({
  page,
}) => {
  const { api } = await signedInProgress(page, { replies: [{ hang: true }] });
  await page.goto("/student/overview");
  for (const name of [
    "Lessons completed",
    "Practice average",
    "Topics to revise",
  ]) {
    await expect(stat(page, name).locator("strong")).toHaveText("…");
    await expect(stat(page, name)).toContainText("Loading…");
  }
  api.release();
});

const failures: [string, Reply, string][] = [
  ["unreachable", { abort: true }, MSG.statOffline],
  ["503", progressError(503, "service_unavailable"), MSG.statUnavailable],
  ["500", progressError(500, "internal_error"), MSG.statUnavailable],
  ["wrong shape", { json: { lessons: 1 } }, MSG.statUnavailable],
  ["403", progressError(403, "forbidden"), MSG.statForbidden],
];
for (const [label, reply, detail] of failures) {
  test(`stu04 AC14 failure (${label}): – and the exact detail on every stat; the rest of the Overview stays`, async ({
    page,
  }) => {
    const { api } = await signedInProgress(page, { replies: [reply] });
    await page.goto("/student/overview");
    for (const name of [
      "Lessons completed",
      "Practice average",
      "Topics to revise",
    ]) {
      await expect(stat(page, name).locator("strong")).toHaveText("–");
      await expect(stat(page, name).locator("small")).toHaveText(detail);
    }
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const text = await page.locator("body").innerText();
    expect(text).not.toMatch(/\b(503|500|403|Server says)\b/);
    await page.waitForTimeout(1200);
    expect(api.count).toBe(1); // no automatic retry
  });
}

test("stu04 AC14 timeout after 10 seconds shows the offline detail", async ({
  page,
}) => {
  const { api } = await signedInProgress(page, { replies: [{ hang: true }] });
  await page.clock.install();
  await page.goto("/student/overview");
  await expect.poll(() => api.count).toBe(1);
  await page.clock.fastForward(9_000);
  await expect(stat(page, "Lessons completed")).toContainText("Loading…");
  await page.clock.fastForward(2_000);
  await expect(stat(page, "Lessons completed")).toContainText(MSG.statOffline);
  api.release();
});

test("stu04 AC16 demo mode: – and Sign in to see your progress, no redirect", async ({
  page,
}) => {
  await signedInProgress(page, { user: null });
  await page.goto("/student/overview");
  for (const name of [
    "Lessons completed",
    "Practice average",
    "Topics to revise",
  ]) {
    await expect(stat(page, name).locator("strong")).toHaveText("–");
    await expect(stat(page, name)).toContainText(MSG.statSignIn);
  }
  await expect(page).toHaveURL(/\/student\/overview$/);
});

test("stu04 AC16 signed in: a 401 goes to /login and no stat stays on screen", async ({
  page,
}) => {
  const { auth, api } = await signedInProgress(page);
  auth.script("me", { json: { user: auth.user, csrf_token: auth.csrf } });
  auth.expire();
  await page.goto("/student/overview");
  await expect(page).toHaveURL(/\/login$/);
  expect(api.count).toBeLessThanOrEqual(1);
  await expect(page.getByText("Lessons completed")).toHaveCount(0);
});

test("stu04 AC14 the Overview no longer shows the sample figures, the streak or the rhythm chart", async ({
  page,
}) => {
  await openOverview(page);
  await expect(stat(page, "Lessons completed")).toContainText("1 / 3");
  const text = await page.locator("main").innerText();
  for (const t of [
    "82%",
    "2.4 hrs",
    "Time well spent",
    "streak",
    "learning rhythm",
    "Sample",
  ])
    expect(text.toLowerCase()).not.toContain(t.toLowerCase());
  await expect(page.getByRole("img", { name: /chart|rhythm/i })).toHaveCount(0);
});

test("stu04 AC14 the Overview sends one GET /api/progress and no GET /api/study/courses", async ({
  page,
}) => {
  const studyCalls: string[] = [];
  await page.route("**/api/study/**", (route) => {
    studyCalls.push(route.request().url());
    return route.fulfill({ status: 500, json: {} });
  });
  const { api } = await openOverview(page);
  await expect(stat(page, "Lessons completed")).toContainText("1 / 3");
  await page.waitForTimeout(500);
  expect(api.count).toBe(1);
  expect(studyCalls).toEqual([]);
});

test("stu04 AC14 Back and Forward to the Overview load it again (one request each)", async ({
  page,
}) => {
  const { api } = await openOverview(page);
  await expect(stat(page, "Lessons completed")).toContainText("1 / 3");
  expect(api.count).toBe(1);
  await page.getByRole("link", { name: "Practice", exact: true }).click();
  await expect(page).toHaveURL(/\/student\/practice$/);
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Choose a practice set",
      exact: true,
    }),
  ).toBeVisible();
  await page.goBack();
  await expect(stat(page, "Lessons completed")).toContainText("1 / 3");
  await expect.poll(() => api.count).toBe(2);
});

test("stu04 AC14 reload shows the loading state and then the stored figures", async ({
  page,
}) => {
  const { api } = await openOverview(page);
  await expect(stat(page, "Lessons completed")).toContainText("1 / 3");
  api.script({ delayMs: 800 });
  await page.reload();
  await expect(stat(page, "Lessons completed")).toContainText("Loading…");
  await expect(stat(page, "Lessons completed")).toContainText("1 / 3");
  expect(api.count).toBe(2);
});

for (const [label, user, home] of [
  ["teacher", TEACHER, "/teacher/overview"],
  ["admin", ADMIN, "/admin/analytics"],
] as const) {
  test(`stu04 AC14 a ${label} is redirected away from the student Overview without a progress request`, async ({
    page,
  }) => {
    const { api } = await signedInProgress(page, { user });
    await page.goto("/student/overview");
    await expect(page).toHaveURL(new RegExp(`${home}$`));
    expect(api.count).toBe(0);
  });
}

test("stu04 AC14 hero and companion strip are unaffected by a failed progress request", async ({
  page,
}) => {
  await signedInProgress(page, {
    replies: [progressError(503, "service_unavailable")],
  });
  await page.goto("/student/overview");
  await expect(stat(page, "Lessons completed")).toContainText(
    MSG.statUnavailable,
  );
  await expect(
    page.getByRole("link", { name: /Continue learning/ }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "View full progress", exact: true }),
  ).toBeVisible();
});

for (const width of [390, 1440]) {
  for (const theme of ["light", "dark"] as const) {
    test(`stu04 AC14 Overview fits ${width}px wide in ${theme} theme`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: theme });
      await openOverview(page);
      await expect(stat(page, "Lessons completed")).toContainText("1 / 3");
      const m = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        width: innerWidth,
      }));
      expect(m.scroll).toBeLessThanOrEqual(m.width);
    });
  }
}

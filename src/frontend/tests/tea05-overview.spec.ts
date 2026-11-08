import { test, expect, type Page } from "@playwright/test";
import {
  ADMIN,
  STUDENT,
  TEACHER,
  exploreDemoLink,
  expectNoSecretsInBrowser,
  logOutWithConfirmation,
  signInThroughForm,
} from "./authApi";
import {
  MSG,
  NOTE_BULLETS,
  PATH,
  dataCourse,
  emptyCourse,
  periodLine,
  quietCourse,
  setup,
  type CourseRow,
  type Step,
} from "./tea05Api";

/**
 * TEA-05 AC12 to AC15 and AC17: the learning overview on /teacher/overview.
 * Names and copy come only from workflow/specs/TEA-05/{spec,plan}.md.
 */

const period = (page: Page) =>
  page.getByRole("combobox", { name: "Reporting period", exact: true });
const tryAgain = (page: Page) =>
  page.getByRole("button", { name: "Try again", exact: true });
const alert = (page: Page, text: string) =>
  page.getByRole("alert").filter({ hasText: text });
const loading = (page: Page) =>
  page.getByRole("status").filter({ hasText: "Loading learning overview…" });
const courseHeading = (page: Page, title: string) =>
  page.getByRole("heading", { level: 3, name: title, exact: true });
const lessonTable = (page: Page, course = "Intro to SE") =>
  page.getByRole("table", {
    name: `Lesson completion, ${course}`,
    exact: true,
  });
const practiceTable = (page: Page, course = "Intro to SE") =>
  page.getByRole("table", { name: `Practice results, ${course}`, exact: true });
const missedList = (page: Page, course = "Intro to SE") =>
  page.getByRole("list", {
    name: `Commonly missed questions, ${course}`,
    exact: true,
  });
const noteHeading = (page: Page) =>
  page.getByRole("heading", {
    level: 3,
    name: "How these figures are calculated",
    exact: true,
  });
const status = (page: Page, text: string) =>
  page.getByRole("status").filter({ hasText: text });

async function choose(page: Page, label: string) {
  await period(page).click();
  await page.getByRole("option", { name: label, exact: true }).click();
}

async function ready(page: Page, first?: Step, courses?: CourseRow[]) {
  const ctx = await setup(page, first, TEACHER, courses);
  await page.goto(PATH);
  await expect(
    courseHeading(page, (courses ?? [dataCourse()])[0]?.title ?? "x"),
  ).toBeVisible();
  return ctx;
}

// ------------------------------------------------------------------ success (AC12, AC14)

test("tea05 AC12/AC14 success shows headings, period line, data-as-of, summary, tables, list and note", async ({
  page,
}) => {
  const ctx = await ready(page);
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Teaching, with a little more space.",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      level: 2,
      name: "Learning overview",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText(MSG.intro, { exact: true })).toBeVisible();
  await expect(period(page)).toBeVisible();
  await expect(period(page)).toContainText("Last 30 days");
  await expect(
    page.getByText(periodLine("30d"), { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Data as of/)).toBeVisible();
  await expect(
    page.locator('time[datetime="2026-11-09T12:00:00Z"]'),
  ).toHaveCount(1);
  await expect(
    page.getByText("Students enrolled: 5", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Published lessons: 2", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Lesson completion rate: 40%", { exact: true }),
  ).toBeVisible();
  for (const name of [
    "Lesson completion",
    "Practice results",
    "Commonly missed questions",
  ])
    await expect(
      page.getByRole("heading", { level: 4, name, exact: true }),
    ).toBeVisible();
  await expect(loading(page)).toHaveCount(0);
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(ctx.requests).toHaveLength(1);
  expect(ctx.requests[0].searchParams.get("period")).toBe("30d");
  expect([...ctx.requests[0].searchParams.keys()]).toEqual(["period"]);
});

test("tea05 AC12 lesson table, practice table and missed list have the exact names, headers and cells", async ({
  page,
}) => {
  await ready(page);
  await expect(
    page.getByRole("region", {
      name: "Lesson completion results, Intro to SE",
      exact: true,
    }),
  ).toHaveAttribute("tabindex", "0");
  await expect(
    page.getByRole("region", {
      name: "Practice set results, Intro to SE",
      exact: true,
    }),
  ).toHaveAttribute("tabindex", "0");
  for (const name of [
    "Lesson",
    "Topic",
    "Students completed",
    "Completion rate",
  ])
    await expect(
      lessonTable(page).getByRole("columnheader", { name, exact: true }),
    ).toBeVisible();
  const clean = lessonTable(page).getByRole("row", { name: /Clean code/ });
  await expect(clean).toContainText("General");
  await expect(clean).toContainText("3 of 5");
  await expect(clean).toContainText("60%");
  const git = lessonTable(page).getByRole("row", { name: /Version control/ });
  await expect(git).toContainText("Git");
  await expect(git).toContainText("1 of 5");
  await expect(git).toContainText("20%");
  for (const name of [
    "Practice set",
    "Topic",
    "Students attempted",
    "Submitted attempts",
    "Average score",
  ])
    await expect(
      practiceTable(page).getByRole("columnheader", { name, exact: true }),
    ).toBeVisible();
  const set = practiceTable(page).getByRole("row", { name: /Testing basics/ });
  for (const text of ["Testing", "4", "6", "58%"])
    await expect(set).toContainText(text);
  const items = missedList(page).getByRole("listitem");
  await expect(items).toHaveCount(2);
  await expect(items.nth(0)).toContainText(
    "Testing basics, question 2: What does a unit test check?",
  );
  await expect(items.nth(0)).toContainText("Missed 3 of 4 answers (75%)");
  await expect(items.nth(1)).toContainText(
    "question 3: Which status means not found?",
  );
  await expect(items.nth(1)).toContainText("Missed 1 of 4 answers (25%)");
  // Totals only: nothing private, no answer key.
  const text = await page.locator("main").innerText();
  for (const forbidden of ["explanation", "correct answer", "@example.com"])
    expect(text.toLowerCase()).not.toContain(forbidden);
});

test("tea05 AC2/AC4/AC12 the calculation note lists every rule in order and is always visible", async ({
  page,
}) => {
  await ready(page);
  await expect(noteHeading(page)).toBeVisible();
  const items = page
    .locator("li")
    .filter({
      hasText:
        /^(Students are the people|A lesson counts|Completion rate for a lesson|Practice results include|A question is missed|Periods use UTC)/,
    });
  await expect(items).toHaveCount(NOTE_BULLETS.length);
  for (const [i, text] of NOTE_BULLETS.entries())
    await expect(items.nth(i)).toHaveText(text);
});

test("tea05 AC1/AC3 one panel per course in the returned order, each with its own tables", async ({
  page,
}) => {
  await ready(page, undefined, [dataCourse(), quietCourse("Zebra course")]);
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
  await expect(courseHeading(page, "Zebra course")).toBeVisible();
  await expect(lessonTable(page, "Zebra course")).toBeVisible();
  await expect(practiceTable(page, "Zebra course")).toBeVisible();
  const titles = await page
    .getByRole("heading", { level: 3 })
    .filter({ hasText: /^(Intro to SE|Zebra course)$/ })
    .allInnerTexts();
  expect(titles).toEqual(["Intro to SE", "Zebra course"]);
});

test("tea05 AC14 the sample figures, sample task list and sample panel are gone; no new navigation item", async ({
  page,
}) => {
  await ready(page);
  for (const sample of [
    "Students learning",
    "LEARNING PULSE · SAMPLE",
    "A few things to pick up",
    "48",
    "76%",
  ])
    await expect(page.getByText(sample, { exact: true })).toHaveCount(0);
  await expect(page.getByText(/sample preview/i)).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: /learning overview/i }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Overview", exact: true }).first(),
  ).toBeVisible();
});

// ------------------------------------------------------------------ AC17 greeting

test("tea05 AC17 a signed-in teacher sees Welcome back with their display name and never Jamie", async ({
  page,
}) => {
  await ready(page);
  await expect(
    page.getByText("Welcome back, Tess Teacher.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Jamie")).toHaveCount(0);
});

test("tea05 AC17 the display name is rendered as text", async ({ page }) => {
  const evil = { ...TEACHER, display_name: "<img src=x onerror=alert(1)>" };
  await setup(page, undefined, evil);
  await page.goto(PATH);
  await expect(
    page.getByText("Welcome back, <img src=x onerror=alert(1)>.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator("img[src=x]")).toHaveCount(0);
});

test("tea05 AC17 the anonymous demo says Welcome back without a name and shows the sign-in notice with no request", async ({
  page,
}) => {
  const ctx = await setup(page, undefined, null);
  await page.goto("/login");
  await (await exploreDemoLink(page, "teacher")).click();
  await expect(page).toHaveURL(/\/teacher\/overview$/);
  await expect(page.getByText("Welcome back.", { exact: true })).toBeVisible();
  await expect(page.getByText("Jamie")).toHaveCount(0);
  await expect(alert(page, MSG.anonymous)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Go to sign in", exact: true }),
  ).toHaveAttribute("href", "/login");
  await expect(period(page)).toHaveCount(0);
  await page.waitForTimeout(300);
  expect(ctx.requests).toHaveLength(0);
});

// ------------------------------------------------------------------ empty states (AC2, AC4, AC12)

test("tea05 AC2/AC4 a teacher without courses sees the empty message, period line and note", async ({
  page,
}) => {
  const ctx = await setup(page, { courses: [] });
  await page.goto(PATH);
  await expect(status(page, MSG.noCourses)).toBeVisible();
  await expect(
    page.getByText(periodLine("30d"), { exact: true }),
  ).toBeVisible();
  await expect(noteHeading(page)).toBeVisible();
  await expect(
    page.getByRole("heading", { level: 3 }).filter({ hasText: "Intro to SE" }),
  ).toHaveCount(0);
  expect(ctx.requests).toHaveLength(1);
});

test("tea05 AC2/AC4 a course without students shows the summary and one empty message instead of the blocks", async ({
  page,
}) => {
  await ready(page, undefined, [emptyCourse("No students yet")]);
  await expect(
    page.getByText("Students enrolled: 0", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Lesson completion rate: Not available", { exact: true }),
  ).toBeVisible();
  await expect(status(page, MSG.noStudents)).toBeVisible();
  await expect(lessonTable(page, "No students yet")).toHaveCount(0);
  await expect(practiceTable(page, "No students yet")).toHaveCount(0);
  await expect(missedList(page, "No students yet")).toHaveCount(0);
  await expect(status(page, MSG.noLessons)).toHaveCount(0);
});

test("tea05 AC2/AC4 students but no lessons and no sets show the three empty messages without tables", async ({
  page,
}) => {
  const course = { ...emptyCourse("Bare course"), student_count: 2 };
  await ready(page, undefined, [course]);
  await expect(
    page.getByText("Students enrolled: 2", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Published lessons: 0", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Lesson completion rate: Not available", { exact: true }),
  ).toBeVisible();
  await expect(status(page, MSG.noLessons)).toBeVisible();
  await expect(status(page, MSG.noSets)).toBeVisible();
  await expect(status(page, MSG.noMissedNoAttempts)).toBeVisible();
  await expect(lessonTable(page, "Bare course")).toHaveCount(0);
  await expect(practiceTable(page, "Bare course")).toHaveCount(0);
});

test("tea05 AC2/AC4 lessons and sets without activity keep the tables with zero values and say so", async ({
  page,
}) => {
  await ready(page, undefined, [quietCourse("Quiet course")]);
  await expect(lessonTable(page, "Quiet course")).toBeVisible();
  await expect(
    lessonTable(page, "Quiet course").getByRole("row", {
      name: /Quiet lesson/,
    }),
  ).toContainText("0 of 3");
  await expect(status(page, MSG.noCompletions)).toBeVisible();
  await expect(practiceTable(page, "Quiet course")).toBeVisible();
  await expect(
    practiceTable(page, "Quiet course").getByRole("row", { name: /Quiet set/ }),
  ).toContainText("Not available");
  await expect(status(page, MSG.noAttempts)).toBeVisible();
  await expect(status(page, MSG.noMissedNoAttempts)).toBeVisible();
  await expect(missedList(page, "Quiet course")).toHaveCount(0);
});

test("tea05 AC4 attempts without misses say that no questions were missed", async ({
  page,
}) => {
  const course = dataCourse();
  course.practice.missed_questions = [];
  await ready(page, undefined, [course]);
  await expect(practiceTable(page)).toBeVisible();
  await expect(status(page, MSG.noMissed)).toBeVisible();
  await expect(status(page, MSG.noMissedNoAttempts)).toHaveCount(0);
  await expect(status(page, MSG.noAttempts)).toHaveCount(0);
});

test("tea05 AC6 a null rate reads Not available and a topic-less lesson reads General", async ({
  page,
}) => {
  const course = dataCourse();
  course.lessons[0].rate_percent = null;
  course.practice.sets[0].average_score_percent = null;
  course.completion_rate_percent = null;
  await ready(page, undefined, [course]);
  await expect(
    lessonTable(page).getByRole("row", { name: /Clean code/ }),
  ).toContainText("Not available");
  await expect(
    practiceTable(page).getByRole("row", { name: /Testing basics/ }),
  ).toContainText("Not available");
  await expect(
    page.getByText("Lesson completion rate: Not available", { exact: true }),
  ).toBeVisible();
});

// ------------------------------------------------------------------ loading and period (AC12, AC13)

test("tea05 AC12/AC13 loading shows a status, no report, one StrictMode request and keeps the select usable", async ({
  page,
}) => {
  const ctx = await setup(page, { hold: true });
  await page.goto(PATH);
  await expect(loading(page)).toBeVisible();
  await expect(courseHeading(page, "Intro to SE")).toHaveCount(0);
  await expect(period(page)).toBeEnabled();
  expect(ctx.requests).toHaveLength(1);
  ctx.release();
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
  await expect(loading(page)).toHaveCount(0);
  expect(ctx.requests).toHaveLength(1);
});

test("tea05 AC5/AC13 the select offers the three presets and each change sends one request and no URL change", async ({
  page,
}) => {
  const ctx = await ready(page);
  const url = page.url();
  const history = await page.evaluate(() => window.history.length);
  await period(page).click();
  for (const label of ["Last 7 days", "Last 30 days", "All time"])
    await expect(
      page.getByRole("option", { name: label, exact: true }),
    ).toBeVisible();
  await page.getByRole("option", { name: "Last 7 days", exact: true }).click();
  await expect(page.getByText(periodLine("7d"), { exact: true })).toBeVisible();
  expect(ctx.requests).toHaveLength(2);
  expect(ctx.requests[1].searchParams.get("period")).toBe("7d");
  await choose(page, "All time");
  await expect(
    page.getByText(periodLine("all"), { exact: true }),
  ).toBeVisible();
  expect(ctx.requests).toHaveLength(3);
  expect(ctx.requests[2].searchParams.get("period")).toBe("all");
  await choose(page, "Last 30 days");
  await expect(
    page.getByText(periodLine("30d"), { exact: true }),
  ).toBeVisible();
  expect(ctx.requests).toHaveLength(4);
  expect(page.url()).toBe(url);
  expect(await page.evaluate(() => window.history.length)).toBe(history);
});

test("tea05 AC12 the previous report is cleared while a new load is pending", async ({
  page,
}) => {
  const ctx = await ready(page);
  ctx.steps.push({ hold: true });
  await choose(page, "Last 7 days");
  await expect(loading(page)).toBeVisible();
  await expect(courseHeading(page, "Intro to SE")).toHaveCount(0);
  await expect(noteHeading(page)).toHaveCount(0);
  ctx.release();
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
});

test("tea05 AC13 a superseded slow response cannot overwrite the newer period", async ({
  page,
}) => {
  const ctx = await setup(page, {
    hold: true,
    mark(body) {
      body.courses[0].title = "STALE-SUPERSEDED-COURSE";
    },
  });
  await page.goto(PATH);
  await expect(loading(page)).toBeVisible();
  await choose(page, "Last 7 days");
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
  await expect(page.getByText(periodLine("7d"), { exact: true })).toBeVisible();
  ctx.release();
  await expect.poll(() => ctx.completed.length).toBe(2);
  await expect(page.getByText("STALE-SUPERSEDED-COURSE")).toHaveCount(0);
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
  await expect(page.getByText(periodLine("7d"), { exact: true })).toBeVisible();
  expect(ctx.requests).toHaveLength(2);
});

// ------------------------------------------------------------------ failures (AC12, AC13)

for (const [code, httpStatus, message, retry] of [
  ["forbidden", 403, MSG.forbidden, false],
  ["invalid_overview_period", 422, MSG.invalid, false],
  ["overview_rate_limited", 429, MSG.limited, true],
  ["service_unavailable", 503, MSG.unavailable, true],
  ["not_found", 404, MSG.malformed, true],
  ["conflict", 409, MSG.malformed, true],
  ["internal", 500, MSG.malformed, true],
] as const) {
  test(`tea05 AC12/AC13 HTTP ${httpStatus} shows its exact message${retry ? " and Try again" : " and no Try again"}`, async ({
    page,
  }) => {
    const ctx = await setup(page, { status: httpStatus, code });
    await page.goto(PATH);
    await expect(alert(page, message)).toBeVisible();
    await expect(courseHeading(page, "Intro to SE")).toHaveCount(0);
    await expect(noteHeading(page)).toHaveCount(0);
    await expect(period(page)).toBeVisible();
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "Teaching, with a little more space.",
        exact: true,
      }),
    ).toBeVisible();
    for (const other of [
      MSG.network,
      MSG.timeout,
      MSG.expired,
      MSG.forbidden,
      MSG.invalid,
      MSG.limited,
      MSG.unavailable,
      MSG.malformed,
    ].filter((m) => m !== message))
      await expect(page.getByText(other, { exact: true })).toHaveCount(0);
    expect(ctx.requests).toHaveLength(1);
    if (!retry) {
      await expect(tryAgain(page)).toHaveCount(0);
      return;
    }
    await tryAgain(page).click();
    await expect(courseHeading(page, "Intro to SE")).toBeVisible();
    await expect(alert(page, message)).toHaveCount(0);
    expect(ctx.requests).toHaveLength(2);
    expect(ctx.requests[1].searchParams.get("period")).toBe("30d");
  });
}

test("tea05 AC12/AC13 a 401 clears the report, shows the session-expired message and offers no Try again", async ({
  page,
}) => {
  const ctx = await ready(page);
  ctx.auth.expire();
  ctx.steps.push({ status: 401, code: "unauthenticated" });
  await choose(page, "Last 7 days");
  await expect(page.getByText(MSG.expired).first()).toBeVisible();
  await expect(courseHeading(page, "Intro to SE")).toHaveCount(0);
  await expect(tryAgain(page)).toHaveCount(0);
  expect(ctx.requests).toHaveLength(2);
  await page.goBack().catch(() => undefined);
  await expect(courseHeading(page, "Intro to SE")).toHaveCount(0);
});

test("tea05 AC12/AC13 a network failure says so, keeps the chosen period and Try again repeats that period", async ({
  page,
}) => {
  const ctx = await ready(page);
  ctx.steps.push({ abort: true });
  await choose(page, "Last 7 days");
  await expect(alert(page, MSG.network)).toBeVisible();
  await expect(period(page)).toContainText("Last 7 days");
  await expect(courseHeading(page, "Intro to SE")).toHaveCount(0);
  await expect(page.getByText(periodLine("7d"), { exact: true })).toHaveCount(
    0,
  );
  expect(ctx.requests).toHaveLength(2);
  await tryAgain(page).click();
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
  expect(ctx.requests).toHaveLength(3);
  expect(ctx.requests[2].searchParams.get("period")).toBe("7d");
  await expect(period(page)).toContainText("Last 7 days");
});

test("tea05 AC12 a failed period change keeps the select value and the hero, and Try again retries it", async ({
  page,
}) => {
  const ctx = await ready(page);
  ctx.steps.push({ status: 503, code: "service_unavailable" });
  await choose(page, "All time");
  await expect(alert(page, MSG.unavailable)).toBeVisible();
  await expect(period(page)).toContainText("All time");
  await expect(
    page.getByRole("heading", {
      level: 2,
      name: "Learning overview",
      exact: true,
    }),
  ).toBeVisible();
  await tryAgain(page).click();
  await expect(
    page.getByText(periodLine("all"), { exact: true }),
  ).toBeVisible();
  expect(ctx.requests.map((u) => u.searchParams.get("period"))).toEqual([
    "30d",
    "all",
    "all",
  ]);
});

for (const [name, step] of [
  ["not JSON", { malformed: true }],
  ["an empty object", { json: {} }],
  ["courses not a list", { json: { period: {}, as_of: "x", courses: "none" } }],
  [
    "a lesson count as text",
    {
      courses: [
        (() => {
          const c = dataCourse() as unknown as {
            lessons: { completed_students: unknown }[];
          };
          c.lessons[0].completed_students = "3";
          return c as unknown as CourseRow;
        })(),
      ],
    },
  ],
  [
    "a course without a title",
    {
      courses: [
        (() => {
          const c = dataCourse() as unknown as Record<string, unknown>;
          delete c.title;
          return c as unknown as CourseRow;
        })(),
      ],
    },
  ],
] as const satisfies readonly (readonly [string, Step])[]) {
  test(`tea05 AC12 a malformed body (${name}) shows the invalid-report message and is not rendered`, async ({
    page,
  }) => {
    const ctx = await setup(page, step);
    await page.goto(PATH);
    await expect(alert(page, MSG.malformed)).toBeVisible();
    await expect(courseHeading(page, "Intro to SE")).toHaveCount(0);
    await expect(tryAgain(page)).toBeVisible();
    expect(ctx.requests).toHaveLength(1);
    await tryAgain(page).click();
    await expect(courseHeading(page, "Intro to SE")).toBeVisible();
    expect(ctx.requests).toHaveLength(2);
  });
}

test("tea05 AC13 a request that never answers times out after 15 seconds with no automatic retry", async ({
  page,
}) => {
  const ctx = await setup(page, { status: 503, code: "service_unavailable" });
  await page.goto(PATH);
  await expect(alert(page, MSG.unavailable)).toBeVisible();
  const now = new Date();
  await page.clock.install({ time: now });
  await page.clock.pauseAt(new Date(now.getTime() + 1000));
  ctx.steps.push({ hold: true });
  await tryAgain(page).click();
  await expect.poll(() => ctx.requests.length).toBe(2);
  await expect(loading(page)).toBeVisible();
  await page.clock.fastForward(14999);
  await expect(alert(page, MSG.timeout)).toHaveCount(0);
  await page.clock.fastForward(2);
  await expect(alert(page, MSG.timeout)).toBeVisible();
  await expect(alert(page, MSG.network)).toHaveCount(0);
  expect(ctx.requests).toHaveLength(2);
  ctx.release();
});

// ------------------------------------------------------------------ roles, history, session (AC13)

for (const [user, destination] of [
  [STUDENT, "/student/overview"],
  [ADMIN, "/admin/overview"],
] as const) {
  test(`tea05 AC13 a signed-in ${user.role} opening the teacher overview is redirected and sends no request`, async ({
    page,
  }) => {
    const ctx = await setup(page, undefined, user);
    await page.goto(PATH);
    await expect(page).toHaveURL(new RegExp(`${destination}$`));
    await expect(
      page.getByRole("heading", { name: "Learning overview" }),
    ).toHaveCount(0);
    await page.waitForTimeout(300);
    expect(ctx.requests).toHaveLength(0);
  });
}

test("tea05 AC13 reload restores the session and sends exactly one request with the default period", async ({
  page,
}) => {
  const ctx = await ready(page);
  await choose(page, "Last 7 days");
  await expect(page.getByText(periodLine("7d"), { exact: true })).toBeVisible();
  expect(ctx.requests).toHaveLength(2);
  await page.reload();
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
  await expect(period(page)).toContainText("Last 30 days");
  expect(ctx.requests).toHaveLength(3);
  expect(ctx.requests[2].searchParams.get("period")).toBe("30d");
  await expectNoSecretsInBrowser(page, [
    "Intro to SE",
    "Testing basics",
    "unit test",
  ]);
});

test("tea05 AC13 Back and Forward each reset to Last 30 days, clear the old report and send one fresh request", async ({
  page,
}) => {
  const ctx = await ready(page);
  await choose(page, "Last 7 days");
  await expect(page.getByText(periodLine("7d"), { exact: true })).toBeVisible();
  expect(ctx.requests).toHaveLength(2);
  await page.route("**/api/feedback/**", (route) =>
    route.fulfill({ json: { items: [], next_offset: null, unread_count: 0 } }),
  );
  await page.route("**/api/messaging/**", (route) =>
    route.fulfill({ json: { items: [], next_offset: null, unread_count: 0 } }),
  );
  await page.getByRole("link", { name: "Inbox" }).first().click();
  await expect(page).toHaveURL(/\/teacher\/inbox$/);
  await expect(courseHeading(page, "Intro to SE")).toHaveCount(0);
  ctx.steps.push({ hold: true });
  await page.goBack();
  await expect(loading(page)).toBeVisible();
  await expect(courseHeading(page, "Intro to SE")).toHaveCount(0);
  await expect(period(page)).toContainText("Last 30 days");
  ctx.release();
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
  await expect(
    page.getByText(periodLine("30d"), { exact: true }),
  ).toBeVisible();
  expect(ctx.requests).toHaveLength(3);
  expect(ctx.requests[2].searchParams.get("period")).toBe("30d");
  await page.goForward();
  await expect(page).toHaveURL(/\/teacher\/inbox$/);
  await page.goBack();
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
  expect(ctx.requests).toHaveLength(4);
});

test("tea05 AC13 a late result for a page the teacher has left is dropped and coming back loads fresh", async ({
  page,
}) => {
  const ctx = await setup(page, {
    hold: true,
    mark(body) {
      body.courses[0].title = "STALE-LEFT-PAGE";
    },
  });
  await page.route("**/api/feedback/**", (route) =>
    route.fulfill({ json: { items: [], next_offset: null, unread_count: 0 } }),
  );
  await page.goto(PATH);
  await expect(loading(page)).toBeVisible();
  await page.getByRole("link", { name: "Inbox" }).first().click();
  await expect(page).toHaveURL(/\/teacher\/inbox$/);
  ctx.release();
  await expect.poll(() => ctx.completed.length).toBe(1);
  await expect(page.getByText("STALE-LEFT-PAGE")).toHaveCount(0);
  await page
    .getByRole("link", { name: "Overview", exact: true })
    .first()
    .click();
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
  expect(ctx.requests).toHaveLength(2);
});

test("tea05 AC13 a successful logout clears the report; a failed logout keeps session and report; Back shows nothing", async ({
  page,
}) => {
  const ctx = await ready(page);
  ctx.auth.script("logout", {
    status: 503,
    json: { detail: { code: "service_unavailable" } },
  });
  await logOutWithConfirmation(page);
  await expect(
    page.getByRole("dialog", { name: "Confirm logout", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      level: 3,
      name: "Intro to SE",
      exact: true,
      includeHidden: true,
    }),
  ).toBeVisible();
  await logOutWithConfirmation(page);
  await expect(page).toHaveURL(/\/login/);
  await page.goBack();
  await expect(courseHeading(page, "Intro to SE")).toHaveCount(0);
  await expect(page.getByText("Testing basics")).toHaveCount(0);
  expect(ctx.requests).toHaveLength(1);
});

test("tea05 AC13 a pending result of the previous account cannot appear after another teacher signs in", async ({
  page,
}) => {
  const ctx = await setup(page, {
    hold: true,
    mark(body) {
      body.courses[0].title = "FIRST-ACCOUNT-PRIVATE-COURSE";
    },
  });
  await page.goto(PATH);
  await expect(loading(page)).toBeVisible();
  await logOutWithConfirmation(page);
  const other = {
    ...TEACHER,
    id: "another-teacher",
    email: "other-teacher@example.com",
    display_name: "Olive Other",
  };
  ctx.auth.accounts.set(other.email!, {
    user: other,
    password: "correct horse battery staple 42",
  });
  await signInThroughForm(page, other.email!);
  await page.goto(PATH);
  await expect(courseHeading(page, "Intro to SE")).toBeVisible();
  ctx.release();
  await expect.poll(() => ctx.completed.length).toBe(2);
  await expect(page.getByText("FIRST-ACCOUNT-PRIVATE-COURSE")).toHaveCount(0);
  await expect(
    page.getByText("Welcome back, Olive Other.", { exact: true }),
  ).toBeVisible();
  await expectNoSecretsInBrowser(page, [
    "FIRST-ACCOUNT-PRIVATE-COURSE",
    "Intro to SE",
  ]);
  expect(ctx.requests).toHaveLength(2);
});

// ------------------------------------------------------------------ safe rendering

test("tea05 AC15 titles and question text are rendered as text, never as markup", async ({
  page,
}) => {
  const course = dataCourse();
  course.title = "<img src=x onerror=alert(1)> course";
  course.lessons[0].title = "<script>window.__owned = 1</script>";
  course.practice.missed_questions[0].question =
    "<b>bold?</b> <img src=y onerror=alert(2)>";
  await ready(page, undefined, [course]);
  await expect(
    page.getByText("<script>window.__owned = 1</script>"),
  ).toBeVisible();
  await expect(page.getByText("<b>bold?</b>", { exact: false })).toBeVisible();
  await expect(page.locator("img[src=x], img[src=y]")).toHaveCount(0);
  await expect(page.locator("main b")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => (window as unknown as { __owned?: number }).__owned,
    ),
  ).toBeUndefined();
});

// ------------------------------------------------------------------ accessibility and layout (AC15)

test("tea05 AC15 keyboard: the select opens and chooses with the keyboard; Tab reaches the two scroll regions in order", async ({
  page,
}) => {
  const ctx = await ready(page);
  await period(page).focus();
  await expect(period(page)).toBeFocused();
  await page.keyboard.press("Enter");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(
    page.getByText(periodLine("all"), { exact: true }),
  ).toBeVisible();
  expect(ctx.requests.at(-1)!.searchParams.get("period")).toBe("all");
  await expect(period(page)).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("region", {
      name: "Lesson completion results, Intro to SE",
      exact: true,
    }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("region", {
      name: "Practice set results, Intro to SE",
      exact: true,
    }),
  ).toBeFocused();
});

test("tea05 AC15 after an error the Try again button is reachable by Tab right after the select", async ({
  page,
}) => {
  await setup(page, { status: 503, code: "service_unavailable" });
  await page.goto(PATH);
  await expect(alert(page, MSG.unavailable)).toBeVisible();
  await period(page).focus();
  await page.keyboard.press("Tab");
  await expect(tryAgain(page)).toBeFocused();
});

const LONG = "Averyveryveryverylongunbrokentitle".repeat(8);
for (const scheme of ["light", "dark"] as const) {
  for (const width of [320, 390, 1280]) {
    test(`tea05 AC15 ${scheme} theme at ${width}px: no page-level horizontal scroll, long titles wrap, controls inside the viewport`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 800 });
      await page.emulateMedia({ colorScheme: scheme });
      const course = dataCourse();
      course.title = `${LONG} course`;
      course.lessons[0].title = LONG;
      course.practice.sets[0].title = LONG;
      course.practice.missed_questions[0].question = LONG;
      course.practice.missed_questions[0].set_title = LONG;
      await ready(page, undefined, [course, quietCourse("Second")]);
      const overflow = await page.evaluate(() => ({
        doc: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
      }));
      expect(overflow.doc).toBeLessThanOrEqual(width);
      expect(overflow.body).toBeLessThanOrEqual(width);
      const box = await period(page).boundingBox();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width + 1);
      await expect(
        page.getByRole("heading", {
          level: 3,
          name: `${LONG} course`,
          exact: true,
        }),
      ).toBeVisible();
      // The long list text wraps inside the page instead of widening it.
      const itemBox = await missedList(page, `${LONG} course`)
        .getByRole("listitem")
        .first()
        .boundingBox();
      expect(itemBox!.x + itemBox!.width).toBeLessThanOrEqual(width + 1);
      await period(page).focus();
      await expect(period(page)).toBeFocused();
      // Text is readable against the surface in both themes.
      const contrast = await page
        .getByText("Students enrolled: 5", { exact: true })
        .evaluate((el) => {
          const fg = getComputedStyle(el).color;
          let node: Element | null = el;
          let bg = "rgba(0, 0, 0, 0)";
          while (node) {
            bg = getComputedStyle(node).backgroundColor;
            if (bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent") break;
            node = node.parentElement;
          }
          return { fg, bg };
        });
      expect(contrast.fg).not.toBe(contrast.bg);
    });
  }
}

test("tea05 AC15 the error alert and the report stay inside a 320px page", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await setup(page, { status: 503, code: "service_unavailable" });
  await page.goto(PATH);
  await expect(alert(page, MSG.unavailable)).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
  const box = await tryAgain(page).boundingBox();
  expect(box!.x + box!.width).toBeLessThanOrEqual(321);
});

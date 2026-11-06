import { test, expect, type Page } from "@playwright/test";
import { logOutWithConfirmation, ADMIN, TEACHER } from "./authApi";
import { L_TESTING } from "./lessonsApi";
import {
  MSG,
  RULE_TEXT,
  SET_TITLE,
  emptyProgress,
  progressError,
  sampleProgress,
  signedInProgress,
  type ProgressBody,
  type Reply,
} from "./progressApi";

/**
 * STU-04 AC2, AC4, AC13, AC15, AC16 on the Progress page `/student/progress`.
 * Every state, exact copy and accessible role/name of the spec's "UI states and copy" and the
 * plan's "UI contract".
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const h1 = (page: Page) =>
  page.getByRole("heading", { level: 1, name: "Your progress" });
const region = (page: Page, name: string) =>
  page.getByRole("region", { name, exact: true });
const alertWith = (page: Page, text: string) =>
  page.getByRole("alert").filter({ hasText: text });

async function openProgress(page: Page, body: ProgressBody = sampleProgress()) {
  const ctx = await signedInProgress(page, { body });
  await page.goto("/student/progress");
  await expect(h1(page)).toBeVisible();
  return ctx;
}

// ------------------------------------------------------------------ structure and success
test("stu04 AC1 page has heading level 1, three named regions with level 2 headings and a sidebar link", async ({
  page,
}) => {
  await openProgress(page);
  for (const name of [
    "Lesson progress",
    "Practice scores",
    "Topics to revise",
  ]) {
    await expect(region(page, name)).toBeVisible();
    await expect(
      region(page, name).getByRole("heading", { level: 2, name, exact: true }),
    ).toBeVisible();
  }
  const link = page.getByRole("link", { name: "Progress", exact: true });
  await expect(link).toHaveAttribute("href", "/student/progress");
});

test("stu04 AC1 sidebar has Progress between Practice and Inbox", async ({
  page,
}) => {
  await openProgress(page);
  const names = await page
    .getByRole("navigation")
    .first()
    .getByRole("link")
    .allInnerTexts();
  const trimmed = names.map((n) => n.trim());
  const iPractice = trimmed.indexOf("Practice");
  const iProgress = trimmed.indexOf("Progress");
  const iInbox = trimmed.findIndex((n) => n.startsWith("Inbox"));
  expect(iPractice).toBeGreaterThanOrEqual(0);
  expect(iProgress).toBe(iPractice + 1);
  expect(iInbox).toBe(iProgress + 1);
});

test("stu04 AC1 lesson progress: courses A to Z with N of M lessons complete and recent lessons as links", async ({
  page,
}) => {
  await openProgress(page);
  const items = page
    .getByRole("list", { name: "Courses" })
    .getByRole("listitem");
  await expect(items).toHaveCount(2);
  await expect(items.nth(0)).toContainText("Algorithms");
  await expect(items.nth(0)).toContainText("0 of 1 lessons complete");
  await expect(items.nth(1)).toContainText("Software Engineering");
  await expect(items.nth(1)).toContainText("1 of 2 lessons complete");
  const recent = page.getByRole("list", { name: "Recently completed" });
  const link = recent.getByRole("link", {
    name: "Unit testing basics",
    exact: true,
  });
  await expect(link).toHaveAttribute("href", `/student/materials/${L_TESTING}`);
});

test("stu04 AC1 recently completed shows the server's entries in the given order, newest first", async ({
  page,
}) => {
  const body = sampleProgress();
  body.lessons.recent = [
    "Lesson five",
    "Lesson four",
    "Lesson three",
    "Lesson two",
    "Lesson one",
  ].map((title, i) => ({
    lesson_id: `55555555-5555-4555-8555-55555555550${i}`,
    course_id: body.lessons.courses[1].id,
    title,
    completed_at: `2026-02-0${5 - i}T10:00:00Z`,
  }));
  await openProgress(page, body);
  await expect(
    page.getByRole("list", { name: "Recently completed" }).getByRole("link"),
  ).toHaveText([
    "Lesson five",
    "Lesson four",
    "Lesson three",
    "Lesson two",
    "Lesson one",
  ]);
});

test("stu04 AC1 practice scores table: headers, C / T scores and a whole-number attempt count", async ({
  page,
}) => {
  await openProgress(page);
  const table = page.getByRole("table", { name: "Practice scores" });
  await expect(table).toBeVisible();
  for (const h of [
    "Practice set",
    "Best score",
    "Latest score",
    "Submitted attempts",
  ])
    await expect(
      table.getByRole("columnheader", { name: h, exact: true }),
    ).toBeVisible();
  const row = table.getByRole("row").filter({ hasText: SET_TITLE });
  await expect(row.getByRole("cell").nth(0)).toHaveText(SET_TITLE);
  await expect(row.getByRole("cell").nth(1)).toHaveText("2 / 3");
  await expect(row.getByRole("cell").nth(2)).toHaveText("1 / 3");
  await expect(row.getByRole("cell").nth(3)).toHaveText("3");
});

test("stu04 AC1 practice sets are listed A to Z by title", async ({ page }) => {
  const body = sampleProgress();
  const base = body.practice.sets[0];
  body.practice.sets = [
    { ...base, set_id: "zz", title: "zebra set" },
    { ...base, set_id: "aa", title: "Alpha set" },
  ];
  // The server sorts (plan: lower(title)); the page keeps the response order.
  body.practice.sets.reverse();
  await openProgress(page, body);
  const rows = page
    .getByRole("table", { name: "Practice scores" })
    .getByRole("row");
  await expect(rows.nth(1)).toContainText("Alpha set");
  await expect(rows.nth(2)).toContainText("zebra set");
});

test("stu04 AC3 topics: rule text, item texts and three lists named as in the contract", async ({
  page,
}) => {
  await openProgress(page);
  const topics = region(page, "Topics to revise");
  await expect(topics.getByText(RULE_TEXT, { exact: true })).toBeVisible();
  await expect(
    topics
      .getByRole("list", { name: "Topics to revise", exact: true })
      .getByRole("listitem"),
  ).toHaveText([`${SET_TITLE}: 1 of 3 correct (33%)`]);
  await expect(
    topics
      .getByRole("list", { name: "On track", exact: true })
      .getByRole("listitem"),
  ).toHaveText(["Testing: 3 of 5 correct (60%)"]);
  await expect(
    topics
      .getByRole("list", { name: "Not enough activity yet", exact: true })
      .getByRole("listitem"),
  ).toHaveText([
    "Design: only 2 of 3 answers so far, not enough activity yet.",
  ]);
  await expect(topics.getByText(MSG.noneNeedPractice)).toHaveCount(0);
});

test("stu04 AC11 the rule text is built from topics.rule of the response", async ({
  page,
}) => {
  const body = sampleProgress();
  body.topics.rule = { min_answers: 4, weak_below_percent: 70 };
  body.topics.items = [
    {
      topic: { id: null, name: "General" },
      answered: 2,
      correct: 0,
      accuracy_percent: 0,
      status: "insufficient",
    },
  ];
  await openProgress(page, body);
  await expect(
    page.getByText(
      "A topic needs practice when you have answered at least 4 questions on it and fewer than 70% were correct. Only your latest submitted attempt on each practice set counts.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "General: only 2 of 4 answers so far, not enough activity yet.",
      { exact: true },
    ),
  ).toBeVisible();
});

test("stu04 AC3 when topics are answered but none needs practice the page says so, above the other lists", async ({
  page,
}) => {
  const body = sampleProgress();
  body.topics.items = body.topics.items.filter(
    (i) => i.status !== "needs_practice",
  );
  await openProgress(page, body);
  const topics = region(page, "Topics to revise");
  await expect(
    topics.getByText(MSG.noneNeedPractice, { exact: true }),
  ).toBeVisible();
  await expect(
    topics.getByRole("list", { name: "Topics to revise", exact: true }),
  ).toHaveCount(0);
  await expect(topics.getByRole("list", { name: "On track" })).toBeVisible();
});

test("stu04 AC1 a list is only rendered when it has items", async ({
  page,
}) => {
  const body = sampleProgress();
  body.topics.items = body.topics.items.filter((i) => i.status === "on_track");
  await openProgress(page, body);
  const topics = region(page, "Topics to revise");
  await expect(topics.getByRole("list", { name: "On track" })).toBeVisible();
  await expect(
    topics.getByRole("list", { name: "Not enough activity yet", exact: true }),
  ).toHaveCount(0);
});

// ------------------------------------------------------------------ empty states
test("stu04 AC13 no courses and no practice: Join a course, No practice results yet, Nothing to revise yet", async ({
  page,
}) => {
  await openProgress(page, emptyProgress());
  const lessons = region(page, "Lesson progress");
  await expect(
    lessons.getByRole("heading", { level: 3, name: "Join a course to start" }),
  ).toBeVisible();
  await expect(lessons.getByText(MSG.noCourses, { exact: true })).toBeVisible();
  const practice = region(page, "Practice scores");
  await expect(
    practice.getByRole("heading", {
      level: 3,
      name: "No practice results yet",
    }),
  ).toBeVisible();
  await expect(
    practice.getByText(MSG.noPractice, { exact: true }),
  ).toBeVisible();
  await expect(
    practice.getByRole("link", { name: "Go to practice" }),
  ).toHaveAttribute("href", "/student/practice");
  await expect(practice.getByRole("table")).toHaveCount(0);
  const topics = region(page, "Topics to revise");
  await expect(
    topics.getByRole("heading", { level: 3, name: "Nothing to revise yet" }),
  ).toBeVisible();
  await expect(topics.getByText(MSG.noTopics, { exact: true })).toBeVisible();
});

test("stu04 AC13 courses with lessons but no activity: 0 of M, No lessons completed yet and Open study materials", async ({
  page,
}) => {
  const body = emptyProgress();
  body.lessons.courses = [
    {
      id: "11111111-1111-4111-8111-111111111111",
      title: "Software Engineering",
      lesson_count: 2,
      completed_count: 0,
    },
    {
      id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      title: "Empty course",
      lesson_count: 0,
      completed_count: 0,
    },
  ];
  body.lessons.totals = { lesson_count: 2, completed_count: 0 };
  await openProgress(page, body);
  const lessons = region(page, "Lesson progress");
  const items = lessons
    .getByRole("list", { name: "Courses" })
    .getByRole("listitem");
  await expect(items.filter({ hasText: "Software Engineering" })).toContainText(
    "0 of 2 lessons complete",
  );
  const empty = items.filter({ hasText: "Empty course" });
  await expect(empty).toContainText(MSG.noLessonsPublished);
  await expect(empty).not.toContainText("0 of 0");
  await expect(
    lessons.getByText(MSG.noLessonsDone, { exact: true }),
  ).toBeVisible();
  await expect(
    lessons.getByRole("link", { name: "Open study materials" }),
  ).toHaveAttribute("href", "/student/materials");
  await expect(lessons.getByText("Join a course to start")).toHaveCount(0);
});

test("stu04 AC4 AC13 every topic insufficient: heading, text and the insufficient list", async ({
  page,
}) => {
  const body = sampleProgress();
  body.topics.items = [
    {
      topic: { id: null, name: "General" },
      answered: 2,
      correct: 0,
      accuracy_percent: 0,
      status: "insufficient",
    },
  ];
  await openProgress(page, body);
  const topics = region(page, "Topics to revise");
  await expect(
    topics.getByRole("heading", { level: 3, name: "Not enough activity yet" }),
  ).toBeVisible();
  await expect(
    topics.getByText(MSG.allInsufficient, { exact: true }),
  ).toBeVisible();
  await expect(
    topics
      .getByRole("list", { name: "Not enough activity yet", exact: true })
      .getByRole("listitem"),
  ).toHaveText([
    "General: only 2 of 3 answers so far, not enough activity yet.",
  ]);
  await expect(topics.getByText("Nothing to revise yet")).toHaveCount(0);
  await expect(topics.getByText(MSG.noneNeedPractice)).toHaveCount(0);
});

test("stu04 AC4 an insufficient topic is never called weak", async ({
  page,
}) => {
  await openProgress(page);
  await expect(
    region(page, "Topics to revise")
      .getByRole("list", { name: "Topics to revise", exact: true })
      .getByText("Design"),
  ).toHaveCount(0);
});

// ------------------------------------------------------------------ loading
test("stu04 AC15 loading: heading stays, status Loading your progress… and no section yet", async ({
  page,
}) => {
  const { api } = await signedInProgress(page, { replies: [{ hang: true }] });
  await page.goto("/student/progress");
  await expect(h1(page)).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: MSG.loading }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Lesson progress" }),
  ).toHaveCount(0);
  api.release();
});

// ------------------------------------------------------------------ failures
const failures: [string, Reply, string][] = [
  ["unreachable", { abort: true }, MSG.offline],
  ["503", progressError(503, "service_unavailable"), MSG.unavailable],
  ["500", progressError(500, "internal_error"), MSG.unavailable],
  [
    "502 with a non-JSON body",
    { status: 502, body: "<html>Bad gateway</html>" },
    MSG.unavailable,
  ],
  ["wrong shape", { json: { lessons: 1 } }, MSG.badShape],
  [
    "invalid status value",
    {
      json: (() => {
        const b = sampleProgress();
        (b.topics.items[0] as { status: string }).status = "weak";
        return b;
      })(),
    },
    MSG.badShape,
  ],
  [
    "negative count",
    {
      json: (() => {
        const b = sampleProgress();
        b.lessons.totals.lesson_count = -1;
        return b;
      })(),
    },
    MSG.badShape,
  ],
];
for (const [label, reply, message] of failures) {
  test(`stu04 AC15 failure (${label}): exact message in an alert, Try again, no raw detail`, async ({
    page,
  }) => {
    await signedInProgress(page, { replies: [reply] });
    await page.goto("/student/progress");
    await expect(alertWith(page, message)).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Try again", exact: true }),
    ).toBeVisible();
    await expect(h1(page)).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Lesson progress" }),
    ).toHaveCount(0);
    const text = await page.locator("body").innerText();
    expect(text).not.toMatch(
      /\b(503|502|500|Server says|Bad gateway|undefined)\b/,
    );
    const other = [MSG.offline, MSG.unavailable, MSG.badShape].filter(
      (m) => m !== message,
    );
    for (const m of other) await expect(page.getByText(m)).toHaveCount(0);
  });
}

test("stu04 AC15 timeout: no error before 10 seconds, the offline message after", async ({
  page,
}) => {
  const { api } = await signedInProgress(page, { replies: [{ hang: true }] });
  await page.clock.install();
  await page.goto("/student/progress");
  await expect.poll(() => api.count).toBe(1);
  await page.clock.fastForward(9_000);
  await expect(page.getByText(MSG.offline)).toHaveCount(0);
  await expect(page.getByText(MSG.loading)).toBeVisible();
  await page.clock.fastForward(2_000);
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  api.release();
});

test("stu04 AC15 403: message in an alert and no Try again button", async ({
  page,
}) => {
  await signedInProgress(page, { replies: [progressError(403, "forbidden")] });
  await page.goto("/student/progress");
  await expect(alertWith(page, MSG.forbidden)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  await expect(h1(page)).toBeVisible();
});

test("stu04 AC15 a failed load keeps the heading and shows no data from an earlier load", async ({
  page,
}) => {
  const { api } = await signedInProgress(page, { body: sampleProgress() });
  await page.goto("/student/progress");
  await expect(region(page, "Lesson progress")).toBeVisible();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(
    page.getByRole("group", { name: "Lessons completed", exact: true }),
  ).toContainText("1 / 3");
  api.script({ abort: true });
  await page.getByRole("link", { name: "Progress", exact: true }).click();
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await expect(page.getByText("Software Engineering")).toHaveCount(0);
  await expect(page.getByText(SET_TITLE)).toHaveCount(0);
  await expect(h1(page)).toBeVisible();
});

// ------------------------------------------------------------------ Try again
test("stu04 AC15 Try again sends exactly one new request, shows loading, then the data; URL unchanged", async ({
  page,
}) => {
  const { api } = await signedInProgress(page, {
    replies: [progressError(503, "service_unavailable")],
  });
  await page.goto("/student/progress");
  await expect(alertWith(page, MSG.unavailable)).toBeVisible();
  expect(api.count).toBe(1);
  api.body = sampleProgress();
  api.script({ delayMs: 800 });
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: MSG.loading }),
  ).toBeVisible();
  await expect(page.getByText(MSG.unavailable)).toHaveCount(0);
  await expect(region(page, "Lesson progress")).toBeVisible();
  expect(api.count).toBe(2);
  await expect(page).toHaveURL(/\/student\/progress$/);
});

test("stu04 AC15 Try again succeeds after the backend returns", async ({
  page,
}) => {
  const { api } = await signedInProgress(page, {
    body: sampleProgress(),
    replies: [{ abort: true }],
  });
  await page.goto("/student/progress");
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(region(page, "Practice scores")).toBeVisible();
  await expect(page.getByText(MSG.offline)).toHaveCount(0);
  expect(api.count).toBe(2);
});

test("stu04 AC15 a new failure replaces the earlier message and nothing retries by itself", async ({
  page,
}) => {
  const { api } = await signedInProgress(page, {
    replies: [{ abort: true }, progressError(503, "service_unavailable")],
  });
  await page.goto("/student/progress");
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await page.waitForTimeout(1500);
  expect(api.count).toBe(1);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(alertWith(page, MSG.unavailable)).toBeVisible();
  await expect(page.getByText(MSG.offline)).toHaveCount(0);
  await page.waitForTimeout(1500);
  expect(api.count).toBe(2);
});

// ------------------------------------------------------------------ requests, history, session
test("stu04 AC15 exactly one GET /api/progress on load (StrictMode shares in-flight requests)", async ({
  page,
}) => {
  const { api } = await openProgress(page);
  await expect(region(page, "Practice scores")).toBeVisible();
  await page.waitForTimeout(500);
  expect(api.count).toBe(1);
  expect(api.requests[0].method).toBe("GET");
  expect(api.requests[0].search).toBe("");
});

test("stu04 AC15 reload shows Loading your progress… then the stored figures; nothing in browser storage", async ({
  page,
}) => {
  const { api } = await openProgress(page);
  api.script({ delayMs: 800 });
  await page.reload();
  await expect(
    page.getByRole("status").filter({ hasText: MSG.loading }),
  ).toBeVisible();
  await expect(region(page, "Lesson progress")).toBeVisible();
  expect(api.count).toBe(2);
  const stored = await page.evaluate(() =>
    JSON.stringify([
      Object.entries(localStorage),
      Object.entries(sessionStorage),
    ]),
  );
  expect(stored).not.toContain(SET_TITLE);
  expect(stored).not.toContain("Unit testing basics");
});

test("stu04 AC15 Back and Forward re-request the page (no client cache)", async ({
  page,
}) => {
  const { api } = await openProgress(page);
  expect(api.count).toBe(1);
  await page.getByRole("link", { name: "Practice", exact: true }).click();
  await expect(page).toHaveURL(/\/student\/practice$/);
  await page.goBack();
  await expect(region(page, "Lesson progress")).toBeVisible();
  await expect.poll(() => api.count).toBe(2);
  await page.goForward();
  await page.goBack();
  await expect.poll(() => api.count).toBe(3);
});

test("stu04 AC15 Go to practice pushes a history entry and Back returns to Progress", async ({
  page,
}) => {
  await openProgress(page, emptyProgress());
  await page.getByRole("link", { name: "Go to practice" }).click();
  await expect(page).toHaveURL(/\/student\/practice$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/student\/progress$/);
});

test("stu04 AC15 Open study materials pushes a history entry and Back returns to Progress", async ({
  page,
}) => {
  const body = sampleProgress();
  body.lessons.courses[1].completed_count = 0;
  body.lessons.recent = [];
  await openProgress(page, body);
  await page.getByRole("link", { name: "Open study materials" }).click();
  await expect(page).toHaveURL(/\/student\/materials$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/student\/progress$/);
});

test("stu04 AC15 a lesson link opens that lesson and Back returns to Progress", async ({
  page,
}) => {
  await openProgress(page);
  await page
    .getByRole("link", { name: "Unit testing basics", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`/student/materials/${L_TESTING}$`));
  await page.goBack();
  await expect(page).toHaveURL(/\/student\/progress$/);
  await expect(h1(page)).toBeVisible();
});

test("stu04 AC16 signed in: a 401 goes to /login and nothing of the session stays on screen", async ({
  page,
}) => {
  const { auth, api } = await signedInProgress(page, {
    body: sampleProgress(),
  });
  auth.script("me", { json: { user: auth.user, csrf_token: auth.csrf } });
  auth.expire();
  await page.goto("/student/progress");
  await expect(page).toHaveURL(/\/login$/);
  expect(api.count).toBeLessThanOrEqual(1);
  await expect(page.getByText(SET_TITLE)).toHaveCount(0);
  await expect(page.getByText("Your progress")).toHaveCount(0);
});

test("stu04 AC16 demo mode: a 401 shows the sign-in notice with a Go to sign in link, no redirect", async ({
  page,
}) => {
  await signedInProgress(page, { user: null });
  await page.goto("/student/progress");
  await expect(alertWith(page, MSG.signIn)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Go to sign in" }),
  ).toHaveAttribute("href", "/login");
  await expect(page).toHaveURL(/\/student\/progress$/);
  await expect(
    page.getByRole("region", { name: "Lesson progress" }),
  ).toHaveCount(0);
  await page.getByRole("link", { name: "Go to sign in" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/student\/progress$/);
});

test("stu04 AC16 logout then Back shows no progress data", async ({ page }) => {
  const { auth } = await openProgress(page);
  await logOutWithConfirmation(page);
  await page.waitForURL("**/login");
  expect(auth.user).toBeNull();
  await page.goBack();
  await expect(page.getByText(SET_TITLE)).toHaveCount(0);
  await expect(page.getByText("Unit testing basics")).toHaveCount(0);
});

for (const [label, user, home] of [
  ["teacher", TEACHER, "/teacher/overview"],
  ["admin", ADMIN, "/admin/overview"],
] as const) {
  test(`stu04 AC5 wrong role: a ${label} opening /student/progress is redirected before any progress request`, async ({
    page,
  }) => {
    const { api } = await signedInProgress(page, { user });
    await page.goto("/student/progress");
    await expect(page).toHaveURL(new RegExp(`${home}$`));
    expect(api.count).toBe(0);
    await expect(page.getByText(SET_TITLE)).toHaveCount(0);
  });

  test(`stu04 AC5 wrong role: a ${label} opening /student/overview is redirected before any progress request`, async ({
    page,
  }) => {
    const { api } = await signedInProgress(page, { user });
    await page.goto("/student/overview");
    await expect(page).toHaveURL(new RegExp(`${home}$`));
    expect(api.count).toBe(0);
  });
}

// ------------------------------------------------------------------ safe rendering and layout
test("stu04 AC15 titles and topic names are plain text: markup and links are not interpreted", async ({
  page,
}) => {
  const body = sampleProgress();
  const evil =
    '<img src=x onerror="window.__xss=1"> <b>bold</b> https://example.com/x';
  body.lessons.courses[1].title = evil;
  body.practice.sets[0].title = evil;
  body.topics.items[0].topic.name = evil;
  body.lessons.recent[0].title = evil;
  await openProgress(page, body);
  await expect(page.locator("img[src='x']")).toHaveCount(0);
  await expect(page.locator("main b")).toHaveCount(0);
  expect(
    await page.evaluate(() => (window as unknown as { __xss?: number }).__xss),
  ).toBeUndefined();
  await expect(
    page.locator("main").getByText(evil, { exact: false }).first(),
  ).toBeVisible();
  await expect(
    page.locator("main a[href='https://example.com/x']"),
  ).toHaveCount(0);
});

test("stu04 AC15 the page shows no chart and none of the removed sample figures", async ({
  page,
}) => {
  await openProgress(page);
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
  await expect(page.locator("main canvas, main svg[role='img']")).toHaveCount(
    0,
  );
});

for (const width of [390, 1440]) {
  for (const theme of ["light", "dark"] as const) {
    test(`stu04 AC15 Progress fits ${width}px wide in ${theme} theme; the table scrolls inside its panel`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: theme });
      const body = sampleProgress();
      body.practice.sets[0].title =
        "A very long practice set title that must wrap or scroll inside the panel and not widen the page";
      await openProgress(page, body);
      await expect(
        page.getByRole("table", { name: "Practice scores" }),
      ).toBeVisible();
      const m = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        width: innerWidth,
      }));
      expect(m.scroll).toBeLessThanOrEqual(m.width);
    });
  }
}

test("stu04 AC15 controls are keyboard reachable: Try again takes focus by Tab and activates with Enter", async ({
  page,
}) => {
  const { api } = await signedInProgress(page, { replies: [{ abort: true }] });
  await page.goto("/student/progress");
  const retry = page.getByRole("button", { name: "Try again" });
  await expect(retry).toBeVisible();
  await retry.focus();
  await expect(retry).toBeFocused();
  api.body = sampleProgress();
  await page.keyboard.press("Enter");
  await expect(region(page, "Lesson progress")).toBeVisible();
});

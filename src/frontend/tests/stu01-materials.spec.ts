import { test, expect, type Page } from "@playwright/test";
import { ADMIN, NOTICE, STUDENT, TEACHER } from "./authApi";
import {
  COURSE_ALGO,
  COURSE_SE,
  L_DESIGN,
  L_GENERAL,
  L_TESTING,
  LESSONS,
  MSG,
  type Reply,
  customLesson,
  signedInStudy,
  studyError,
} from "./lessonsApi";

/**
 * STU-01 AC1, AC5, AC12, AC13, AC14: the materials list (browse, filter, search, states).
 * Copy and roles come from workflow/specs/STU-01/spec.md "UI states and copy" and plan.md "UI contract".
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const list = (page: Page) => page.locator('a[href^="/student/materials/"]');
const topicButton = (page: Page, name: string) =>
  page.getByRole("button", { name, exact: true });
const search = (page: Page) =>
  page.getByRole("textbox", { name: "Search materials" });
const course = (page: Page) => page.getByRole("combobox", { name: "Course" });
const alertWith = (page: Page, text: string) =>
  page.getByRole("alert").filter({ hasText: text });
const hrefs = (page: Page) =>
  list(page).evaluateAll((els) =>
    els.map((e) => (e as HTMLAnchorElement).getAttribute("href")),
  );

async function openSe(page: Page) {
  await page.goto(`/student/materials?course=${COURSE_SE}`);
  await expect(
    page.getByRole("link", { name: /Unit testing basics/ }),
  ).toBeVisible();
}

// ---------------------------------------------------------------- AC1, AC5 browse
test("stu01 AC5 shows the heading, a course select A to Z with the first course chosen, and its lessons", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await page.goto("/student/materials");
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Small lessons. Lasting understanding.",
    }),
  ).toBeVisible();
  await expect(course(page)).toBeVisible();
  const options = await course(page).locator("option").allTextContents();
  expect(options).toEqual(["Algorithms", "Software Engineering"]);
  await expect(course(page)).toHaveValue(COURSE_ALGO);
  await expect(
    page.getByRole("link", { name: /Binary search basics/ }),
  ).toBeVisible();
  await expect(page.getByText("0 of 1 lessons complete")).toBeVisible();
  expect(api.count("courses")).toBe(1);
  expect(api.of("lessons").map((r) => r.courseId)).toEqual([COURSE_ALGO]);
});

test("stu01 AC5 lessons are grouped by topic: topics A to Z, General last, each card shows title, excerpt and status", async ({
  page,
}) => {
  await signedInStudy(page, { done: [L_GENERAL] });
  await openSe(page);
  expect(await hrefs(page)).toEqual([
    `/student/materials/${L_DESIGN}`,
    `/student/materials/${L_TESTING}`,
    `/student/materials/${L_GENERAL}`,
  ]);
  const testing = page.getByRole("link", { name: /Unit testing basics/ });
  await expect(testing).toContainText("Testing");
  await expect(testing).toContainText(
    "Write small tests first. Run them often.",
  );
  await expect(testing).toContainText("Start learning");
  await expect(testing).not.toContainText("Complete");
  const general = page.getByRole("link", { name: /Clean code habits/ });
  await expect(general).toContainText("Complete");
  await expect(general).not.toContainText("Start learning");
  await expect(general).toContainText("General");
  await expect(page.getByText("1 of 3 lessons complete")).toBeVisible();
});

test("stu01 AC5 the count comes from the lessons response of the selected course", async ({
  page,
}) => {
  await signedInStudy(page, { done: [L_TESTING, L_DESIGN] });
  await openSe(page);
  await expect(page.getByText("2 of 3 lessons complete")).toBeVisible();
});

test("stu01 AC5 a card links to the lesson page and opens it", async ({
  page,
}) => {
  await signedInStudy(page);
  await openSe(page);
  const card = page.getByRole("link", { name: /Unit testing basics/ });
  await expect(card).toHaveAttribute("href", `/student/materials/${L_TESTING}`);
  await card.click();
  await expect(page).toHaveURL(new RegExp(`/student/materials/${L_TESTING}$`));
  await expect(
    page.getByRole("heading", { level: 1, name: "Unit testing basics" }),
  ).toBeVisible();
});

test("stu01 AC5 the topic buttons are All topics plus each topic that has a lesson, with aria-pressed", async ({
  page,
}) => {
  await signedInStudy(page);
  await openSe(page);
  for (const name of ["All topics", "Design", "Testing", "General"])
    await expect(topicButton(page, name)).toBeVisible();
  await expect(topicButton(page, "All topics")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(topicButton(page, "Testing")).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await topicButton(page, "Testing").click();
  await expect(topicButton(page, "Testing")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(topicButton(page, "All topics")).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  expect(await hrefs(page)).toEqual([`/student/materials/${L_TESTING}`]);
  await topicButton(page, "All topics").click();
  expect(await list(page).count()).toBe(3);
});

test("stu01 AC5 topic filtering is client side (no extra request)", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openSe(page);
  const before = api.requests.length;
  await topicButton(page, "Design").click();
  await search(page).fill("design");
  await expect(list(page)).toHaveCount(1);
  expect(api.requests.length).toBe(before);
});

test("stu01 AC5 search filters lesson titles case-insensitively and can be combined with a topic", async ({
  page,
}) => {
  await signedInStudy(page);
  await openSe(page);
  await search(page).fill("CLEAN");
  expect(await hrefs(page)).toEqual([`/student/materials/${L_GENERAL}`]);
  await search(page).fill("");
  await expect(list(page)).toHaveCount(3);
  await topicButton(page, "Testing").click();
  await search(page).fill("design");
  await expect(
    page.getByRole("heading", { level: 3, name: "Nothing here just yet" }),
  ).toBeVisible();
  await expect(page.getByText(MSG.noMatch)).toBeVisible();
  await search(page).fill("unit");
  await expect(list(page)).toHaveCount(1);
});

test("stu01 AC5 search only looks at titles, not lesson content", async ({
  page,
}) => {
  await signedInStudy(page);
  await openSe(page);
  await search(page).fill("small tests first");
  await expect(
    page.getByRole("heading", { level: 3, name: "Nothing here just yet" }),
  ).toBeVisible();
});

test("stu01 AC5 changing the course loads that course, updates ?course= and resets topic and search", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openSe(page);
  await topicButton(page, "Testing").click();
  await search(page).fill("unit");
  await course(page).selectOption({ label: "Algorithms" });
  await expect(page).toHaveURL(new RegExp(`course=${COURSE_ALGO}`));
  await expect(
    page.getByRole("link", { name: /Binary search basics/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Unit testing basics/ }),
  ).toHaveCount(0);
  await expect(search(page)).toHaveValue("");
  await expect(topicButton(page, "All topics")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(api.of("lessons").map((r) => r.courseId)).toEqual([
    COURSE_SE,
    COURSE_ALGO,
  ]);
  expect(api.count("courses")).toBe(1);
});

test("stu01 AC5 the course in ?course= is selected; an unknown or non-member id is ignored without an error", async ({
  page,
}) => {
  await signedInStudy(page);
  await page.goto(`/student/materials?course=${COURSE_SE}`);
  await expect(course(page)).toHaveValue(COURSE_SE);
  await page.goto(
    "/student/materials?course=99999999-9999-4999-8999-999999999999",
  );
  await expect(course(page)).toHaveValue(COURSE_ALGO);
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.goto("/student/materials?course=not-a-uuid");
  await expect(course(page)).toHaveValue(COURSE_ALGO);
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("stu01 AC1 the course select is shown even when the student has one course", async ({
  page,
}) => {
  await signedInStudy(page, {
    courses: [{ id: COURSE_SE, title: "Software Engineering" }],
  });
  await page.goto("/student/materials");
  await expect(course(page)).toBeVisible();
  await expect(course(page).locator("option")).toHaveCount(1);
});

test("stu01 AC8 refresh reloads from the server, keeps the course and resets topic and search", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openSe(page);
  await topicButton(page, "Testing").click();
  await search(page).fill("unit");
  await page.reload();
  await expect(course(page)).toHaveValue(COURSE_SE);
  await expect(list(page)).toHaveCount(3);
  await expect(search(page)).toHaveValue("");
  await expect(topicButton(page, "All topics")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(api.count("courses")).toBe(2);
});

test("stu01 AC8 completion is read from the server on every load and nothing is kept in browser storage", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openSe(page);
  await expect(page.getByText("0 of 3 lessons complete")).toBeVisible();
  api.done.set(L_TESTING, "2026-02-02T00:00:00.000Z");
  await page.reload();
  await expect(page.getByText("1 of 3 lessons complete")).toBeVisible();
  const stored = await page.evaluate(() =>
    JSON.stringify([
      Object.entries(localStorage),
      Object.entries(sessionStorage),
      document.cookie,
    ]),
  );
  expect(stored.toLowerCase()).not.toContain("lesson");
  expect(stored).not.toContain(L_TESTING);
});

// ---------------------------------------------------------------- empty states
test("stu01 AC13 no courses: heading, text and no course select", async ({
  page,
}) => {
  await signedInStudy(page, { courses: [] });
  await page.goto("/student/materials");
  await expect(
    page.getByRole("heading", { level: 3, name: "No courses yet" }),
  ).toBeVisible();
  await expect(page.getByText(MSG.noCourses)).toBeVisible();
  await expect(course(page)).toHaveCount(0);
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Small lessons. Lasting understanding.",
    }),
  ).toBeVisible();
});

test("stu01 AC13 a course without published lessons shows the empty state and keeps the select", async ({
  page,
}) => {
  await signedInStudy(page, { lessons: [] });
  await page.goto("/student/materials");
  await expect(
    page.getByRole("heading", { level: 3, name: "No lessons published yet" }),
  ).toBeVisible();
  await expect(page.getByText(MSG.noLessons)).toBeVisible();
  await expect(course(page)).toBeVisible();
});

// ---------------------------------------------------------------- loading
test("stu01 AC13 the first load shows the status text and no course select or lessons yet", async ({
  page,
}) => {
  const { api } = await signedInStudy(page, {
    replies: { courses: [{ hang: true }] },
  });
  await page.goto("/student/materials");
  await expect(
    page.getByRole("status").filter({ hasText: MSG.loadingList }),
  ).toBeVisible();
  await expect(course(page)).toHaveCount(0);
  await expect(list(page)).toHaveCount(0);
  api.release();
});

test("stu01 AC13 changing the course shows the loading status over the lessons while the select stays usable", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openSe(page);
  api.script("lessons", { hang: true });
  await course(page).selectOption({ label: "Algorithms" });
  await expect(
    page.getByRole("status").filter({ hasText: MSG.loadingList }),
  ).toBeVisible();
  await expect(course(page)).toBeEnabled();
  await expect(
    page.getByRole("link", { name: /Unit testing basics/ }),
  ).toHaveCount(0);
  api.release();
});

// ---------------------------------------------------------------- failures on the courses request
const loadFailures: [string, Reply, string][] = [
  ["unreachable", { abort: true }, MSG.offline],
  [
    "503 service_unavailable",
    studyError(503, "service_unavailable"),
    MSG.unavailable,
  ],
  ["500", studyError(500, "internal_error"), MSG.unavailable],
  [
    "502 with a raw body",
    { status: 502, body: "<html>Bad gateway</html>" },
    MSG.unavailable,
  ],
  [
    "200 with a body of the wrong shape",
    { json: { courses: "nope" } },
    MSG.badShape,
  ],
  ["200 with an unrelated body", { json: [] }, MSG.badShape],
];

for (const [label, reply, message] of loadFailures) {
  test(`stu01 AC13 courses request ${label}: exact message and Try again repeats only the courses request`, async ({
    page,
  }) => {
    const { api } = await signedInStudy(page, {
      replies: { courses: [reply] },
    });
    await page.goto("/student/materials");
    await expect(alertWith(page, message)).toBeVisible();
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "Small lessons. Lasting understanding.",
      }),
    ).toBeVisible();
    await expect(course(page)).toHaveCount(0);
    const text = (await page.locator("body").innerText()) ?? "";
    expect(text).not.toMatch(/\b(502|503|500|Traceback|Server says)\b/);
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(
      page.getByRole("link", { name: /Binary search basics/ }),
    ).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    expect(api.count("courses")).toBe(2);
    expect(api.count("lessons")).toBe(1);
  });
}

for (const [label, user, area] of [
  ["teacher", TEACHER, /\/teacher\//],
  ["admin", ADMIN, /\/admin\//],
] as const) {
  test(`stu01 AC6 a ${label} who opens the materials URL is redirected by the role guard and no study request is sent`, async ({
    page,
  }) => {
    const { api } = await signedInStudy(page, { user });
    await page.goto("/student/materials");
    await expect(page).toHaveURL(area);
    await expect(alertWith(page, MSG.forbidden)).toHaveCount(0);
    expect(api.requests).toHaveLength(0);
  });
}

test("stu01 AC13 a 403 forbidden (role changed after sign-in) shows the access message and no retry", async ({
  page,
}) => {
  const { api } = await signedInStudy(page, {
    replies: { courses: [studyError(403, "forbidden")] },
  });
  await page.goto("/student/materials");
  await expect(alertWith(page, MSG.forbidden)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  expect(api.count("courses")).toBe(1);
});

test("stu01 AC13 the courses request times out after 10 seconds with the unreachable message", async ({
  page,
}) => {
  const { api } = await signedInStudy(page, {
    replies: { courses: [{ hang: true }] },
  });
  await page.clock.install();
  await page.goto("/student/materials");
  await expect.poll(() => api.count("courses")).toBe(1);
  await page.clock.fastForward(9_000);
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.clock.fastForward(2_000);
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  api.release();
});

// ---------------------------------------------------------------- failures on the lessons request
test("stu01 AC13 a failed lessons request keeps the course select and search text, shows no stale lessons, and Try again repeats only that request", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openSe(page);
  await search(page).fill("unit");
  api.script("lessons", { abort: true });
  await course(page).selectOption({ label: "Algorithms" });
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await expect(course(page)).toBeEnabled();
  await expect(
    page.getByRole("link", { name: /Unit testing basics/ }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: /Binary search basics/ }),
  ).toHaveCount(0);
  const coursesBefore = api.count("courses");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByRole("link", { name: /Binary search basics/ }),
  ).toBeVisible();
  expect(api.count("courses")).toBe(coursesBefore);
  expect(api.of("lessons").map((r) => r.courseId)).toEqual([
    COURSE_SE,
    COURSE_ALGO,
    COURSE_ALGO,
  ]);
});

test("stu01 AC13 lessons request 503, 500 and a bad shape use the shared messages", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openSe(page);
  const cases: [Reply, string][] = [
    [studyError(503, "service_unavailable"), MSG.unavailable],
    [studyError(500, "internal_error"), MSG.unavailable],
    [{ json: { course: {}, topics: "x" } }, MSG.badShape],
  ];
  for (const [reply, message] of cases) {
    api.script("lessons", reply);
    await page.reload();
    await expect(alertWith(page, message)).toBeVisible();
    await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  }
});

test("stu01 AC13 lessons request 404 (membership removed) says the course is not available and has no retry", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openSe(page);
  api.script("lessons", studyError(404, "not_found", "Course not found."));
  await course(page).selectOption({ label: "Algorithms" });
  await expect(alertWith(page, MSG.courseGone)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  await expect(course(page)).toBeEnabled();
  await course(page).selectOption({ label: "Software Engineering" });
  await expect(
    page.getByRole("link", { name: /Unit testing basics/ }),
  ).toBeVisible();
});

test("stu01 AC13 the list can wait up to 20 seconds in total: two sequential 10 second timeouts", async ({
  page,
}) => {
  const { api } = await signedInStudy(page, {
    replies: { lessons: [{ hang: true }] },
  });
  await page.clock.install();
  await page.goto("/student/materials");
  await expect.poll(() => api.count("lessons")).toBe(1);
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.clock.fastForward(11_000);
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await expect(course(page)).toBeVisible();
  api.release();
});

test("stu01 AC13 recovery after the backend comes back needs no reload", async ({
  page,
}) => {
  await signedInStudy(page, {
    replies: { courses: [{ abort: true }, { abort: true }] },
  });
  await page.goto("/student/materials");
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(course(page)).toBeVisible();
});

// ---------------------------------------------------------------- AC14 session
test("stu01 AC14 a 401 while signed in goes to /login and shows no lesson data", async ({
  page,
}) => {
  const { auth } = await signedInStudy(page);
  await openSe(page);
  auth.expire();
  await course(page).selectOption({ label: "Algorithms" });
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText("Unit testing basics")).toHaveCount(0);
  await expect(page.getByText("Binary search basics")).toHaveCount(0);
});

test("stu01 AC14 a 401 on the first request while signed in goes to /login", async ({
  page,
}) => {
  const { auth } = await signedInStudy(page);
  auth.script("me", { json: { user: STUDENT, csrf_token: auth.csrf } });
  auth.expire();
  await page.goto("/student/materials");
  await expect(page).toHaveURL(/\/login$/);
});

test("stu01 AC14 demo mode: the sign-in notice with the materials message replaces the data", async ({
  page,
}) => {
  await signedInStudy(page, { user: null });
  await page.goto("/student/materials");
  await expect(page.getByText(MSG.signIn)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Go to sign in" }),
  ).toHaveAttribute("href", "/login");
  await expect(page).toHaveURL(/\/student\/materials$/);
  await expect(page.getByText(NOTICE)).toHaveCount(0);
  await expect(list(page)).toHaveCount(0);
  await expect(course(page)).toHaveCount(0);
});

test("stu01 AC14 demo mode shows none of the old built-in sample lessons", async ({
  page,
}) => {
  await signedInStudy(page, { user: null });
  await page.goto("/student/materials");
  await expect(page.getByText(MSG.signIn)).toBeVisible();
  const body = await page.locator("body").innerText();
  for (const sample of [
    "Clean code",
    "Easy to change",
    "Small lessons, big impact",
  ])
    expect(body).not.toContain(sample);
});

test("stu01 AC14 after the session expires, browser Back to the list shows no lesson data", async ({
  page,
}) => {
  const { auth } = await signedInStudy(page);
  await openSe(page);
  await page.getByRole("link", { name: /Unit testing basics/ }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: "Unit testing basics" }),
  ).toBeVisible();
  auth.expire();
  await page.goBack();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText("Unit testing basics")).toHaveCount(0);
});

// ---------------------------------------------------------------- AC12 safe rendering
test("stu01 AC12 HTML in a lesson title and excerpt is shown as text and never runs", async ({
  page,
}) => {
  const evil = customLesson({
    id: "aaaaaaaa-0000-4000-8000-000000000001",
    title: "<img src=x onerror=window.__pwned=1> Title",
    content: "<script>window.__pwned=2</script> <b>bold</b>\nsecond",
  });
  await signedInStudy(page, { lessons: [...LESSONS, evil] });
  await openSe(page);
  await expect(
    page.getByText("<img src=x onerror=window.__pwned=1> Title"),
  ).toBeVisible();
  await expect(
    page.getByText("<script>window.__pwned=2</script>"),
  ).toBeVisible();
  await expect(page.locator('img[src="x"]')).toHaveCount(0);
  await expect(page.locator("main b")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => (window as unknown as { __pwned?: number }).__pwned,
    ),
  ).toBeUndefined();
});

// ---------------------------------------------------------------- back navigation
test("stu01 AC13 Back from a lesson returns to the list of that course, reloaded with the new status", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openSe(page);
  await page.getByRole("link", { name: /Unit testing basics/ }).click();
  await page
    .getByRole("button", { name: "Mark as complete", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Mark as incomplete", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "All study materials" }).click();
  await expect(page).toHaveURL(
    new RegExp(`/student/materials\\?course=${COURSE_SE}$`),
  );
  await expect(page.getByText("1 of 3 lessons complete")).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Unit testing basics/ }),
  ).toContainText("Complete");
  expect(api.isDone(L_TESTING)).toBe(true);
  // History is list, lesson, list: the Back link is an ordinary push.
  await page.goBack();
  await expect(
    page.getByRole("heading", { level: 1, name: "Unit testing basics" }),
  ).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL(
    new RegExp(`/student/materials\\?course=${COURSE_SE}$`),
  );
  await expect(course(page)).toBeVisible();
  await expect(page.getByText("1 of 3 lessons complete")).toBeVisible();
});

// ---------------------------------------------------------------- layout and theme
for (const theme of ["light", "dark"] as const) {
  for (const width of [390, 1440]) {
    test(`stu01 AC13 materials list fits ${width}px wide in the ${theme} theme without horizontal overflow`, async ({
      page,
    }) => {
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 900 });
      await signedInStudy(page);
      await openSe(page);
      const overflow = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        width: innerWidth,
      }));
      expect(overflow.scroll).toBeLessThanOrEqual(overflow.width);
      await expect(search(page)).toBeVisible();
      await expect(course(page)).toBeVisible();
    });
  }
}

test("stu01 AC13 the controls are reachable by keyboard and show a focus outline", async ({
  page,
}) => {
  await signedInStudy(page);
  await openSe(page);
  await search(page).focus();
  const outline = await search(page).evaluate((el) => {
    const s = getComputedStyle(el);
    return `${s.outlineStyle}|${s.boxShadow}|${s.borderColor}`;
  });
  expect(outline).not.toBe("");
  await topicButton(page, "Testing").focus();
  await expect(topicButton(page, "Testing")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(topicButton(page, "Testing")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await course(page).focus();
  await expect(course(page)).toBeFocused();
});

test("stu01 AC2 the study pages never send an identity header or a user id", async ({
  page,
}) => {
  const { api } = await signedInStudy(page);
  await openSe(page);
  await page.getByRole("link", { name: /Unit testing basics/ }).click();
  await page
    .getByRole("button", { name: "Mark as complete", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Mark as incomplete", exact: true }),
  ).toBeVisible();
  expect(api.requests.length).toBeGreaterThanOrEqual(4);
  for (const r of api.requests) {
    expect(r.headers["x-student-id"]).toBeUndefined();
    expect(r.headers["x-demo-user-id"]).toBeUndefined();
    expect(r.path).not.toMatch(/user/i);
    expect(JSON.stringify(r.body)).not.toMatch(/user/i);
  }
});

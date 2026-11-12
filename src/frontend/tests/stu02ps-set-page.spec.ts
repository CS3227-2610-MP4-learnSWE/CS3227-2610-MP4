import { test, expect, type Page } from "@playwright/test";
import { ADMIN, NOTICE, STUDENT, TEACHER, mockAuthApi } from "./authApi";
import {
  ALL_CORRECT,
  FIXTURE_SET,
  SET_ID,
  UNKNOWN_SET_ID,
  apiError,
  catalogCourse,
  catalogSet,
  mockPracticeApi,
  type MockOptions,
} from "./practiceApi";

/**
 * STU-02-published-sets AC16: the practice page `/student/practice/SETID`.
 * The set id is read from the URL; new not-available states; every old state is kept.
 */

const NOT_AVAILABLE = "This practice set is not available to you.";
const NO_LONGER = "This practice set is no longer available to you.";
const LOAD_FAILED = "We could not load the practice set. Please try again.";
const FORBIDDEN = "You do not have access to practice.";
const LOADING = "Loading the practice set…";
const SUBMIT = "Submit practice set";
const OTHER_SET = "b1111111-1111-4111-8111-111111111111";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const alertWith = (page: Page, text: string) =>
  page.getByRole("alert").filter({ hasText: text });
const backLink = (page: Page) =>
  page.getByRole("link", { name: "Back to practice sets", exact: true });

function choice(questionId: string, choiceId: string) {
  const q = FIXTURE_SET.questions.find((x) => x.id === questionId)!;
  return q.choices.find((c) => c.id === choiceId)!.text;
}
const radio = (page: Page, q: string, c: string) =>
  page.getByRole("radio", { name: choice(q, c), exact: true });

async function openSet(
  page: Page,
  options: MockOptions = {},
  path = `/student/practice/${SET_ID}`,
  user: typeof STUDENT | null = STUDENT,
) {
  const auth = await mockAuthApi(page, { user });
  const mock = await mockPracticeApi(page, { auth, ...options });
  await page.goto(path);
  return { auth, mock };
}

async function pickAll(page: Page) {
  for (const [q, c] of Object.entries(ALL_CORRECT))
    await radio(page, q, c).check();
}

// ------------------------------------------------------------------ the set id comes from the URL
test("stu02ps AC16 the page requests the set named in the URL, once, and shows it", async ({
  page,
}) => {
  const { mock } = await openSet(page);
  await expect(radio(page, "q1", "a")).toBeVisible();
  expect(mock.count("getSet")).toBe(1);
  expect(mock.of("getSet")[0].path).toBe(`/api/practice-sets/${SET_ID}`);
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Put your knowledge to work.",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { level: 2, name: FIXTURE_SET.title }),
  ).toBeVisible();
  await expect(page.getByText("3 MCQs · Whole-set submission")).toBeVisible();
});

test("stu02ps AC16 the hard-coded subject tag no longer exists", async ({
  page,
}) => {
  await openSet(page);
  await expect(radio(page, "q1", "a")).toBeVisible();
  await expect(page.getByText("SOFTWARE ENGINEERING ESSENTIALS")).toHaveCount(
    0,
  );
  await expect(page.getByText(/software engineering essentials/i)).toHaveCount(
    0,
  );
});

test("stu02ps AC16 every practice request uses the URL's set id and never the old fixture id", async ({
  page,
}) => {
  const { mock } = await openSet(page);
  await pickAll(page);
  await page.getByRole("button", { name: SUBMIT }).click();
  await expect(page.getByText("Correct answer:").first()).toBeVisible();
  expect(mock.order).toEqual(["getSet", "start", "save", "submit", "results"]);
  expect(mock.of("start")[0].path).toBe(
    `/api/practice-sets/${SET_ID}/attempts`,
  );
  for (const r of mock.requests) expect(r.path).not.toContain("intro-se-1");
});

test("stu02ps AC16 loading: the status shows with the heading and no questions", async ({
  page,
}) => {
  const { mock } = await openSet(page, {
    replies: { getSet: [{ passThrough: true, delayMs: 800 }] },
  });
  await expect(
    page.getByRole("status").filter({ hasText: LOADING }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Put your knowledge to work.",
    }),
  ).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(0);
  await expect(radio(page, "q1", "a")).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: LOADING }),
  ).toHaveCount(0);
  expect(mock.count("getSet")).toBe(1);
});

// ------------------------------------------------------------------ not available
test("stu02ps AC16 an unknown set (404) shows the not-available message, a link back, no Try again", async ({
  page,
}) => {
  const { mock } = await openSet(
    page,
    {},
    `/student/practice/${UNKNOWN_SET_ID}`,
  );
  const alert = alertWith(page, NOT_AVAILABLE);
  await expect(alert).toBeVisible();
  await expect(backLink(page)).toHaveAttribute("href", "/student/practice");
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  await expect(page.getByRole("radio")).toHaveCount(0);
  await expect(page.getByRole("button", { name: SUBMIT })).toHaveCount(0);
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Put your knowledge to work.",
    }),
  ).toBeVisible();
  const text = await page.locator("body").innerText();
  expect(text).not.toContain("set_not_found");
  expect(text).not.toMatch(/\b404\b/);
  expect(mock.count("getSet")).toBe(1);
  expect(mock.count("start")).toBe(0);
});

for (const bad of [
  "intro-se-1",
  "not-a-uuid",
  "a%2Fb",
  "%20",
  "..%2F..%2Fcourses",
]) {
  test(`stu02ps AC16 a set id that is not a UUID (${bad}) shows the same not-available message after one request`, async ({
    page,
  }) => {
    const { mock } = await openSet(page, {}, `/student/practice/${bad}`);
    await expect(alertWith(page, NOT_AVAILABLE)).toBeVisible();
    await expect(backLink(page)).toBeVisible();
    await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(
      0,
    );
    await expect(page.getByText("validation_error")).toHaveCount(0);
    await expect(page.getByText("A valid UUID is required.")).toHaveCount(0);
    expect(mock.count("getSet")).toBeLessThanOrEqual(1);
  });
}

test("stu02ps AC16 a set the server refuses is never shown: nothing of an earlier set or its answers stays", async ({
  page,
}) => {
  const { mock } = await openSet(page, {
    replies: { getSet: [apiError(404, "set_not_found")] },
  });
  await expect(alertWith(page, NOT_AVAILABLE)).toBeVisible();
  await expect(page.getByText(FIXTURE_SET.title)).toHaveCount(0);
  await expect(page.getByText(FIXTURE_SET.questions[0].text)).toHaveCount(0);
  expect(mock.count("getSet")).toBe(1);
});

test("stu02ps AC16 403 forbidden on load: the access message and no Try again", async ({
  page,
}) => {
  await openSet(page, { replies: { getSet: [apiError(403, "forbidden")] } });
  await expect(alertWith(page, FORBIDDEN)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  await expect(page.getByRole("radio")).toHaveCount(0);
});

// ------------------------------------------------------------------ load failures keep the old message
for (const [label, reply] of [
  ["network failure", { abort: true }],
  ["HTTP 500", { status: 500, body: "Traceback SECRET_TRACE_MARKER" }],
  [
    "HTTP 503",
    {
      status: 503,
      json: { detail: { code: "service_unavailable", message: "x" } },
    },
  ],
  [
    "a response of the wrong shape",
    { json: { id: SET_ID, title: 42, questions: "nope" } },
  ],
] as const) {
  test(`stu02ps AC16 ${label} on load: the load-failure message with Try again that repeats only the set request`, async ({
    page,
  }) => {
    const { mock } = await openSet(page, { replies: { getSet: [reply] } });
    await expect(alertWith(page, LOAD_FAILED)).toBeVisible();
    await expect(page.getByText(NOT_AVAILABLE)).toHaveCount(0);
    await expect(page.getByText(NO_LONGER)).toHaveCount(0);
    const text = await page.locator("body").innerText();
    expect(text).not.toContain("SECRET_TRACE_MARKER");
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(radio(page, "q1", "a")).toBeVisible();
    expect(mock.count("getSet")).toBe(2);
    expect(mock.count("start")).toBe(0);
    await expect(page).toHaveURL(new RegExp(`/student/practice/${SET_ID}$`));
  });
}

test("stu02ps AC16 timeout on load: no error before 10 seconds, the load-failure message after", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  const mock = await mockPracticeApi(page, {
    auth,
    replies: { getSet: [{ hang: true }] },
  });
  await page.clock.install();
  await page.goto(`/student/practice/${SET_ID}`);
  await expect.poll(() => mock.count("getSet")).toBe(1);
  await page.clock.fastForward(9_000);
  await expect(page.getByText(LOAD_FAILED)).toHaveCount(0);
  await page.clock.fastForward(2_000);
  await expect(alertWith(page, LOAD_FAILED)).toBeVisible();
  mock.release();
});

test("stu02ps AC16 401 while signed in goes to /login", async ({ page }) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  await mockPracticeApi(page, { auth });
  auth.script("me", { json: { user: STUDENT, csrf_token: auth.csrf } });
  auth.expire();
  await page.goto(`/student/practice/${SET_ID}`);
  await expect(page).toHaveURL(/\/login$/);
});

test("stu02ps AC16 401 in demo mode shows the sign-in notice and no set", async ({
  page,
}) => {
  await openSet(page, {}, `/student/practice/${SET_ID}`, null);
  await expect(page.getByText(NOTICE).first()).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Go to sign in" }).first(),
  ).toHaveAttribute("href", "/login");
  await expect(page.getByRole("radio")).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/student/practice/${SET_ID}$`));
});

// ------------------------------------------------------------------ later 404 set_not_found
for (const step of ["start", "save", "submit", "results"] as const) {
  test(`stu02ps AC16 404 set_not_found at the ${step} step: the no-longer-available alert, link, nothing kept, no retry`, async ({
    page,
  }) => {
    const { mock } = await openSet(page, {
      replies: { [step]: [apiError(404, "set_not_found")] },
    });
    await pickAll(page);
    await page.getByRole("button", { name: SUBMIT }).click();
    await expect(alertWith(page, NO_LONGER)).toBeVisible();
    await expect(backLink(page)).toHaveAttribute("href", "/student/practice");
    await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(
      0,
    );
    await expect(page.getByRole("radio")).toHaveCount(0);
    await expect(page.getByRole("button", { name: SUBMIT })).toHaveCount(0);
    await expect(page.getByText("Correct answer:")).toHaveCount(0);
    await expect(page.getByText(FIXTURE_SET.questions[0].text)).toHaveCount(0);
    expect(mock.count(step)).toBe(1);
    expect(mock.count("getSet")).toBe(1);
    await expect(page.getByText(NOT_AVAILABLE)).toHaveCount(0);
    await expect(page.getByText(LOAD_FAILED)).toHaveCount(0);
  });
}

test("stu02ps AC16 404 set_not_found after a successful submit removes the results too", async ({
  page,
}) => {
  await openSet(page, {
    replies: { results: [apiError(404, "set_not_found")] },
  });
  await pickAll(page);
  await page.getByRole("button", { name: SUBMIT }).click();
  await expect(alertWith(page, NO_LONGER)).toBeVisible();
  await expect(page.getByText(/\d \/ 3 — /)).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Start another attempt" }),
  ).toHaveCount(0);
});

// ------------------------------------------------------------------ links and history
test("stu02ps AC16 Back to practice sets pushes /student/practice and Back returns to the set page", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  const mock = await mockPracticeApi(page, {
    auth,
    catalog: { courses: [catalogCourse("SE", [catalogSet()])] },
  });
  await page.goto(`/student/practice/${UNKNOWN_SET_ID}`);
  await expect(alertWith(page, NOT_AVAILABLE)).toBeVisible();
  await backLink(page).click();
  await expect(page).toHaveURL(/\/student\/practice$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Choose a practice set" }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(
    new RegExp(`/student/practice/${UNKNOWN_SET_ID}$`),
  );
  expect(mock.count("catalog")).toBe(1);
});

test("stu02ps AC16 Try again and Start another attempt do not change the URL", async ({
  page,
}) => {
  await openSet(page, { replies: { getSet: [{ abort: true }] } });
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(radio(page, "q1", "a")).toBeVisible();
  const url = page.url();
  await pickAll(page);
  await page.getByRole("button", { name: SUBMIT }).click();
  await expect(page.getByText("Correct answer:").first()).toBeVisible();
  await page.getByRole("button", { name: "Start another attempt" }).click();
  await expect(radio(page, "q1", "a")).not.toBeChecked();
  expect(page.url()).toBe(url);
});

// ------------------------------------------------------------------ refresh, Back and Forward
test("stu02ps AC16 refresh reloads the set: loading, then a fresh empty form and no new attempt", async ({
  page,
}) => {
  const { mock } = await openSet(page);
  await radio(page, "q1", "a").check();
  await expect(page.getByText("1 of 3 answered")).toBeVisible();
  await page.reload();
  await expect(radio(page, "q1", "a")).toBeVisible();
  await expect(radio(page, "q1", "a")).not.toBeChecked();
  await expect(page.getByText("0 of 3 answered")).toBeVisible();
  expect(mock.count("getSet")).toBe(2);
  expect(mock.count("start")).toBe(0);
});

test("stu02ps AC16 Back to the same set keeps the chosen answers without a new request", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  const mock = await mockPracticeApi(page, {
    auth,
    catalog: { courses: [catalogCourse("SE", [catalogSet()])] },
  });
  await page.goto(`/student/practice/${SET_ID}`);
  await radio(page, "q1", "a").check();
  await page
    .getByRole("link", { name: "Practice", exact: true })
    .first()
    .click();
  await expect(page).toHaveURL(/\/student\/practice$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Choose a practice set" }),
  ).toBeVisible();
  await page.goBack();
  await expect(radio(page, "q1", "a")).toBeChecked();
  expect(mock.count("getSet")).toBe(1);
  await page.goForward();
  await page.goBack();
  await expect(radio(page, "q1", "a")).toBeChecked();
  expect(mock.count("getSet")).toBe(1);
});

test("stu02ps AC16 opening a different set id resets the state and loads the new set with one request", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  const mock = await mockPracticeApi(page, {
    auth,
    catalog: {
      courses: [
        catalogCourse("SE", [
          catalogSet(),
          catalogSet({ id: OTHER_SET, title: "Other set" }),
        ]),
      ],
    },
  });
  await page.goto(`/student/practice/${SET_ID}`);
  await radio(page, "q1", "a").check();
  await page
    .getByRole("link", { name: "Practice", exact: true })
    .first()
    .click();
  await page.getByRole("link", { name: "Other set", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/student/practice/${OTHER_SET}$`));
  await expect(alertWith(page, NOT_AVAILABLE)).toBeVisible();
  expect(
    mock.of("getSet").filter((r) => r.path.endsWith(OTHER_SET)),
  ).toHaveLength(1);
  await page.goBack();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/student/practice/${SET_ID}$`));
  await expect(radio(page, "q1", "a")).toBeVisible();
  await expect(radio(page, "q1", "a")).not.toBeChecked();
  await expect(page.getByText(NOT_AVAILABLE)).toHaveCount(0);
});

// ------------------------------------------------------------------ wrong role, companion, layout
for (const [label, user, home] of [
  ["teacher", TEACHER, "/teacher/overview"],
  ["admin", ADMIN, "/admin/analytics"],
] as const) {
  test(`stu02ps AC16 wrong role: a ${label} opening a set is redirected before any request`, async ({
    page,
  }) => {
    const { mock } = await openSet(
      page,
      {},
      `/student/practice/${SET_ID}`,
      user,
    );
    await expect(page).toHaveURL(new RegExp(`${home}$`));
    expect(mock.requests).toHaveLength(0);
    await expect(page.getByRole("radio")).toHaveCount(0);
  });
}

test("stu02ps AC16 a stale session after a set was shown leaves no questions or answers on screen", async ({
  page,
}) => {
  const { auth } = await openSet(page);
  await pickAll(page);
  auth.expire();
  await page.getByRole("button", { name: SUBMIT }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText(FIXTURE_SET.questions[0].text)).toHaveCount(0);
  await expect(page.getByText("Correct answer:")).toHaveCount(0);
});

for (const width of [390, 1440]) {
  for (const theme of ["light", "dark"] as const) {
    test(`stu02ps AC16 the set page and its not-available state fit ${width}px wide in ${theme} theme`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: theme });
      await openSet(page);
      await expect(radio(page, "q1", "a")).toBeVisible();
      const fits = () =>
        page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
      expect(await fits()).toBe(true);
      await page.goto(`/student/practice/${UNKNOWN_SET_ID}`);
      await expect(alertWith(page, NOT_AVAILABLE)).toBeVisible();
      expect(await fits()).toBe(true);
    });
  }
}

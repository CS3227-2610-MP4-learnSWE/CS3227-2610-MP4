import { test, expect, type Page } from "@playwright/test";
import { ADMIN, NOTICE, STUDENT, TEACHER, mockAuthApi } from "./authApi";
import {
  SET_ID,
  apiError,
  catalogCourse,
  catalogSet,
  mockPracticeApi,
  type Catalog,
  type MockOptions,
} from "./practiceApi";
import { mockCompanionApi } from "./companionApi";

/**
 * STU-02-published-sets AC14, AC15: the practice set picker `/student/practice`.
 * Every state, exact copy and accessible role/name of the spec's "UI states and copy" and the plan's
 * "UI contract". The picker makes exactly one request, `GET /api/practice-sets`.
 */

const MSG = {
  offline: "Could not reach the server. Check your connection and try again.",
  unavailable: "Practice sets are unavailable right now. Please try again.",
  badShape: "Practice sets could not be read. Please try again.",
  forbidden: "You do not have access to practice.",
  signIn: "Sign in to see your practice sets.",
  loading: "Loading practice sets…",
  joinHeading: "Join a course to start",
  joinText:
    "You are not enrolled in any course yet. Ask your teacher or an administrator to add you, and practice sets will appear here.",
  noSets: "No practice sets published in this course yet.",
} as const;

const SET_B = "b1111111-1111-4111-8111-111111111111";
const SET_C = "c2222222-2222-4222-8222-222222222222";
const COURSE_2 = "22222222-2222-4222-8222-222222222222";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const h1 = (page: Page) =>
  page.getByRole("heading", { level: 1, name: "Choose a practice set" });
const alertWith = (page: Page, text: string) =>
  page.getByRole("alert").filter({ hasText: text });

function twoCourses(): Catalog {
  return {
    courses: [
      catalogCourse(
        "Algorithms",
        [
          catalogSet({
            id: SET_B,
            title: "Sorting drill",
            topic: {
              id: "33333333-3333-4333-8333-333333333333",
              name: "Sorting",
            },
            best: { correct: 2, total: 3 },
          }),
        ],
        COURSE_2,
      ),
      catalogCourse("Software Engineering", [
        catalogSet({
          id: SET_ID,
          title: "Testing basics",
          topic: {
            id: "44444444-4444-4444-8444-444444444444",
            name: "Testing",
          },
          best: { correct: 3, total: 3 },
        }),
        catalogSet({ id: SET_C, title: "Never tried", best: null }),
      ]),
    ],
  };
}

async function openPicker(
  page: Page,
  options: MockOptions = {},
  user: typeof STUDENT | null = STUDENT,
) {
  const auth = await mockAuthApi(page, { user });
  const mock = await mockPracticeApi(page, { auth, ...options });
  await page.goto("/student/practice");
  return { auth, mock };
}

/** Every /api request except auth and health, in order. */
function recordApi(page: Page) {
  const seen: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (
      url.pathname.startsWith("/api/") &&
      !url.pathname.startsWith("/api/auth/") &&
      url.pathname !== "/api/health"
    )
      seen.push(`${request.method()} ${url.pathname}`);
  });
  return seen;
}

// ------------------------------------------------------------------ structure and success
test("stu02ps AC15 heading level 1, eyebrow, description and the sidebar link Practice", async ({
  page,
}) => {
  await openPicker(page, { catalog: twoCourses() });
  await expect(h1(page)).toBeVisible();
  await expect(page.getByText("UNDERSTAND IT. THEN TRY IT.")).toBeVisible();
  await expect(
    page.getByText(
      "Pick a set your teacher has published for one of your courses.",
    ),
  ).toBeVisible();
  const link = page
    .getByRole("navigation", { name: "student navigation" })
    .getByRole("link", { name: "Practice", exact: true });
  await expect(link).toHaveAttribute("href", "/student/practice");
});

test("stu02ps AC15 courses are regions with a level 2 heading, sets are links in a named list", async ({
  page,
}) => {
  await openPicker(page, { catalog: twoCourses() });
  const algo = page.getByRole("region", { name: "Algorithms", exact: true });
  await expect(algo).toBeVisible();
  await expect(
    algo.getByRole("heading", { level: 2, name: "Algorithms", exact: true }),
  ).toBeVisible();
  const se = page.getByRole("region", {
    name: "Software Engineering",
    exact: true,
  });
  await expect(
    se.getByRole("heading", {
      level: 2,
      name: "Software Engineering",
      exact: true,
    }),
  ).toBeVisible();
  const list = se.getByRole("list", {
    name: "Practice sets in Software Engineering",
  });
  await expect(list.getByRole("listitem")).toHaveCount(2);
  const first = list.getByRole("listitem").nth(0);
  await expect(
    first
      .getByRole("heading", { level: 3 })
      .getByRole("link", { name: "Testing basics", exact: true }),
  ).toHaveAttribute("href", `/student/practice/${SET_ID}`);
  await expect(
    first.getByText("Topic: Testing", { exact: true }),
  ).toBeVisible();
  await expect(
    first.getByText("Best score: 3 / 3", { exact: true }),
  ).toBeVisible();
  const second = list.getByRole("listitem").nth(1);
  await expect(
    second.getByRole("link", { name: "Never tried", exact: true }),
  ).toHaveAttribute("href", `/student/practice/${SET_C}`);
  await expect(
    second.getByText("No attempts yet", { exact: true }),
  ).toBeVisible();
  await expect(
    algo.getByText("Best score: 2 / 3", { exact: true }),
  ).toBeVisible();
});

test("stu02ps AC15 courses and sets appear in the order the server sent them", async ({
  page,
}) => {
  await openPicker(page, { catalog: twoCourses() });
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  const headings = await page
    .getByRole("heading", { level: 2 })
    .allInnerTexts();
  expect(headings.indexOf("Algorithms")).toBeGreaterThan(-1);
  expect(headings.indexOf("Algorithms")).toBeLessThan(
    headings.indexOf("Software Engineering"),
  );
  const links = await page
    .getByRole("region", { name: "Software Engineering" })
    .getByRole("link")
    .allInnerTexts();
  expect(links).toEqual(["Testing basics", "Never tried"]);
});

test("stu02ps AC15 a member course with no sets shows the empty text and no list", async ({
  page,
}) => {
  await openPicker(page, {
    catalog: { courses: [catalogCourse("Empty course", [], COURSE_2)] },
  });
  const region = page.getByRole("region", {
    name: "Empty course",
    exact: true,
  });
  await expect(region.getByText(MSG.noSets, { exact: true })).toBeVisible();
  await expect(region.getByRole("list")).toHaveCount(0);
  await expect(region.getByRole("link")).toHaveCount(0);
});

test("stu02ps AC15 no courses: the join heading and text", async ({ page }) => {
  await openPicker(page, { catalog: { courses: [] } });
  await expect(h1(page)).toBeVisible();
  await expect(
    page.getByRole("heading", { level: 3, name: MSG.joinHeading }),
  ).toBeVisible();
  await expect(page.getByText(MSG.joinText, { exact: true })).toBeVisible();
  await expect(page.getByRole("region")).toHaveCount(0);
});

test("stu02ps AC15 loading: the status shows with the heading and no list, then the list", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  const mock = await mockPracticeApi(page, {
    auth,
    catalog: twoCourses(),
    replies: { catalog: [{ passThrough: true, delayMs: 800 }] },
  });
  await page.goto("/student/practice");
  await expect(
    page.getByRole("status").filter({ hasText: MSG.loading }),
  ).toBeVisible();
  await expect(h1(page)).toBeVisible();
  await expect(page.getByRole("link", { name: "Testing basics" })).toHaveCount(
    0,
  );
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: MSG.loading }),
  ).toHaveCount(0);
  expect(mock.count("catalog")).toBe(1);
});

// ------------------------------------------------------------------ requests
test("stu02ps AC15 one GET /api/practice-sets on load and nothing else (no study courses, no progress)", async ({
  page,
}) => {
  const seen = recordApi(page);
  const { mock } = await openPicker(page, { catalog: twoCourses() });
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(seen.filter((s) => s.includes("/api/practice-sets"))).toEqual([
    "GET /api/practice-sets",
  ]);
  // The shell's inbox badge (ADM-04) adds one GET /api/messaging/unread-count; the picker itself
  // sends exactly one request and nothing else.
  expect(
    seen.filter((s) => !s.includes("/api/messaging/unread-count")),
  ).toEqual(["GET /api/practice-sets"]);
  expect(mock.count("catalog")).toBe(1);
});

test("stu02ps AC15 the response is not sent with identity headers or query parameters", async ({
  page,
}) => {
  const { mock } = await openPicker(page, { catalog: twoCourses() });
  await expect(h1(page)).toBeVisible();
  const r = mock.of("catalog")[0];
  expect(r.path).toBe("/api/practice-sets");
  expect(r.headers["x-student-id"]).toBeUndefined();
});

// ------------------------------------------------------------------ failures
test("stu02ps AC15 backend unreachable: offline message in an alert with Try again; retry loads and replaces it", async ({
  page,
}) => {
  const { mock } = await openPicker(page, {
    catalog: twoCourses(),
    replies: { catalog: [{ abort: true }] },
  });
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await expect(h1(page)).toBeVisible();
  await expect(page.getByRole("link", { name: "Testing basics" })).toHaveCount(
    0,
  );
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(mock.count("catalog")).toBe(2);
  await expect(page).toHaveURL(/\/student\/practice$/);
});

test("stu02ps AC15 timeout: no error before 10 seconds, the offline message after", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  const mock = await mockPracticeApi(page, {
    auth,
    replies: { catalog: [{ hang: true }] },
  });
  await page.clock.install();
  await page.goto("/student/practice");
  await expect.poll(() => mock.count("catalog")).toBe(1);
  await page.clock.fastForward(9_000);
  await expect(page.getByText(MSG.offline)).toHaveCount(0);
  await expect(page.getByText(MSG.loading)).toBeVisible();
  await page.clock.fastForward(2_000);
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  mock.release();
});

for (const status of [500, 503]) {
  test(`stu02ps AC15 HTTP ${status}: the unavailable message, no raw body, Try again`, async ({
    page,
  }) => {
    const body =
      status === 503
        ? {
            json: {
              detail: {
                code: "service_unavailable",
                message: "The service is unavailable.",
              },
            },
          }
        : { body: "Traceback SECRET_TRACE_MARKER" };
    await openPicker(page, { replies: { catalog: [{ status, ...body }] } });
    await expect(alertWith(page, MSG.unavailable)).toBeVisible();
    await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
    const text = await page.locator("body").innerText();
    expect(text).not.toContain("SECRET_TRACE_MARKER");
    expect(text).not.toContain("The service is unavailable.");
    expect(text).not.toMatch(new RegExp(`\\b${status}\\b`));
    await expect(page.getByText(MSG.offline)).toHaveCount(0);
  });
}

for (const [label, json] of [
  ["courses is not a list", { courses: "nope" }],
  [
    "a set has no title",
    {
      courses: [
        catalogCourse("C", [{ ...catalogSet(), title: undefined } as never]),
      ],
    },
  ],
  [
    "best has the wrong shape",
    {
      courses: [
        catalogCourse("C", [{ ...catalogSet(), best: "2/3" } as never]),
      ],
    },
  ],
  ["a bare array", [catalogCourse("C", [catalogSet()])]],
  ["null", null],
] as const) {
  test(`stu02ps AC15 200 with a wrong shape (${label}): the could-not-be-read message, never the offline one`, async ({
    page,
  }) => {
    await openPicker(page, { replies: { catalog: [{ json }] } });
    await expect(alertWith(page, MSG.badShape)).toBeVisible();
    await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
    await expect(page.getByText(MSG.offline)).toHaveCount(0);
  });
}

test("stu02ps AC15 403 forbidden: the access message and no Try again", async ({
  page,
}) => {
  await openPicker(page, {
    replies: { catalog: [apiError(403, "forbidden")] },
  });
  await expect(alertWith(page, MSG.forbidden)).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  const text = await page.locator("body").innerText();
  expect(text).not.toContain("Server says");
});

test("stu02ps AC15 401 while signed in goes to /login and shows no message", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  await mockPracticeApi(page, { auth, catalog: twoCourses() });
  auth.script("me", { json: { user: STUDENT, csrf_token: auth.csrf } });
  auth.expire();
  await page.goto("/student/practice");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText("Testing basics")).toHaveCount(0);
});

test("stu02ps AC15 401 in demo mode: the sign-in notice with a Go to sign in link, no redirect", async ({
  page,
}) => {
  const { mock } = await openPicker(page, { catalog: twoCourses() }, null);
  await expect(page.getByText(MSG.signIn).first()).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Go to sign in" }).first(),
  ).toHaveAttribute("href", "/login");
  await expect(page).toHaveURL(/\/student\/practice$/);
  await expect(page.getByText("Testing basics")).toHaveCount(0);
  expect(mock.count("catalog")).toBe(1);
  await expect(page.getByText(NOTICE)).toHaveCount(0);
});

test("stu02ps AC15 a failed retry replaces the message and shows no list from an earlier load", async ({
  page,
}) => {
  const { mock } = await openPicker(page, {
    catalog: twoCourses(),
    replies: {
      catalog: [
        { passThrough: true },
        { abort: true },
        { status: 503, json: {} },
      ],
    },
  });
  await page.getByRole("link", { name: "Testing basics" }).click();
  await expect(page).toHaveURL(new RegExp(`/student/practice/${SET_ID}$`));
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Put your knowledge to work.",
    }),
  ).toBeVisible();
  await page.goBack();
  await expect(alertWith(page, MSG.offline)).toBeVisible();
  await expect(page.getByRole("link", { name: "Testing basics" })).toHaveCount(
    0,
  );
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(alertWith(page, MSG.unavailable)).toBeVisible();
  await expect(page.getByText(MSG.offline)).toHaveCount(0);
  expect(mock.count("catalog")).toBe(3);
});

// ------------------------------------------------------------------ wrong role, history, refresh
for (const [label, user, home] of [
  ["teacher", TEACHER, "/teacher/overview"],
  ["admin", ADMIN, "/admin/overview"],
] as const) {
  for (const path of ["/student/practice", `/student/practice/${SET_ID}`]) {
    test(`stu02ps AC15 wrong role: a ${label} opening ${path === "/student/practice" ? "the picker" : "a set"} is redirected before any request`, async ({
      page,
    }) => {
      const seen = recordApi(page);
      const auth = await mockAuthApi(page, { user });
      const mock = await mockPracticeApi(page, { auth, catalog: twoCourses() });
      await page.goto(path);
      await expect(page).toHaveURL(new RegExp(`${home}$`));
      expect(mock.requests).toHaveLength(0);
      expect(seen.filter((s) => s.includes("practice-sets"))).toEqual([]);
      await expect(page.getByText("Testing basics")).toHaveCount(0);
    });
  }
}

test("stu02ps AC15 a set link pushes a history entry; Back returns to the picker and re-requests it", async ({
  page,
}) => {
  const { mock } = await openPicker(page, { catalog: twoCourses() });
  await page.getByRole("link", { name: "Testing basics" }).click();
  await expect(page).toHaveURL(new RegExp(`/student/practice/${SET_ID}$`));
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Put your knowledge to work.",
    }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/\/student\/practice$/);
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  expect(mock.count("catalog")).toBe(2);
  await page.goForward();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Put your knowledge to work.",
    }),
  ).toBeVisible();
  await page.goBack();
  await expect.poll(() => mock.count("catalog")).toBe(3);
});

test("stu02ps AC15 refresh reloads the picker from the server", async ({
  page,
}) => {
  const { mock } = await openPicker(page, { catalog: twoCourses() });
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  expect(mock.count("catalog")).toBe(2);
});

test("stu02ps AC15 Try again with the keyboard: Tab to the button and Enter", async ({
  page,
}) => {
  const { mock } = await openPicker(page, {
    catalog: twoCourses(),
    replies: { catalog: [{ abort: true }] },
  });
  const retry = page.getByRole("button", { name: "Try again" });
  await expect(retry).toBeVisible();
  await retry.focus();
  await expect(retry).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  expect(mock.count("catalog")).toBe(2);
});

test("stu02ps AC15 after the session ends, Back shows no practice data", async ({
  page,
}) => {
  const { auth, mock } = await openPicker(page, { catalog: twoCourses() });
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Testing basics" }).click();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Put your knowledge to work.",
    }),
  ).toBeVisible();
  await expect.poll(() => mock.count("getSet")).toBe(1);
  auth.expire();
  await page.goBack();
  await expect(page.getByText("Testing basics")).toHaveCount(0);
  await expect(page.getByText("Sorting drill")).toHaveCount(0);
  expect(mock.count("catalog")).toBeGreaterThanOrEqual(2);
});

// ------------------------------------------------------------------ safe rendering, storage, companion, layout
test("stu02ps AC15 titles, topics and course names are plain text, not HTML", async ({
  page,
}) => {
  const evil =
    '<img src=x onerror="window.__xss=1"> <b>bold</b> https://example.com/x';
  await openPicker(page, {
    catalog: {
      courses: [
        catalogCourse(evil, [
          catalogSet({ title: evil, topic: { id: "t", name: evil } }),
        ]),
      ],
    },
  });
  await expect(
    page.getByRole("link", { name: evil, exact: true }),
  ).toBeVisible();
  await expect(page.locator("main img, main b")).toHaveCount(0);
  expect(
    await page.evaluate(() => (window as unknown as { __xss?: number }).__xss),
  ).toBeUndefined();
});

test("stu02ps AC15 nothing of the list is kept in browser storage", async ({
  page,
}) => {
  await openPicker(page, { catalog: twoCourses() });
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  const stored = await page.evaluate(() =>
    JSON.stringify([
      Object.entries(localStorage),
      Object.entries(sessionStorage),
      document.cookie,
    ]),
  );
  expect(stored).not.toContain("Testing basics");
  expect(stored).not.toContain(SET_ID);
});

test("stu02ps AC15 the companion on the picker reports page other with no set or attempt", async ({
  page,
}) => {
  const companion = await mockCompanionApi(page);
  await openPicker(page, { catalog: twoCourses() });
  await expect(
    page.getByRole("link", { name: "Testing basics" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open study companion" }).click();
  await page
    .getByLabel("Message your study companion")
    .fill("What is a unit test?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect.poll(() => companion.count).toBe(1);
  const ctx = companion.requests[0].body.context;
  expect(ctx.page).toBe("other");
  expect(ctx.set_id ?? null).toBeNull();
  expect(ctx.attempt_id ?? null).toBeNull();
});

for (const width of [390, 1440]) {
  for (const theme of ["light", "dark"] as const) {
    test(`stu02ps AC15 the picker fits ${width}px wide in ${theme} theme`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: theme });
      const long =
        "A very long practice set title that must wrap inside the panel and not widen the page at all";
      await openPicker(page, {
        catalog: {
          courses: [
            catalogCourse("Course " + long, [
              catalogSet({
                title: long,
                topic: { id: "t", name: "Topic " + long },
              }),
            ]),
          ],
        },
      });
      await expect(
        page.getByRole("link", { name: long, exact: true }),
      ).toBeVisible();
      const m = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        width: innerWidth,
      }));
      expect(m.scroll).toBeLessThanOrEqual(m.width);
    });
  }
}

import { test, expect } from "@playwright/test";
import {
  ADMIN,
  DEMO_HEADING,
  PASSWORD,
  STUDENT,
  TEACHER,
  authError,
  browserState,
  emailField,
  exploreDemoLink,
  mockAuthApi,
  passwordField,
} from "./authApi";

/**
 * SHR-01 AC22 and AC25: the route guard (RequireRole), the auth state (AuthContext), logout and
 * demo-mode coexistence. The guard is UX only; the server is the control (backend tests).
 * Flag-off behaviour (VITE_ENABLE_DEMO_ACCESS=false) is in auth-demo-off.spec.ts.
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const ROLE_ROUTES = [
  "/student/overview",
  "/teacher/overview",
  "/admin/overview",
];

// ---------------------------------------------------------------- AuthContext
test("shr01 AuthContext asks /api/auth/me exactly once on mount and not on in-app navigation", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  await page.goto("/student/overview");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.getByRole("link", { name: "Practice", exact: true }).click();
  await expect(page).toHaveURL(/\/student\/practice$/);
  expect(auth.count("me")).toBe(1);
});

test("shr01 AuthContext treats a 401 from /api/auth/me as anonymous, not as an error", async ({
  page,
}) => {
  await mockAuthApi(page, { user: null });
  await page.goto("/student/overview");
  await expect(page.getByText("Demo (not signed in)").first()).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

for (const [name, reply] of [
  ["a network failure", { abort: true }],
  ["a 500 with an HTML body", { status: 500 }],
  ["a 503", authError(503, "service_unavailable")],
] as const) {
  test(`shr01 AC25 ${name} on /api/auth/me leaves the visitor in demo mode (teacher specs have no auth mock)`, async ({
    page,
  }) => {
    const auth = await mockAuthApi(page, { user: null });
    auth.script("me", reply as never);
    await page.goto("/teacher/overview");
    await expect(page).toHaveURL(/\/teacher\/overview$/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByText("Demo (not signed in)").first()).toBeVisible();
  });
}

// ---------------------------------------------------------------- RequireRole, loading
test("shr01 AC22 while the session check is pending a loading status shows and nothing protected renders", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  auth.script("me", { hold: true });
  await page.goto("/student/overview");
  await expect(
    page.getByRole("status").filter({ hasText: /loading/i }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveCount(0);
  await expect(page.getByText("Sam Student")).toHaveCount(0);
  await expect(page.getByText("Demo (not signed in)")).toHaveCount(0);
  auth.release();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText("Sam Student").first()).toBeVisible();
});

test("shr01 AC22 a pending session check never flashes the demo shell for a signed-in user", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: TEACHER });
  auth.script("me", { hold: true });
  await page.goto("/teacher/overview");
  await page.waitForTimeout(300);
  await expect(page.getByText("Demo (not signed in)")).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: "Demo role" })).toHaveCount(
    0,
  );
  auth.release();
  await expect(page.getByText("Tess Teacher").first()).toBeVisible();
});

// ---------------------------------------------------------------- RequireRole, authenticated
for (const [user, own] of [
  [STUDENT, "/student/overview"],
  [TEACHER, "/teacher/overview"],
  [ADMIN, "/admin/overview"],
] as const) {
  test(`shr01 AC22 a signed-in ${user.role} renders their own area and is sent home from the others`, async ({
    page,
  }) => {
    await mockAuthApi(page, { user });
    await page.goto(own);
    await expect(page).toHaveURL(new RegExp(`${own}$`));
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    for (const other of ROLE_ROUTES.filter((r) => r !== own)) {
      await page.goto(other);
      await expect(page).toHaveURL(new RegExp(`${own}$`));
    }
  });
}

test("shr01 AC22 wrong-role redirect applies to deep links too", async ({
  page,
}) => {
  await mockAuthApi(page, { user: STUDENT });
  await page.goto("/teacher/materials");
  await expect(page).toHaveURL(/\/student\/overview$/);
  await page.goto("/admin/users");
  await expect(page).toHaveURL(/\/student\/overview$/);
});

test("shr01 AC25 an authenticated user sees the real name and role, a Log out button and no demo switcher", async ({
  page,
}) => {
  await mockAuthApi(page, { user: STUDENT });
  await page.goto("/student/overview");
  await expect(page.getByText("Sam Student").first()).toBeVisible();
  await expect(page.getByText(/student/i).first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: /log out/i }).first(),
  ).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Demo role" })).toHaveCount(
    0,
  );
  await expect(page.getByText("Demo (not signed in)")).toHaveCount(0);
});

test("shr01 AC22 the root path sends signed-in users home and others to /login", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: TEACHER });
  await page.goto("/");
  await expect(page).toHaveURL(/\/teacher\/overview$/);
  auth.expire();
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
});

// ---------------------------------------------------------------- demo mode (AC25)
test("shr01 AC25 anonymous visitors still reach every role area in labelled demo mode", async ({
  page,
}) => {
  await mockAuthApi(page, { user: null });
  for (const route of ROLE_ROUTES) {
    await page.goto(route);
    await expect(page).toHaveURL(new RegExp(`${route}$`));
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByText("Demo (not signed in)").first()).toBeVisible();
    await expect(page.getByText("Demo · Sample data").first()).toBeVisible();
    await expect(
      page.getByRole("combobox", { name: "Demo role" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: /log out/i })).toHaveCount(0);
  }
});

test("shr01 AC25 the Demo role switcher still switches areas in demo mode", async ({
  page,
}) => {
  await mockAuthApi(page, { user: null });
  await page.goto("/student/overview");
  await page.getByRole("combobox", { name: "Demo role" }).click();
  await page.getByRole("option", { name: "Teacher", exact: true }).click();
  await expect(page).toHaveURL(/\/teacher\//);
  await expect(page.getByText("Demo (not signed in)").first()).toBeVisible();
});

test("shr01 AC25 the Explore demo buttons enter demo mode without any sign-in request", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await expect(page.getByText(DEMO_HEADING)).toBeVisible();
  await (await exploreDemoLink(page, "admin")).click();
  await expect(page).toHaveURL(/\/admin\/overview$/);
  await expect(page.getByText("Demo (not signed in)").first()).toBeVisible();
  expect(auth.count("login")).toBe(0);
  expect(auth.count("signup")).toBe(0);
  expect(auth.count("logout")).toBe(0);
});

test("shr01 AC25 demo mode creates no cookie and no browser storage entry", async ({
  page,
  context,
}) => {
  await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await (await exploreDemoLink(page, "student")).click();
  await expect(page).toHaveURL(/\/student\/overview$/);
  await page.getByRole("combobox", { name: "Demo role" }).click();
  await page.getByRole("option", { name: "Teacher", exact: true }).click();
  expect(await context.cookies()).toEqual([]);
  expect(await browserState(page)).toEqual({
    local: [],
    session: [],
    cookie: "",
  });
});

test("shr01 AC25 demo mode sends no X-Student-Id and no credentials on any API call", async ({
  page,
}) => {
  const seen: Record<string, string>[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api/"))
      seen.push(request.headers());
  });
  await mockAuthApi(page, { user: null });
  await page.goto("/student/practice");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  for (const headers of seen) {
    expect(headers["x-student-id"]).toBeUndefined();
    expect(headers["authorization"]).toBeUndefined();
  }
});

// ---------------------------------------------------------------- logout
test("shr01 AC22 logout posts with the CSRF token, clears client state and returns to /login", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  await page.goto("/student/overview");
  await page
    .getByRole("button", { name: /log out/i })
    .first()
    .click();
  await expect(page).toHaveURL(/\/login$/);
  expect(auth.count("logout")).toBe(1);
  expect(auth.of("logout")[0].headers["x-csrf-token"]).toBe(auth.csrf);
  expect(auth.user).toBeNull();
  await expect(page.getByText("Sam Student")).toHaveCount(0);
});

test("shr01 AC22 after logout the back button does not show the signed-in area", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  await page.goto("/student/overview");
  await page
    .getByRole("button", { name: /log out/i })
    .first()
    .click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goBack();
  // Either the login page or the labelled demo mode (flag unset): never the signed-in shell.
  await expect(page.getByText("Sam Student")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /log out/i })).toHaveCount(0);
  expect(auth.user).toBeNull();
});

for (const [label, failure] of [
  ["a network error", { abort: true }],
  ["a 503", authError(503, "service_unavailable")],
] as const) {
  test(`shr01 AC22 a failed logout (${label}) keeps the user signed in, shows an alert, and a retry signs out`, async ({
    page,
  }) => {
    const auth = await mockAuthApi(page, { user: STUDENT });
    auth.script("logout", failure);
    await page.goto("/student/overview");
    const logout = page.getByRole("button", { name: /log out/i }).first();
    await logout.click();
    await expect(page.getByRole("alert")).toContainText(/could not log out/i);
    await expect(page).toHaveURL(/\/student\/overview$/);
    await expect(page.getByText("Sam Student").first()).toBeVisible();
    expect(auth.user).not.toBeNull(); // the server session is still alive, so the UI must say so
    // The server recovers: a second click retries and signs out.
    await logout.click();
    await expect(page).toHaveURL(/\/login$/);
    expect(auth.count("logout")).toBe(2);
    expect(auth.user).toBeNull();
    await expect(page.getByText("Sam Student")).toHaveCount(0);
  });
}

test("shr01 AC22 a 401 on logout still ends the client session", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  auth.script("logout", authError(401, "unauthenticated"));
  await page.goto("/student/overview");
  await page
    .getByRole("button", { name: /log out/i })
    .first()
    .click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText("Sam Student")).toHaveCount(0);
});

test("shr01 AC22 companion history from a signed-in session is gone after logout and a new sign-in", async ({
  page,
}) => {
  await mockAuthApi(page, { user: STUDENT });
  await page.route("**/api/companion/messages", (route) =>
    route.fulfill({
      json: { reply: "Think about it.", mode: "hint", withheld: false },
    }),
  );
  await page.goto("/student/overview");
  await page.getByRole("button", { name: "Open study companion" }).click();
  await page
    .getByLabel("Message your study companion")
    .fill("Private signed-in message");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Private signed-in message",
  );
  await page.getByRole("button", { name: "Minimise study companion" }).click();
  await page
    .getByRole("button", { name: /log out/i })
    .first()
    .click();
  await expect(page).toHaveURL(/\/login$/);
  await emailField(page).fill(STUDENT.email!);
  await passwordField(page).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/student\/overview$/);
  await page.getByRole("button", { name: "Open study companion" }).click();
  await expect(page.getByRole("dialog")).not.toContainText(
    "Private signed-in message",
  );
});

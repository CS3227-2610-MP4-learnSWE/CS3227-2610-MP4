import { test, expect, type Page } from "@playwright/test";
import {
  ADMIN,
  DEMO_HEADING,
  PASSWORD,
  STUDENT,
  TEACHER,
  authError,
  emailField,
  exploreDemoLink,
  mockAuthApi,
  passwordField,
} from "./authApi";

/**
 * SHR-01 AC21: the real sign-in and create-account form on /login.
 * Everything runs against the auth mock (tests/authApi.ts); no backend.
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

const SIGN_IN = { name: "Sign in", exact: true } as const;

async function openCreateAccount(page: Page) {
  await page
    .getByRole("button", { name: /create account/i })
    .first()
    .click();
  await expect(page.getByLabel(/^display name/i)).toBeVisible();
}

test("shr01 AC21 the form has labelled fields, correct autocomplete and a Sign in button", async ({
  page,
}) => {
  await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await expect(emailField(page)).toBeVisible();
  await expect(passwordField(page)).toBeVisible();
  await expect(page.getByRole("button", SIGN_IN)).toBeVisible();
  expect(["username", "email"]).toContain(
    await emailField(page).getAttribute("autocomplete"),
  );
  await expect(passwordField(page)).toHaveAttribute("type", "password");
  await expect(passwordField(page)).toHaveAttribute(
    "autocomplete",
    "current-password",
  );
});

test("shr01 AC21 create account mode asks for display name, email and password with new-password autocomplete", async ({
  page,
}) => {
  await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await openCreateAccount(page);
  await expect(emailField(page)).toBeVisible();
  await expect(passwordField(page)).toBeVisible();
  await expect(passwordField(page)).toHaveAttribute(
    "autocomplete",
    "new-password",
  );
  await expect(page.getByLabel(/^display name/i)).toHaveAttribute(
    "autocomplete",
    "name",
  );
  // The password rules are shown to the visitor.
  await expect(page.locator("body")).toContainText(/10/);
  await expect(page.locator("body")).toContainText(/128/);
});

for (const [user, home] of [
  [STUDENT, "/student/overview"],
  [TEACHER, "/teacher/overview"],
  [ADMIN, "/admin/overview"],
] as const) {
  test(`shr01 AC21 signing in as a ${user.role} goes to ${home} and posts exactly email and password`, async ({
    page,
  }) => {
    const auth = await mockAuthApi(page, { user: null });
    await page.goto("/login");
    await emailField(page).fill(`  ${user.email!.toUpperCase()} `);
    await passwordField(page).fill(PASSWORD);
    await page.getByRole("button", SIGN_IN).click();
    await expect(page).toHaveURL(new RegExp(`${home}$`));
    const posts = auth.of("login");
    expect(posts).toHaveLength(1);
    const body = posts[0].body as Record<string, unknown>;
    expect(Object.keys(body).sort()).toEqual(["email", "password"]);
    expect(body.password).toBe(PASSWORD);
    expect(posts[0].headers["x-student-id"]).toBeUndefined();
  });
}

test("shr01 AC21 a wrong password shows an announced error and stays on /login", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await emailField(page).fill(STUDENT.email!);
  await passwordField(page).fill("not the password at all");
  await page.getByRole("button", SIGN_IN).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("alert")).not.toContainText(
    "not the password at all",
  );
  // invalid_credentials is a login failure, not an expired session: no redirect, no sign-in notice.
  expect(auth.count("login")).toBe(1);
  // A retry with the right password works.
  await passwordField(page).fill(PASSWORD);
  await page.getByRole("button", SIGN_IN).click();
  await expect(page).toHaveURL(/\/student\/overview$/);
});

test("shr01 AC21 the error is the same for an unknown email (no enumeration in the UI)", async ({
  page,
}) => {
  await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await emailField(page).fill(STUDENT.email!);
  await passwordField(page).fill("wrong wrong wrong");
  await page.getByRole("button", SIGN_IN).click();
  const known = await page.getByRole("alert").innerText();
  await emailField(page).fill("nobody.at.all@example.com");
  await page.getByRole("button", SIGN_IN).click();
  await expect(page.getByRole("alert")).toHaveText(known);
});

test("shr01 AC21 the submit button is disabled while the request is in flight", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  auth.script("login", { hold: true });
  await page.goto("/login");
  await emailField(page).fill(STUDENT.email!);
  await passwordField(page).fill(PASSWORD);
  await page.getByRole("button", SIGN_IN).click();
  await expect.poll(() => auth.count("login")).toBe(1);
  await expect(
    page.getByRole("button", { name: /sign(ing)? in/i }).first(),
  ).toBeDisabled();
  // A second click or Enter cannot send a second request.
  await passwordField(page).press("Enter");
  expect(auth.count("login")).toBe(1);
  auth.release();
  await expect(page).toHaveURL(/\/student\/overview$/);
});

test("shr01 AC21 a 429 shows how long to wait", async ({ page }) => {
  const auth = await mockAuthApi(page, { user: null });
  auth.script(
    "login",
    authError(429, "rate_limited", { retry_after_seconds: 37 }),
  );
  await page.goto("/login");
  await emailField(page).fill(STUDENT.email!);
  await passwordField(page).fill(PASSWORD);
  await page.getByRole("button", SIGN_IN).click();
  await expect(page.getByRole("alert")).toContainText("37");
  await expect(page).toHaveURL(/\/login$/);
});

test("shr01 AC21 server and network failures during sign-in are announced without raw text", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  auth.script("login", authError(503, "service_unavailable"), { abort: true });
  await page.goto("/login");
  await emailField(page).fill(STUDENT.email!);
  await passwordField(page).fill(PASSWORD);
  for (let i = 0; i < 2; i++) {
    await page.getByRole("button", SIGN_IN).click();
    await expect(page.getByRole("alert")).toBeVisible();
    expect(await page.getByRole("alert").innerText()).not.toContain(
      "service_unavailable",
    );
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("button", SIGN_IN)).toBeEnabled();
  }
});

test("shr01 AC21 create account posts only display name, email and password, then shows the generic message and switches to sign in", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await openCreateAccount(page);
  await page.getByLabel(/^display name/i).fill("Nora New");
  await emailField(page).fill("nora.new@example.com");
  await passwordField(page).fill("a long enough passphrase");
  await passwordField(page).press("Enter");
  await expect.poll(() => auth.count("signup")).toBe(1);
  const body = auth.of("signup")[0].body as Record<string, unknown>;
  // Nothing the visitor controls can name a role: the client never sends one.
  expect(Object.keys(body).sort()).toEqual([
    "display_name",
    "email",
    "password",
  ]);
  expect(body).toEqual({
    display_name: "Nora New",
    email: "nora.new@example.com",
    password: "a long enough passphrase",
  });
  // Back on the sign-in form, with a generic confirmation that does not say whether the
  // address was already registered.
  await expect(page.getByLabel(/^display name/i)).toHaveCount(0);
  await expect(page.getByRole("button", SIGN_IN)).toBeVisible();
  const text = await page.locator("body").innerText();
  expect(text).not.toMatch(/already (registered|exists|in use|taken)/i);
  await expect(
    page.getByRole("status").or(page.getByRole("alert")).first(),
  ).toContainText(/\S/);
  await expect(page).toHaveURL(/\/login$/);
  expect(auth.count("login")).toBe(0); // signup does not sign the visitor in
});

test("shr01 AC21 signup validation errors are announced and keep the entered fields", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: null });
  auth.script(
    "signup",
    authError(422, "validation_error", { fields: ["password"] }),
  );
  await page.goto("/login");
  await openCreateAccount(page);
  await page.getByLabel(/^display name/i).fill("Nora New");
  await emailField(page).fill("nora.new@example.com");
  await passwordField(page).fill("short");
  await passwordField(page).press("Enter");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel(/^display name/i)).toHaveValue("Nora New");
  await expect(emailField(page)).toHaveValue("nora.new@example.com");
});

test("shr01 AC21 a signup 429 shows how long to wait", async ({ page }) => {
  const auth = await mockAuthApi(page, { user: null });
  auth.script(
    "signup",
    authError(429, "rate_limited", { retry_after_seconds: 91 }),
  );
  await page.goto("/login");
  await openCreateAccount(page);
  await page.getByLabel(/^display name/i).fill("Nora New");
  await emailField(page).fill("nora.new@example.com");
  await passwordField(page).fill("a long enough passphrase");
  await passwordField(page).press("Enter");
  await expect(page.getByRole("alert")).toContainText("91");
});

test("shr01 AC21 the Explore demo buttons stay, grouped under the development-shortcut heading", async ({
  page,
}) => {
  await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await expect(page.getByText(DEMO_HEADING)).toBeVisible();
  for (const role of ["student", "teacher", "admin"] as const)
    await expect(await exploreDemoLink(page, role)).toBeVisible();
  // The misleading preview-only wording is gone from the sign-in form.
  await expect(page.locator("body")).not.toContainText("Preview only");
  await expect(page.locator("body")).not.toContainText(
    "Not available in this preview",
  );
});

test("shr01 AC21 the page works on a narrow viewport without horizontal scroll", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 640 });
  await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await expect(page.getByRole("button", SIGN_IN)).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
});

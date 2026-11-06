import { test, expect } from "@playwright/test";
import {
  logOutWithConfirmation,
  ADMIN,
  DEMO_HEADING,
  STUDENT,
  TEACHER,
  mockAuthApi,
} from "./authApi";

/**
 * SHR-01 AC22 flag-off: the build sets VITE_ENABLE_DEMO_ACCESS=false (project "demo-off" in
 * playwright.config.ts, a second dev server on port 5174). RequireRole must then send anonymous
 * visitors to /login and the login page must hide the demo shortcut. Real sessions are unaffected.
 * The same guard with the flag unset (anonymous renders children) is covered in auth-guard.spec.ts.
 */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

for (const route of [
  "/student/overview",
  "/teacher/overview",
  "/admin/overview",
  "/teacher/materials",
]) {
  test(`shr01 AC22 flag off: anonymous ${route} redirects to /login`, async ({
    page,
  }) => {
    await mockAuthApi(page, { user: null });
    await page.goto(route);
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByText("Demo (not signed in)")).toHaveCount(0);
    await expect(page.getByRole("combobox", { name: "Demo role" })).toHaveCount(
      0,
    );
  });
}

test("shr01 AC22 flag off: the login page hides the Explore demo shortcut and its heading", async ({
  page,
}) => {
  await mockAuthApi(page, { user: null });
  await page.goto("/login");
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(DEMO_HEADING)).toHaveCount(0);
  for (const role of ["student", "teacher", "admin"])
    await expect(
      page.getByRole("link", { name: `Explore ${role} demo` }),
    ).toHaveCount(0);
});

test("shr01 AC22 flag off: the loading status shows while pending and never redirects early", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  auth.script("me", { hold: true });
  await page.goto("/student/overview");
  await expect(
    page.getByRole("status").filter({ hasText: /loading/i }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/student\/overview$/);
  auth.release();
  await expect(page.getByText("Sam Student").first()).toBeVisible();
});

for (const [user, own] of [
  [STUDENT, "/student/overview"],
  [TEACHER, "/teacher/overview"],
  [ADMIN, "/admin/overview"],
] as const) {
  test(`shr01 AC22 flag off: a signed-in ${user.role} still reaches their area and no demo switcher shows`, async ({
    page,
  }) => {
    await mockAuthApi(page, { user });
    await page.goto(own);
    await expect(page).toHaveURL(new RegExp(`${own}$`));
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Demo role" })).toHaveCount(
      0,
    );
  });
}

test("shr01 AC22 flag off: a signed-in user of the wrong role is still sent to their own home", async ({
  page,
}) => {
  await mockAuthApi(page, { user: STUDENT });
  await page.goto("/admin/overview");
  await expect(page).toHaveURL(/\/student\/overview$/);
});

test("shr01 AC22 flag off: after logout the user lands on /login and cannot return to the area", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  await page.goto("/student/overview");
  await logOutWithConfirmation(page);
  await expect(page).toHaveURL(/\/login$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/login$/);
  expect(auth.user).toBeNull();
});

test("shr01 AC22 flag off: an expired session (401) sends the user to /login", async ({
  page,
}) => {
  const auth = await mockAuthApi(page, { user: STUDENT });
  await page.goto("/student/overview");
  auth.expire();
  await page.goto("/teacher/overview");
  await expect(page).toHaveURL(/\/login$/);
});

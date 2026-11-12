import { expect, test } from "@playwright/test";

for (const role of ["student", "teacher"] as const) {
  test(`admin-created ${role} signs in from an independent browser context`, async ({
    page,
    browser,
    baseURL,
  }, testInfo) => {
    test.skip(
      process.env.E2E_ALLOW_ADMIN_ACCOUNT_CREATION !== "1" ||
        !process.env.E2E_ADMIN_EMAIL ||
        !process.env.E2E_ADMIN_PASSWORD,
      "Requires explicit opt-in and an administrator in an isolated test database",
    );
    const email = `fresh-${role}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.test`;
    const password =
      role === "student" ? "E2E!CaseSensitive9#42" : "Mixed Case!9 #Z";
    const name = `Fresh ${role}`;
    await page.goto("/login");
    await page.getByLabel(/^email/i).fill(process.env.E2E_ADMIN_EMAIL!);
    await page.getByLabel(/^password/i).fill(process.env.E2E_ADMIN_PASSWORD!);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/analytics(\?.*)?$/);
    await page.goto("/admin/users");
    await page.getByLabel("Display name", { exact: true }).fill(name);
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page
      .getByRole("combobox", { name: "Account role", exact: true })
      .click();
    await page
      .getByRole("option", {
        name: role === "student" ? "Student" : "Teacher",
        exact: true,
      })
      .click();
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByLabel("Confirm password", { exact: true }).fill(password);
    const response = page.waitForResponse(
      (r) =>
        new URL(r.url()).pathname === "/api/admin/accounts" &&
        r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Create account", exact: true })
      .click();
    expect((await response).status()).toBe(201);
    await expect(
      page.getByRole("status").filter({ hasText: "Account created." }),
    ).toBeVisible();

    const fresh = await browser.newContext({ baseURL });
    try {
      expect(await fresh.cookies()).toHaveLength(0);
      const loginPage = await fresh.newPage();
      await loginPage.goto("/login");
      await loginPage.getByLabel(/^email/i).fill(email);
      await loginPage.getByLabel(/^password/i).fill(password);
      await loginPage
        .getByRole("button", { name: "Sign in", exact: true })
        .click();
      await expect(loginPage).toHaveURL(new RegExp(`/${role}/overview$`));
      const me = await fresh.request.get("/api/auth/me");
      expect(me.status()).toBe(200);
      expect((await me.json()).user.role).toBe(role);
      await loginPage.reload();
      await expect(loginPage).toHaveURL(new RegExp(`/${role}/overview$`));
    } finally {
      await fresh.close();
    }
    await page.setViewportSize({ width: 1100, height: 600 });
    await page.screenshot({ path: testInfo.outputPath("created-account.png") });
    await page
      .getByRole("button", { name: `Manage account ${name}`, exact: true })
      .click();
    await expect(
      page.getByRole("dialog", { name: "Account details", exact: true }),
    ).toBeVisible();
    await expect(page.locator(".MuiDialog-container").last()).toHaveCSS(
      "opacity",
      "1",
    );
    const screenshot = testInfo.outputPath("account-details.png");
    await page.screenshot({ path: screenshot });
    await testInfo.attach("Account details overlay", {
      path: screenshot,
      contentType: "image/png",
    });
    console.log("Account overlay visual:", screenshot);
  });
}

// Runs against the real FastAPI backend (no mocks): a contract change on either side fails here.
// Start the backend first, then: REAL_BACKEND=1 npx playwright test --project=real-backend
test("student answers, submits and sees the server's score", async ({
  page,
}) => {
  // SHR-01: sign in first as the seeded demo-student. Credentials come from the environment
  // used to run `python -m auth.seed` (never committed): E2E_STUDENT_EMAIL / E2E_STUDENT_PASSWORD.
  const email = process.env.E2E_STUDENT_EMAIL;
  const password = process.env.E2E_STUDENT_PASSWORD;
  test.skip(
    !email || !password,
    "E2E_STUDENT_EMAIL / E2E_STUDENT_PASSWORD not set",
  );
  await page.goto("/login");
  await page.getByLabel(/^e-?mail( address)?\s*\*?$/i).fill(email!);
  await page.getByLabel(/^password\s*\*?$/i).fill(password!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/student\/overview$/);
  // STU-02-published-sets: the seeded published set (python -m teacher_publications.seed) is picked
  // from the picker; the page reads the set id from the URL.
  await page.goto("/student/practice");
  await expect(
    page.getByRole("heading", { level: 1, name: "Choose a practice set" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Software engineering practice", exact: true })
    .click();
  await expect(page).toHaveURL(/\/student\/practice\/[0-9a-f-]{36}$/);
  await expect(
    page.getByRole("heading", {
      level: 2,
      name: "Software engineering practice",
    }),
  ).toBeVisible();
  await expect(page.getByText("Correct answer:")).toHaveCount(0);
  await page
    .getByRole("radio", { name: "A single, focused responsibility" })
    .check();
  await page
    .getByRole("radio", { name: "To catch regressions when code changes" })
    .check();
  await page.getByRole("radio", { name: "3", exact: true }).check();
  await expect(page.getByText("3 of 3 answered")).toBeVisible();
  await page.getByRole("button", { name: "Submit practice set" }).click();
  await expect(
    page.getByRole("heading", { name: "3 / 3 — Nicely done!" }),
  ).toBeVisible();
  await expect(page.getByText("Correct answer:")).toHaveCount(3);
  await expect(
    page.getByText("len returns the number of items."),
  ).toBeVisible();
});

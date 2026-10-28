import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

test("login tabs explore selected roles without authentication requests", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (
      request.url().includes("/api/") &&
      !request.url().endsWith("/api/health")
    )
      requests.push(request.url());
  });
  await page.goto("/login");
  await page.getByRole("tab", { name: "Teacher" }).click();
  await page.getByLabel("Email address").fill("demo@example.com");
  await page.getByLabel("Password", { exact: true }).fill("preview-only");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(
    "Not available in this preview",
  );
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Not available in this preview",
  );
  await page.getByRole("link", { name: "Explore teacher demo" }).click();
  await expect(page).toHaveURL(/\/teacher\/overview$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Teaching",
  );
  expect(requests).toEqual([]);
});

test("practice blocks incomplete submissions and reveals solutions only after whole-set submission", async ({
  page,
}) => {
  await page.goto("/student/practice");
  await expect(page.getByText("Correct answer:", { exact: false })).toHaveCount(
    0,
  );
  await page.getByRole("button", { name: "Submit practice set" }).click();
  await expect(page.getByRole("alert")).toContainText("Answer all 3 questions");
  await page
    .getByRole("radio", { name: "A single, focused responsibility" })
    .check();
  await page
    .getByRole("radio", { name: "To catch regressions when code changes" })
    .check();
  await page.getByLabel("Your answer").fill("3");
  await page.getByRole("button", { name: "Get a hint" }).click();
  await expect(page.getByText("Correct answer:", { exact: false })).toHaveCount(
    0,
  );
  await page.getByRole("button", { name: "Submit practice set" }).click();
  await expect(
    page.getByRole("heading", { name: "3 / 3 — Nicely done!" }),
  ).toBeVisible();
  await expect(page.getByText("Correct answer:", { exact: false })).toHaveCount(
    3,
  );
});

test("lesson completion is reversible and reflected in dashboard", async ({
  page,
}) => {
  await page.goto("/student/materials/clean-code");
  await page
    .getByRole("button", { name: "Mark as complete", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Mark as incomplete" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page.getByText("3 of 8 lessons")).toBeVisible();
  await page.goto("/student/materials/clean-code");
  await expect(
    page.getByRole("button", { name: "Mark as complete", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Mark as complete", exact: true })
    .click();
  await page.getByRole("button", { name: "Mark as incomplete" }).click();
  await expect(
    page.getByRole("button", { name: "Mark as complete", exact: true }),
  ).toBeVisible();
});

test("inbox opening marks message read and survey opens a form", async ({
  page,
}) => {
  await page.goto("/student/inbox");
  await expect(page.getByText("2 unread", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: /Help shape your learning experience/ })
    .click();
  await expect(page.getByText("1 unread", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Open feedback form" }).click();
  await expect(
    page.getByRole("heading", { name: "A better learning experience" }),
  ).toBeVisible();
});

test("theme toggle works on login and workspace", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/login");
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("link", { name: "Explore student demo" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("all role routes render on direct navigation and reload", async ({
  page,
}) => {
  for (const route of [
    "/student/overview",
    "/student/materials",
    "/student/assistant",
    "/teacher/overview",
    "/teacher/materials",
    "/teacher/generate",
    "/teacher/review",
    "/teacher/practice",
    "/teacher/inbox",
    "/teacher/feedback",
    "/admin/overview",
    "/admin/forms",
    "/admin/responses",
    "/admin/announcements",
    "/admin/users",
    "/admin/usage",
  ]) {
    await page.goto(route);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  }
  await page.reload();
  await expect(page.getByRole("heading", { name: "AI usage" })).toBeVisible();
});

test("backend outage does not block sample screens", async ({ page }) => {
  await page.route("**/api/health", (route) => route.abort());
  await page.goto("/student/overview");
  await expect(
    page.getByText("Backend unavailable", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "A little progress, every day." }),
  ).toBeVisible();
});

test("mobile navigation works without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/student/overview");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("link", { name: "Practice", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Put your knowledge to work." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("teacher actions and admin messages are explicit previews", async ({
  page,
}) => {
  await page.goto("/teacher/generate");
  await page.getByRole("button", { name: "Preview generation" }).click();
  await expect(
    page.getByText("Sample draft · No AI request was made"),
  ).toBeVisible();
  await page.goto("/admin/announcements");
  await page.getByLabel("Subject").fill("Course update");
  await page.getByLabel("Message").fill("Some useful information.");
  await page.getByRole("button", { name: "Preview announcement" }).click();
  await expect(page.getByRole("dialog")).toContainText("Nothing will be sent");
});

test("desktop and mobile layouts render without overflow in both themes", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  for (const theme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 960 });
      for (const route of [
        "/login",
        "/student/overview",
        "/student/materials",
        "/student/materials/clean-code",
        "/student/practice",
        "/student/assistant",
        "/student/inbox",
        "/teacher/overview",
        "/teacher/materials",
        "/teacher/generate",
        "/teacher/review",
        "/teacher/practice",
        "/teacher/inbox",
        "/admin/overview",
        "/admin/forms",
        "/admin/responses",
        "/admin/announcements",
        "/admin/users",
        "/admin/usage",
      ]) {
        await page.goto(route);
        await expect(page.locator("#root")).not.toBeEmpty();
        const overflow = await page.evaluate(() => ({
          width: innerWidth,
          scroll: document.documentElement.scrollWidth,
          elements: [...document.querySelectorAll("*")]
            .map((el) => ({
              className: el.className,
              width: el.getBoundingClientRect().width,
              right: el.getBoundingClientRect().right,
            }))
            .filter((el) => el.right > innerWidth),
        }));
        expect(
          overflow.scroll <= overflow.width,
          `${route} at ${width}px in ${theme}: ${JSON.stringify(overflow)}`,
        ).toBe(true);
        if (
          [
            "/login",
            "/student/overview",
            "/teacher/generate",
            "/admin/overview",
          ].includes(route)
        ) {
          await page.screenshot({
            path: `test-results/visual/${theme}-${width}-${route.replaceAll("/", "-")}.png`,
            fullPage: true,
          });
        }
      }
    }
  }
  expect(errors).toEqual([]);
});

test("keyboard focus is visible and navigation supports back and forward", async ({
  page,
}) => {
  await page.goto("/student/overview");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  const style = await page
    .getByRole("link", { name: "Skip to content" })
    .evaluate((el) => getComputedStyle(el).outlineStyle);
  expect(style).not.toBe("none");
  await page.getByRole("link", { name: "Practice", exact: true }).click();
  await page.goBack();
  await expect(page).toHaveURL(/\/student\/overview$/);
  await page.goForward();
  await expect(page).toHaveURL(/\/student\/practice$/);
});

test("search keeps material metadata stable", async ({ page }) => {
  await page.goto("/teacher/materials");
  const row = page
    .getByRole("row")
    .filter({ hasText: "Tests that give you confidence" });
  await expect(row).toContainText("Draft");
  await page.getByLabel("Search your materials").fill("testing");
  await expect(row).toContainText("Draft");
  await expect(row).toContainText("Yesterday");
});

test("file preview picker can be opened with the keyboard", async ({
  page,
}) => {
  await page.goto("/teacher/materials");
  await page.getByRole("button", { name: "Upload material" }).click();
  const choose = page.getByRole("button", { name: "Choose a file" });
  await choose.focus();
  const picker = page.waitForEvent("filechooser", { timeout: 1500 });
  await page.keyboard.press("Enter");
  const filechooser = await picker;
  await filechooser.setFiles({
    name: "sample-notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Sample notes"),
  });
  await expect(page.getByText("sample-notes.txt")).toBeVisible();
});

test("lesson outline links to the corresponding section", async ({ page }) => {
  await page.goto("/student/materials/clean-code");
  await page.getByRole("link", { name: "Easy to change", exact: true }).click();
  await expect(page).toHaveURL(/#easy-to-change$/);
  await expect(page.locator("#easy-to-change")).toHaveText(
    "02 / Make it easy to change",
  );
});

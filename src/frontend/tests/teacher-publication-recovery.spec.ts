import { test, expect } from "@playwright/test";
import {
  mockTeacherPublicationsApi,
  SAVED,
  COURSE_A,
} from "./teacherPublicationsApi";
import {
  TEACHER,
  PASSWORD,
  emailField,
  passwordField,
  mockAuthApi,
} from "./authApi";

test("publication topic failure has scoped retry and preserves title input", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
  await expect(
    page.getByRole("button", { name: "Publish notes", exact: true }),
  ).toBeEnabled();
  api.failTopics = 1;
  await page
    .getByRole("button", { name: "Publish notes", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Publish notes?",
    exact: true,
  });
  await expect(dialog.getByRole("alert")).toContainText(
    "Published content is unavailable. Please try again.",
  );
  await dialog
    .getByLabel("Publication title", { exact: true })
    .fill("Preserved confirmation title");
  await expect(
    dialog.getByRole("button", { name: "Confirm publication", exact: true }),
  ).toBeDisabled();
  const before = api.requests.length;
  await dialog
    .getByRole("button", { name: "Retry topics", exact: true })
    .click();
  await expect(
    dialog.getByRole("button", { name: "Confirm publication", exact: true }),
  ).toBeEnabled();
  await expect(
    dialog.getByLabel("Publication title", { exact: true }),
  ).toHaveValue("Preserved confirmation title");
  expect(api.requests.slice(before).map((r) => r.path)).toEqual([
    `/api/teacher/courses/${COURSE_A}/topics`,
  ]);
  expect(api.publicationCalls).toBe(0);
});

test("stale publication requires explicit reload and review before fresh confirmation", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  api.publishStatus = 409;
  api.publishCode = "draft_conflict";
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
  await page
    .getByRole("button", { name: "Publish notes", exact: true })
    .click();
  await page
    .getByLabel("Publication title", { exact: true })
    .fill("Unsaved confirmation title");
  await page
    .getByRole("button", { name: "Confirm publication", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "This draft has changed. Reload and review it before publishing.",
  );
  await expect(
    page.getByRole("button", { name: "Confirm publication", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Reload draft", exact: true }).click();
  const reload = page.getByRole("dialog", {
    name: "Reload latest draft?",
    exact: true,
  });
  await expect(reload).toContainText(
    "Reloading will discard the publication form entries. Review the latest draft before publishing.",
  );
  await reload.getByRole("button", { name: "Keep form", exact: true }).click();
  await expect(
    page.getByLabel("Publication title", { exact: true }),
  ).toHaveValue("Unsaved confirmation title");
  api.drafts = [
    {
      ...SAVED,
      version: 2,
      title: "Latest saved title",
      content: "Latest reviewed notes",
    },
  ];
  const before = api.requests.filter((r) =>
    r.path.endsWith(`/${SAVED.id}`),
  ).length;
  await page.getByRole("button", { name: "Reload draft", exact: true }).click();
  await page
    .getByRole("dialog", { name: "Reload latest draft?", exact: true })
    .getByRole("button", { name: "Reload draft", exact: true })
    .click();
  await expect(
    page.getByText("Latest reviewed notes", { exact: true }),
  ).toBeVisible();
  expect(
    api.requests.filter((r) => r.path.endsWith(`/${SAVED.id}`)),
  ).toHaveLength(before + 1);
  await page
    .getByRole("button", { name: "Publish notes", exact: true })
    .click();
  await expect(
    page.getByLabel("Publication title", { exact: true }),
  ).toHaveValue("Latest saved title");
  expect(api.publicationCalls).toBe(1);
});

test("old publication completion cannot appear after session expiry and replacement account", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  const auth = await mockAuthApi(page, { user: TEACHER });
  const next = {
    ...TEACHER,
    id: "teacher-next",
    email: "next.teacher@example.com",
    display_name: "Next Teacher",
  };
  auth.accounts.set(next.email, { user: next, password: PASSWORD });
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
  await page
    .getByRole("button", { name: "Publish notes", exact: true })
    .click();
  let release!: () => void;
  api.holdPublish = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page
    .getByRole("button", { name: "Confirm publication", exact: true })
    .click();
  await expect.poll(() => api.publicationCalls).toBe(1);
  await page.route("**/api/teacher/session-probe", (r) =>
    r.fulfill({
      status: 401,
      json: {
        detail: { code: "unauthenticated", message: "Sign in to continue." },
      },
    }),
  );
  await page.evaluate(async () => {
    const client = await new Function(
      "return import('/src/services/client.ts')",
    )();
    try {
      await client.requestTeacher("GET", "/api/teacher/session-probe");
    } catch {
      /* Expected expiry drives AuthProvider. */
    }
  });
  await expect(page).toHaveURL(/\/login$/);
  await emailField(page).fill(next.email);
  await passwordField(page).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/teacher\/overview$/);
  await page.locator('a[href="/teacher/generate"]').first().click();
  await page.getByRole("button", { name: new RegExp(SAVED.title) }).click();
  await expect(
    page.getByRole("button", { name: "Publish notes", exact: true }),
  ).toBeEnabled();
  const response = page.waitForResponse((r) => r.url().endsWith("/publish"));
  release();
  await response;
  await expect(
    page.getByText(
      "Notes published. Enrolled students can read them in Study materials.",
      { exact: true },
    ),
  ).toHaveCount(0);
  await expect(
    page.getByText("Working draft · Published snapshot exists", {
      exact: true,
    }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Publish notes", exact: true }),
  ).toBeEnabled();
  expect(api.publicationCalls).toBe(1);
});

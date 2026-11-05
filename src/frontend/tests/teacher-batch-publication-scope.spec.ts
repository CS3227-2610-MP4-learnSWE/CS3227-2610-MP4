import { test, expect } from "@playwright/test";
import { BATCH, mockTeacherMcqsApi } from "./teacherMcqsApi";

const notice =
  "One batch of three questions will be published as one practice set. Review the saved batch before publishing.";

test("teacher batch publication scope removes assembly and redirects its legacy route", async ({
  page,
}) => {
  await mockTeacherMcqsApi(page);
  await page.goto("/teacher/practice");
  await expect(page).toHaveURL(/\/teacher\/generate\?tab=questions$/);
  await expect(
    page.getByRole("heading", { name: "AI content studio", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(notice, { exact: true })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Practice sets", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Build a practice set" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Preview practice set" }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: new RegExp(BATCH.source_title) })
    .click();
  await expect(
    page.getByRole("button", { name: "Publish practice set", exact: true }),
  ).toBeEnabled();
  await page.reload();
  await expect(page.getByText(notice, { exact: true })).toBeVisible();
});

test("batch-only teacher scope preserves the student Practice navigation", async ({
  page,
}) => {
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      status: 401,
      json: {
        detail: { code: "unauthenticated", message: "Sign in to continue." },
      },
    }),
  );
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.goto("/student/overview");
  await expect(
    page.getByRole("link", { name: "Practice", exact: true }),
  ).toHaveAttribute("href", "/student/practice");
});

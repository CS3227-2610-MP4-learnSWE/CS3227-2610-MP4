import { test, expect, type Page } from "@playwright/test";
import { mockPracticeApi } from "./practiceApi";

/** STU-02-frontend: a wrong answer must look wrong, and the right one must be shown. */

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

async function submitWithOneWrong(page: Page) {
  await mockPracticeApi(page);
  await page.goto("/student/practice");
  await page
    .getByRole("radio", { name: "A single, focused responsibility" })
    .check();
  await page
    .getByRole("radio", { name: "To catch regressions when code changes" })
    .check();
  await page.getByRole("radio", { name: "2", exact: true }).check();
  await page.getByRole("button", { name: "Submit practice set" }).click();
  await expect(page.getByText("Correct answer:").first()).toBeVisible();
}

const option = (page: Page, name: string, exact = false) =>
  page.locator(".answer-option").filter({
    has: page.getByRole("radio", { name, exact }),
  });

test("stu02fe wrong answer: chosen choice is marked wrong, the right one is highlighted", async ({
  page,
}) => {
  await submitWithOneWrong(page);
  await expect(option(page, "2", true)).toHaveClass(/\bwrong\b/);
  await expect(option(page, "3", true)).toHaveClass(/\bcorrect\b/);
  await expect(option(page, "4", true)).not.toHaveClass(/\b(wrong|correct)\b/);
});

test("stu02fe wrong answer: its explanation is red, a right answer's stays green", async ({
  page,
}) => {
  await submitWithOneWrong(page);
  const panels = page.locator(".question-panel");
  await expect(panels.nth(2).locator(".solution")).toHaveClass(/\bwrong\b/);
  await expect(panels.nth(2).locator(".solution")).toContainText("Not quite");
  await expect(panels.nth(0).locator(".solution")).not.toHaveClass(/\bwrong\b/);
  await expect(panels.nth(0).locator(".solution")).toContainText("Correct");
  await expect(panels.nth(0).locator(".answer-option.correct")).toHaveCount(1);
  await expect(panels.nth(0).locator(".answer-option.wrong")).toHaveCount(0);
});

test("stu02fe wrong answer: the summary is not shown as a success when the set is not perfect", async ({
  page,
}) => {
  await submitWithOneWrong(page);
  await expect(page.locator(".MuiAlert-standardSuccess")).toHaveCount(0);
  await expect(page.locator(".MuiAlert-standardWarning")).toContainText(
    "2 / 3",
  );
});

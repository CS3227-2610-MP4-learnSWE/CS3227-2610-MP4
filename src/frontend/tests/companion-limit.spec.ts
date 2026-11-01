import { test, expect, type Page } from "@playwright/test";
import { mockPracticeApi } from "./practiceApi";
import { mockCompanionApi } from "./companionApi";

/**
 * STU-03 widget: the message box holds at most 1,000 characters and tells the
 * student when extra text was not added. Written by the orchestrator for a small
 * UI fix after the first live use, not by the independent test-designer.
 */

const BOX = "Message your study companion";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

async function openChat(page: Page) {
  await mockPracticeApi(page);
  await mockCompanionApi(page, []);
  await page.goto("/student/overview");
  await page.getByRole("button", { name: "Open study companion" }).click();
  const chat = page.getByRole("dialog", { name: "Your study companion" });
  await expect(chat).toBeVisible();
  return chat;
}

test("stu03 limit: an empty box shows 0 of 1000 and no limit note", async ({
  page,
}) => {
  const chat = await openChat(page);
  await expect(chat).toContainText("0 / 1000");
  await expect(chat).not.toContainText("limit reached");
});

test("stu03 limit: a short message shows its length and no limit note", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.getByLabel(BOX).fill("x".repeat(100));
  await expect(chat).toContainText("100 / 1000");
  await expect(chat).not.toContainText("limit reached");
});

test("stu03 limit: a long paste is cut at 1000 characters and the widget says so", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.getByLabel(BOX).fill("y".repeat(1200));
  await expect(page.getByLabel(BOX)).toHaveValue("y".repeat(1000));
  await expect(chat).toContainText("1000 / 1000");
  await expect(chat).toContainText("limit reached");
  await expect(chat).toContainText("extra text was not added");
});

test("stu03 limit: the limit note goes away once the message is shortened", async ({
  page,
}) => {
  const chat = await openChat(page);
  await page.getByLabel(BOX).fill("z".repeat(1200));
  await expect(chat).toContainText("limit reached");
  await page.getByLabel(BOX).fill("z".repeat(500));
  await expect(chat).toContainText("500 / 1000");
  await expect(chat).not.toContainText("limit reached");
});

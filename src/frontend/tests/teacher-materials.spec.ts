import { test, expect, type Page } from "@playwright/test";
import { mockTeacherMaterialsApi, COURSE_A, COURSE_B, TOPIC_A, NEW, OLD } from "./teacherMaterialsApi";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) => route.fulfill({ json: { status: "ok" } }));
});

async function openMaterials(page: Page) {
  await page.goto("/teacher/materials");
  await expect(page.getByRole("heading", { name: "Your materials, all together." })).toBeVisible();
  await expect(page.getByLabel("Course", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Topic filter")).toBeVisible();
  await expect(page.getByLabel("Search your materials")).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload material" })).toBeVisible();
}

test("tea01 course, topic, newest-first rows and search use the HTTP boundary", async ({ page }) => {
  const api = await mockTeacherMaterialsApi(page);
  await openMaterials(page);
  await expect(page.getByText(NEW.title)).toBeVisible();
  await expect(page.getByText(OLD.title)).toBeVisible();
  const items = page.getByText(/Newer testing guide|Older source/);
  await expect(items.nth(0)).toHaveText(NEW.title);
  await page.getByLabel("Search your materials").fill("architecture.txt");
  await expect(page.getByText(OLD.title)).toBeVisible();
  await expect(page.getByText(NEW.title)).toHaveCount(0);
  await page.getByLabel("Search your materials").fill("");
  await page.getByLabel("Topic filter").selectOption(TOPIC_A);
  await expect(page.getByText(NEW.title)).toBeVisible();
  await expect(page.getByText(OLD.title)).toHaveCount(0);
  expect(api.requests.some((r) => r.method === "GET" && r.path === `/api/teacher/courses/${COURSE_A}/materials?topic_id=${TOPIC_A}`)).toBe(true);
  await page.getByLabel("Course", { exact: true }).selectOption(COURSE_B);
  await expect(page.getByText(NEW.title)).toHaveCount(0);
  expect(api.requests.some((r) => r.path === `/api/teacher/courses/${COURSE_B}/topics`)).toBe(true);
});

test("tea01 upload dialog validates, sends multipart and refreshes", async ({ page }) => {
  const api = await mockTeacherMaterialsApi(page);
  await openMaterials(page);
  await page.getByRole("button", { name: "Upload material" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Title")).toBeVisible();
  await expect(dialog.getByLabel("Topic optional")).toBeVisible();
  await expect(dialog.getByText("Choose a file")).toBeVisible();
  await dialog.getByLabel("Title").fill("Uploaded checklist");
  await dialog.locator('input[type="file"]').setInputFiles({
    name: "checklist.txt", mimeType: "text/plain", buffer: Buffer.from("Checklist contents"),
  });
  await dialog.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(page.getByText("Uploaded checklist")).toBeVisible();
  const post = api.requests.find((r) => r.method === "POST" && r.path === `/api/teacher/courses/${COURSE_A}/materials`);
  expect(post?.body).toContain("checklist.txt");
  expect(post?.body).toContain("Uploaded checklist");
  expect(api.requests.filter((r) => r.method === "GET" && r.path.startsWith(`/api/teacher/courses/${COURSE_A}/materials`)).length).toBeGreaterThanOrEqual(2);
});

test("tea01 assignment, unassignment and download work on rows", async ({ page }) => {
  const api = await mockTeacherMaterialsApi(page);
  await openMaterials(page);
  const row = page.getByRole("row").filter({ hasText: OLD.title });
  await expect(row).toBeVisible();
  const selector = row.getByRole("combobox", { name: /Change topic/ });
  if (await selector.count()) {
    await selector.selectOption(TOPIC_A);
  } else {
    await row.getByRole("button", { name: "Change topic" }).click();
    await page.getByRole("option", { name: "Testing" }).click();
  }
  await expect.poll(() => api.materials.find((m) => m.id === OLD.id)?.topic_id).toBe(TOPIC_A);
  const download = page.waitForEvent("download");
  await row.getByRole("button", { name: "Download" }).click();
  expect((await download).suggestedFilename()).toBe(OLD.original_filename);
  expect(api.requests.some((r) => r.method === "GET" && r.path === `/api/teacher/materials/${OLD.id}/file`)).toBe(true);
  if (await selector.count()) {
    await selector.selectOption("");
  } else {
    await row.getByRole("button", { name: "Change topic" }).click();
    await page.getByRole("option", { name: /Unassigned|No topic/ }).click();
  }
  await expect.poll(() => api.materials.find((m) => m.id === OLD.id)?.topic_id).toBeNull();
});

test("tea01 empty state, course error Retry and recoverable material error", async ({ page }) => {
  const api = await mockTeacherMaterialsApi(page);
  api.failCourses = 1;
  await page.goto("/teacher/materials");
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByLabel("Course", { exact: true })).toBeVisible();
  api.materials = [];
  await page.getByLabel("Course", { exact: true }).selectOption(COURSE_B);
  await expect(page.getByText(/no materials/i)).toBeVisible();
  api.failMaterials = 1;
  await page.getByLabel("Course", { exact: true }).selectOption(COURSE_A);
  await expect(page.getByText(/could not|error|failed/i)).toBeVisible();
});

test("tea01 mobile page retains labeled controls and no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockTeacherMaterialsApi(page);
  await openMaterials(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole("button", { name: "Upload material" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

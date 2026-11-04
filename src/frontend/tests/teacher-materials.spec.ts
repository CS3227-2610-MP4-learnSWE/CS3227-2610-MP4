import { test, expect, type Page } from "@playwright/test";
import {
  mockTeacherMaterialsApi,
  COURSE_A,
  COURSE_B,
  TOPIC_A,
  NEW,
  OLD,
} from "./teacherMaterialsApi";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

async function openMaterials(page: Page) {
  await page.goto("/teacher/materials");
  await expect(
    page.getByRole("heading", { name: "Your materials, all together." }),
  ).toBeVisible();
  await expect(page.getByLabel("Course", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Topic filter")).toBeVisible();
  await expect(page.getByLabel("Search your materials")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Upload material" }),
  ).toBeVisible();
}

async function choose(page: Page, label: string, option: string) {
  await page
    .getByRole("combobox", { name: new RegExp(`^${label}(?: |$)`) })
    .click();
  await page.getByRole("option", { name: option, exact: true }).click();
}

test("tea01 course, topic, newest-first rows and search use the HTTP boundary", async ({
  page,
}) => {
  const api = await mockTeacherMaterialsApi(page);
  await openMaterials(page);
  await expect(page.getByText(NEW.title, { exact: true })).toBeVisible();
  await expect(page.getByText(OLD.title, { exact: true })).toBeVisible();
  await expect(page.locator("tbody tr strong").first()).toHaveText(NEW.title);
  await page.getByLabel("Search your materials").fill("architecture.txt");
  await expect(page.getByText(OLD.title, { exact: true })).toBeVisible();
  await expect(page.getByText(NEW.title, { exact: true })).toHaveCount(0);
  await page.getByLabel("Search your materials").fill("");
  await choose(page, "Topic filter", "Testing");
  await expect(page.getByText(NEW.title, { exact: true })).toBeVisible();
  await expect(page.getByText(OLD.title, { exact: true })).toHaveCount(0);
  expect(
    api.requests.some(
      (r) =>
        r.method === "GET" &&
        r.path ===
          `/api/teacher/courses/${COURSE_A}/materials?topic_id=${TOPIC_A}`,
    ),
  ).toBe(true);
  await choose(page, "Course", "Programming");
  await expect(page.getByText(NEW.title, { exact: true })).toHaveCount(0);
  expect(
    api.requests.some(
      (r) => r.path === `/api/teacher/courses/${COURSE_B}/topics`,
    ),
  ).toBe(true);
  expect(api.requests.length).toBeGreaterThan(0);
  for (const request of api.requests) {
    expect(request.headers["x-demo-user-id"]).toBeUndefined();
    expect(request.headers["x-student-id"]).toBeUndefined();
  }
});

test("tea01 upload dialog validates, sends multipart and refreshes", async ({
  page,
}) => {
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
    name: "checklist.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Checklist contents"),
  });
  await dialog.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(
    page.getByText("Uploaded checklist", { exact: true }),
  ).toBeVisible();
  const post = api.requests.find(
    (r) =>
      r.method === "POST" &&
      r.path === `/api/teacher/courses/${COURSE_A}/materials`,
  );
  expect(post?.body).toContain("checklist.txt");
  expect(post?.body).toContain("Uploaded checklist");
  expect(
    api.requests.filter(
      (r) =>
        r.method === "GET" &&
        r.path.startsWith(`/api/teacher/courses/${COURSE_A}/materials`),
    ).length,
  ).toBeGreaterThanOrEqual(2);
});

test("tea01 assignment, unassignment and download work on rows", async ({
  page,
}) => {
  const api = await mockTeacherMaterialsApi(page);
  await openMaterials(page);
  const row = page.getByRole("row").filter({ hasText: OLD.title });
  await expect(row).toBeVisible();
  const selector = row.getByRole("combobox", { name: /Change topic/ });
  await selector.click();
  await page.getByRole("option", { name: "Testing", exact: true }).click();
  await expect
    .poll(() => api.materials.find((m) => m.id === OLD.id)?.topic_id)
    .toBe(TOPIC_A);
  const download = page.waitForEvent("download");
  await row.getByRole("button", { name: "Download" }).click();
  expect((await download).suggestedFilename()).toBe(OLD.original_filename);
  expect(
    api.requests.some(
      (r) =>
        r.method === "GET" &&
        r.path === `/api/teacher/materials/${OLD.id}/file`,
    ),
  ).toBe(true);
  await selector.click();
  await page.getByRole("option", { name: "Unassigned", exact: true }).click();
  await expect
    .poll(() => api.materials.find((m) => m.id === OLD.id)?.topic_id)
    .toBeNull();
});

test("tea01 empty state, course error Retry and recoverable material error", async ({
  page,
}) => {
  const api = await mockTeacherMaterialsApi(page);
  api.failCourses = 10;
  await page.goto("/teacher/materials");
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Upload material" }),
  ).toBeDisabled();
  await expect(
    page.getByText("Upload becomes available after a course loads."),
  ).toBeVisible();
  expect(
    await page
      .getByRole("alert")
      .evaluate((element) => parseFloat(getComputedStyle(element).paddingLeft)),
  ).toBeGreaterThanOrEqual(19);
  api.failCourses = 0;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByLabel("Course", { exact: true })).toBeVisible();
  api.materials = [];
  await choose(page, "Course", "Programming");
  await expect(
    page.getByText(/no matching materials|no materials/i),
  ).toBeVisible();
  api.failMaterials = 10;
  await choose(page, "Course", "Software Engineering");
  await expect(page.getByText(/could not|error|failed/i)).toBeVisible();
});

test("tea01 mobile page retains labeled controls and no horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockTeacherMaterialsApi(page);
  await openMaterials(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Upload material" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("tea01 switching courses ignores a late response from the old course", async ({
  page,
}) => {
  const api = await mockTeacherMaterialsApi(page);
  api.materials.push({
    ...NEW,
    id: "88888888-8888-4888-8888-888888888888",
    course_id: COURSE_B,
    topic_id: null,
    title: "Programming source",
    original_filename: "programming.txt",
  });
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let held = 0;
  let completed = 0;
  await page.route(
    (url) =>
      url.pathname === `/api/teacher/courses/${COURSE_A}/materials` &&
      !url.search,
    async (route) => {
      held++;
      await gate;
      await route.fulfill({ json: [NEW, OLD] });
      completed++;
    },
  );
  await openMaterials(page);
  await expect.poll(() => held).toBeGreaterThan(0);
  await choose(page, "Course", "Programming");
  await expect(
    page.getByText("Programming source", { exact: true }),
  ).toBeVisible();
  const pending = held;
  release();
  await expect.poll(() => completed).toBe(pending);
  await settle(page);
  await expect(
    page.getByText("Programming source", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(NEW.title, { exact: true })).toHaveCount(0);
});

test("tea01 changing topic filter ignores a late unfiltered response", async ({
  page,
}) => {
  await mockTeacherMaterialsApi(page);
  await openMaterials(page);
  await expect(page.getByText(OLD.title, { exact: true })).toBeVisible();
  await choose(page, "Topic filter", "Testing");
  await expect(page.getByText(OLD.title, { exact: true })).toHaveCount(0);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let held = 0;
  let completed = 0;
  await page.route(
    (url) =>
      url.pathname === `/api/teacher/courses/${COURSE_A}/materials` &&
      !url.search,
    async (route) => {
      held++;
      await gate;
      await route.fulfill({ json: [NEW, OLD] });
      completed++;
    },
  );
  await choose(page, "Topic filter", "All topics");
  await expect.poll(() => held).toBeGreaterThan(0);
  await choose(page, "Topic filter", "Testing");
  await expect(page.getByText(NEW.title, { exact: true })).toBeVisible();
  await expect(page.getByText(OLD.title, { exact: true })).toHaveCount(0);
  const pending = held;
  release();
  await expect.poll(() => completed).toBe(pending);
  await settle(page);
  await expect(page.getByText(OLD.title, { exact: true })).toHaveCount(0);
});

test("tea01 a late topic-change refresh cannot overwrite a newer list", async ({
  page,
}) => {
  const api = await mockTeacherMaterialsApi(page);
  await openMaterials(page);
  const row = page.getByRole("row").filter({ hasText: OLD.title });
  await expect(row).toBeVisible();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let hold = true;
  let held = 0;
  let completed = 0;
  await page.route(
    (url) =>
      url.pathname === `/api/teacher/courses/${COURSE_A}/materials` &&
      !url.search,
    async (route) => {
      if (!hold) return api.handle(route);
      held++;
      await gate;
      await route.fulfill({ json: [NEW, { ...OLD, topic_id: TOPIC_A }] });
      completed++;
    },
  );
  await row.getByRole("combobox", { name: /Change topic/ }).click();
  await page.getByRole("option", { name: "Testing", exact: true }).click();
  await expect.poll(() => held).toBeGreaterThan(0);
  api.materials = api.materials.map((item) =>
    item.id === OLD.id ? { ...item, topic_id: null } : item,
  );
  hold = false;
  await choose(page, "Topic filter", "Testing");
  await expect(page.getByText(OLD.title, { exact: true })).toHaveCount(0);
  await choose(page, "Topic filter", "All topics");
  await expect(
    row.getByRole("combobox", { name: /Change topic/ }),
  ).not.toContainText("Testing");
  const pending = held;
  release();
  await expect.poll(() => completed).toBe(pending);
  await settle(page);
  await expect(
    row.getByRole("combobox", { name: /Change topic/ }),
  ).not.toContainText("Testing");
});

test("tea01 Retry reloads failed topics and restores topic options", async ({
  page,
}) => {
  const api = await mockTeacherMaterialsApi(page);
  api.failTopics = 10;
  await openMaterials(page);
  await expect(page.getByRole("alert")).toContainText("Could not load topics");
  const before = api.requests.filter(
    (r) => r.path === `/api/teacher/courses/${COURSE_A}/topics`,
  ).length;
  api.failTopics = 0;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect
    .poll(
      () =>
        api.requests.filter(
          (r) => r.path === `/api/teacher/courses/${COURSE_A}/topics`,
        ).length,
    )
    .toBeGreaterThan(before);
  await choose(page, "Topic filter", "Testing");
  await expect(page.getByText(NEW.title, { exact: true })).toBeVisible();
});

async function settle(page: Page) {
  await page.evaluate(() => new Promise(requestAnimationFrame));
  await page.evaluate(() => new Promise(requestAnimationFrame));
}

test("tea01 cancelling upload clears fields and errors on reopen", async ({
  page,
}) => {
  await mockTeacherMaterialsApi(page);
  await openMaterials(page);
  for (const dismiss of ["cancel", "escape"]) {
    await page.getByRole("button", { name: "Upload material" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Title").fill("Discard me");
    await choose(page, "Topic optional", "Testing");
    await dialog.locator('input[type="file"]').setInputFiles({
      name: "invalid.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.from("invalid"),
    });
    await dialog.getByRole("button", { name: "Upload", exact: true }).click();
    await expect(dialog.getByRole("alert")).toBeVisible();
    if (dismiss === "cancel")
      await dialog.getByRole("button", { name: "Cancel" }).click();
    else await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    await page.getByRole("button", { name: "Upload material" }).click();
    await expect(dialog.getByLabel("Title")).toHaveValue("");
    await dialog.getByLabel("Topic optional").click();
    await expect(
      page.getByRole("option", { name: "Unassigned", exact: true }),
    ).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("Escape");
    await expect(dialog.locator('input[type="file"]')).toHaveValue("");
    await expect(dialog.getByText("invalid.jpg")).toHaveCount(0);
    await expect(dialog.getByRole("alert")).toHaveCount(0);
    await dialog.getByRole("button", { name: "Cancel" }).click();
  }
});

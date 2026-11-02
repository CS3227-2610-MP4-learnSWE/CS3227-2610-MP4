import { test, expect, type Page } from "@playwright/test";
import {
  mockTeacherNotesApi,
  COURSE_A,
  SAVED,
  type TeacherNotesApi,
} from "./teacherNotesApi";

const url = `/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`;
async function edit(page: Page) {
  await page.goto(url);
  await page.getByRole("button", { name: "Edit notes", exact: true }).click();
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    SAVED.title,
  );
  await expect(page.getByLabel("Note content", { exact: true })).toHaveValue(
    SAVED.content,
  );
}
async function choose(page: Page, label: string, name: string) {
  await page
    .getByRole("combobox", { name: new RegExp(`^${label}(?: |$)`) })
    .click();
  await page.getByRole("option", { name, exact: true }).click();
}
async function dirty(page: Page) {
  await page
    .getByLabel("Note title", { exact: true })
    .fill("Local edited title");
}
async function discard(page: Page) {
  const dialog = page.getByRole("dialog", {
    name: "Unsaved changes",
    exact: true,
  });
  await expect(dialog).toBeVisible();
  await dialog
    .getByRole("button", { name: "Discard changes", exact: true })
    .click();
}
async function keep(page: Page) {
  const dialog = page.getByRole("dialog", {
    name: "Unsaved changes",
    exact: true,
  });
  await expect(dialog).toBeVisible();
  await dialog
    .getByRole("button", { name: "Keep editing", exact: true })
    .click();
}
function patches(api: TeacherNotesApi) {
  return api.requests.filter((r) => r.method === "PATCH");
}

test("tea03 edit saves explicit versioned changes and preserves source attribution after reload", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  await edit(page);
  await expect(
    page.getByRole("button", { name: "Save changes", exact: true }),
  ).toBeDisabled();
  await dirty(page);
  await page
    .getByLabel("Note content", { exact: true })
    .fill('<img src=x onerror="alert(1)">\nEdited explanation');
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByText("Draft changes saved.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Local edited title", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".notes-viewer")).toContainText(SAVED.source_title);
  await expect(page.locator(".notes-viewer")).toContainText(
    "Last edited by: demo-teacher",
  );
  await expect(page.locator('img[src="x"]')).toHaveCount(0);
  expect(patches(api)).toHaveLength(1);
  expect(JSON.parse(patches(api)[0].body!)).toEqual({
    title: "Local edited title",
    content: '<img src=x onerror="alert(1)">\nEdited explanation',
    version: 1,
  });
  expect(patches(api)[0].headers["x-demo-user-id"]).toBe("demo-teacher");
  expect(patches(api)[0].headers["x-student-id"]).toBeUndefined();
  expect(api.generationCalls).toBe(0);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Local edited title", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".notes-viewer")).toContainText(SAVED.source_title);
});

test("tea03 canonical validation counts Unicode codepoints and cancel discards only on confirmation", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  await edit(page);
  const save = page.getByRole("button", { name: "Save changes", exact: true });
  await page.getByLabel("Note title", { exact: true }).fill(` ${SAVED.title} `);
  await expect(save).toBeDisabled(); // Raw dirty, but no semantic change.
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await keep(page);
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    ` ${SAVED.title} `,
  );
  await page.getByLabel("Note title", { exact: true }).fill("x".repeat(201));
  await expect(save).toBeDisabled();
  await page.getByLabel("Note title", { exact: true }).fill("Good title");
  await page
    .getByLabel("Note content", { exact: true })
    .fill("😀".repeat(2000));
  await expect(
    page.getByText("2000 / 2000 characters", { exact: true }),
  ).toBeVisible();
  await expect(save).toBeEnabled();
  await page
    .getByLabel("Note content", { exact: true })
    .fill("😀".repeat(2001));
  await expect(save).toBeDisabled();
  await page.getByLabel("Note content", { exact: true }).fill(" \r\n\t ");
  await expect(save).toBeDisabled();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await discard(page);
  await expect(page.getByLabel("Note title", { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: SAVED.title, exact: true }),
  ).toBeVisible();
  expect(patches(api)).toHaveLength(0);
});

test("tea03 clean cancel needs no confirmation and dirty state clears when input is restored", async ({
  page,
}) => {
  await mockTeacherNotesApi(page);
  await edit(page);
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Edit notes", exact: true }).click();
  await dirty(page);
  await page.getByLabel("Note title", { exact: true }).fill(SAVED.title);
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page).toHaveURL(/\/teacher\/overview$/);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("tea03 failed save keeps inputs and retries only explicitly", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  await edit(page);
  await dirty(page);
  api.failPatchStatus = 503;
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByText("Could not save changes. Your edits are still here.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    "Local edited title",
  );
  expect(patches(api)).toHaveLength(1);
  expect(api.drafts[0].title).toBe(SAVED.title);
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(
    page.getByText("Draft changes saved.", { exact: true }),
  ).toBeVisible();
  expect(patches(api)).toHaveLength(2);
  expect(JSON.parse(patches(api)[1].body!).version).toBe(1);
});

test("tea03 conflict and failed latest read preserve local edits until successful confirmed load", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  await edit(page);
  await dirty(page);
  api.drafts[0] = {
    ...SAVED,
    title: "Other teacher title",
    content: "Other teacher notes",
    version: 2,
    updated_by: "demo-teacher-other",
  };
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByText(
      "This draft has changed. Load the latest saved version before saving.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save changes", exact: true }),
  ).toBeDisabled();
  const load = page.getByRole("button", {
    name: "Load latest saved version",
    exact: true,
  });
  await load.click();
  let modal = page.getByRole("dialog", {
    name: "Load latest saved version?",
    exact: true,
  });
  await modal
    .getByRole("button", { name: "Keep editing", exact: true })
    .click();
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    "Local edited title",
  );
  api.failGet = 1;
  await load.click();
  modal = page.getByRole("dialog", {
    name: "Load latest saved version?",
    exact: true,
  });
  await modal
    .getByRole("button", { name: "Discard changes", exact: true })
    .click();
  await expect(
    page.getByText(
      "Could not load the latest saved version. Your edits are still here.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    "Local edited title",
  );
  await load.click();
  await page
    .getByRole("dialog", { name: "Load latest saved version?", exact: true })
    .getByRole("button", { name: "Discard changes", exact: true })
    .click();
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    "Other teacher title",
  );
  await page
    .getByLabel("Note title", { exact: true })
    .fill("Merged correction");
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByText("Draft changes saved.", { exact: true }),
  ).toBeVisible();
  expect(JSON.parse(patches(api).at(-1)!.body!).version).toBe(2);
});

test("tea03 course and draft changes keep dirty buffers until navigation is confirmed", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  api.drafts.push({
    ...SAVED,
    id: "77777777-7777-4777-8777-777777777777",
    title: "Second draft",
  });
  await edit(page);
  await dirty(page);
  await choose(page, "Course", "Programming");
  await keep(page);
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    "Local edited title",
  );
  await expect(page).toHaveURL(url);
  await page.getByRole("button", { name: /^Second draft/ }).click();
  await keep(page);
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    "Local edited title",
  );
  await page.getByRole("button", { name: /^Second draft/ }).click();
  await discard(page);
  await expect(
    page.getByRole("heading", { name: "Second draft", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit notes", exact: true }).click();
  await dirty(page);
  await choose(page, "Course", "Programming");
  await discard(page);
  await expect(page).toHaveURL(/course=22222222/);
});

test("tea03 sidebar role and login navigations honour keep and discard", async ({
  page,
}) => {
  await mockTeacherNotesApi(page);
  await edit(page);
  await dirty(page);
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await keep(page);
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    "Local edited title",
  );
  await choose(page, "Demo role", "Student");
  await keep(page);
  await expect(page).toHaveURL(url);
  await page.getByRole("link", { name: "Login preview", exact: true }).click();
  await keep(page);
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await discard(page);
  await expect(page).toHaveURL(/\/teacher\/overview$/);
});

test("tea03 back and forward navigation guard retains or discards dirty edits", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  const secondId = "77777777-7777-4777-8777-777777777777";
  api.drafts.push({ ...SAVED, id: secondId, title: "Second draft" });
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${secondId}`);
  await page
    .getByRole("button", { name: new RegExp(`^${SAVED.title}`) })
    .click();
  await page.getByRole("button", { name: "Edit notes", exact: true }).click();
  await dirty(page);
  await page.goBack();
  await keep(page);
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    "Local edited title",
  );
  await page.goBack();
  await discard(page);
  await expect(page.getByLabel("Note title", { exact: true })).toHaveCount(0);
  await page.goForward();
  await page.getByRole("button", { name: "Edit notes", exact: true }).click();
  await dirty(page);
  await page.goBack();
  await discard(page);
  await page.goForward();
  await expect(
    page.getByRole("button", { name: "Edit notes", exact: true }),
  ).toBeVisible();
});

test("tea03 pending save blocks departure and duplicate saves until settled", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  await edit(page);
  await dirty(page);
  let release!: () => void;
  api.holdPatch = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect.poll(() => api.patchCalls).toBe(1);
  await expect(page.getByLabel("Note title", { exact: true })).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Cancel", exact: true }),
  ).toBeDisabled();
  await expect(page.getByRole("combobox", { name: /^Course/ })).toBeDisabled();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  const dialog = page.getByRole("dialog", {
    name: "Saving changes",
    exact: true,
  });
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Discard changes", exact: true }),
  ).toHaveCount(0);
  await dialog.getByRole("button", { name: "Stay here", exact: true }).click();
  release();
  await expect(
    page.getByText("Draft changes saved.", { exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(url);
  expect(patches(api)).toHaveLength(1);
});

test("tea03 native unload warning protects edits and reload discards only after acceptance", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  await edit(page);
  await dirty(page);
  let prompts = 0;
  page.on("dialog", async (dialog) => {
    expect(dialog.type()).toBe("beforeunload");
    prompts++;
    await dialog.accept();
  });
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Edit notes", exact: true }),
  ).toBeVisible();
  expect(prompts).toBe(1);
  expect(api.drafts[0].title).toBe(SAVED.title);
  expect(patches(api)).toHaveLength(0);
});

for (const [width, theme] of [
  [390, "light"],
  [1440, "light"],
  [390, "dark"],
  [1440, "dark"],
] as const) {
  test(`tea03 editor at ${width}px ${theme} remains readable without overflow`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
    await mockTeacherNotesApi(page);
    await edit(page);
    await dirty(page);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await expect(
      page.getByRole("button", { name: "Save changes", exact: true }),
    ).toBeEnabled();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: testInfo.outputPath(`tea03-${theme}-${width}.png`),
      fullPage: true,
    });
  });
}

test("tea03 late latest-version read cannot overwrite a different selected course", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  await edit(page);
  await dirty(page);
  api.failPatchStatus = 409;
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  let release!: () => void;
  let received = false;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(`**/api/teacher/note-drafts/${SAVED.id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    received = true;
    await held;
    await route.fulfill({
      json: { ...SAVED, version: 3, title: "Late remote title" },
    });
  });
  await page
    .getByRole("button", { name: "Load latest saved version", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Load latest saved version?", exact: true })
    .getByRole("button", { name: "Discard changes", exact: true })
    .click();
  await expect.poll(() => received).toBe(true);
  await choose(page, "Course", "Programming");
  await discard(page);
  await expect(page).toHaveURL(/course=22222222/);
  release();
  await expect(
    page.getByText("Late remote title", { exact: true }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Note title", { exact: true })).toHaveCount(0);
});

test("tea03 discard during latest read and same-draft query navigation leaves a usable fresh editor", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  await page.goto(`/teacher/generate?draft=${SAVED.id}&course=${COURSE_A}`);
  await page.getByRole("button", { name: "Edit notes", exact: true }).click();
  await dirty(page);
  api.failPatchStatus = 409;
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByText(
      "This draft has changed. Load the latest saved version before saving.",
      { exact: true },
    ),
  ).toBeVisible();
  let release!: () => void;
  let received = false;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(`**/api/teacher/note-drafts/${SAVED.id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    received = true;
    await held;
    await route.fulfill({
      json: { ...SAVED, version: 2, title: "Stale abandoned read" },
    });
  });
  await page
    .getByRole("button", { name: "Load latest saved version", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Load latest saved version?", exact: true })
    .getByRole("button", { name: "Discard changes", exact: true })
    .click();
  await expect.poll(() => received).toBe(true);
  // Clicking the current draft only normalises the query order; its keyed editor survives.
  await page
    .getByRole("button", { name: new RegExp(`^${SAVED.title}`) })
    .click();
  await discard(page);
  await expect(page).toHaveURL(url);
  await page.getByRole("button", { name: "Edit notes", exact: true }).click();
  try {
    // This must work while the abandoned GET is still held, not just after it settles.
    await expect(page.getByLabel("Note title", { exact: true })).toBeEditable();
    await page
      .getByLabel("Note title", { exact: true })
      .fill("Fresh local change");
    await expect(
      page.getByRole("button", { name: "Cancel", exact: true }),
    ).toBeEnabled();
    let releaseSave!: () => void;
    api.holdPatch = new Promise<void>((resolve) => {
      releaseSave = resolve;
    });
    await page
      .getByRole("button", { name: "Save changes", exact: true })
      .click();
    await expect.poll(() => api.patchCalls).toBe(2);
    release();
    await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
      "Fresh local change",
    );
    await expect(page.getByLabel("Note title", { exact: true })).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Cancel", exact: true }),
    ).toBeDisabled();
    releaseSave();
    await expect(
      page.getByText("Draft changes saved.", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Fresh local change", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Stale abandoned read", { exact: true }),
    ).toHaveCount(0);
    expect(patches(api)).toHaveLength(2);
  } finally {
    release();
  }
});

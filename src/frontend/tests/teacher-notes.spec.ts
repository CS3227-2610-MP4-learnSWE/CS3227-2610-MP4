import { test, expect, type Page } from "@playwright/test";
import {
  mockTeacherNotesApi,
  COURSE_A,
  COURSE_B,
  NEW,
  SAVED,
} from "./teacherNotesApi";

async function choose(page: Page, label: string, name: string) {
  await page
    .getByRole("combobox", { name: new RegExp(`^${label}(?: |$)`) })
    .click();
  await page.getByRole("option", { name, exact: true }).click();
}
async function open(page: Page) {
  await page.goto("/teacher/generate");
  await expect(
    page.getByRole("heading", { name: "AI content studio", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Generate draft notes", exact: true }),
  ).toBeEnabled();
}

test("tea02 studio generates, saves and reopens a draft with explicit real-call notices", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  await open(page);
  await expect(
    page.getByText("Generation sends the selected source text to the SoC LLM."),
  ).toBeVisible();
  await expect(page.getByText(/8,000 characters/)).toBeVisible();
  await expect(page.getByText(/100 pages/)).toBeVisible();
  await expect(
    page.getByText("MCQ generation is not available in this increment."),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Generate draft notes", exact: true })
    .click();
  await expect(
    page.getByText("Draft notes generated and saved."),
  ).toBeVisible();
  await expect(
    page.getByText("Unpublished draft · Review required"),
  ).toBeVisible();
  await expect(page.getByText(SAVED.content, { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/draft=99999999/);
  await page.reload();
  await expect(page.getByText(SAVED.content, { exact: true })).toBeVisible();
  expect(api.generationCalls).toBe(1);
  const post = api.requests.find((request) => request.method === "POST")!;
  expect(post.path).toBe(`/api/teacher/materials/${NEW.id}/note-drafts`);
  expect(post.headers["x-demo-user-id"]).toBe("demo-teacher");
  expect(post.headers["x-student-id"]).toBeUndefined();
  expect(post.body).toBeNull();
});

test("tea02 deep-linked draft is escaped text with preserved line breaks", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  const unsafe =
    '<img src=x onerror="window.__tea02Injected=true">\n<script>bad()</script>';
  api.drafts = [{ ...SAVED, content: unsafe }];
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
  const content = page.getByText(unsafe, { exact: true });
  await expect(content).toBeVisible();
  expect(
    await content.evaluate((node) => getComputedStyle(node).whiteSpace),
  ).toMatch(/pre/);
  expect(
    await page.evaluate(
      () => (window as unknown as Record<string, unknown>).__tea02Injected,
    ),
  ).toBeUndefined();
  await expect(page.locator('img[src="x"]')).toHaveCount(0);
  await expect(page.getByText("demo-teacher", { exact: true })).toBeVisible();
});

test("tea02 generation failure retains source/drafts and retries only on explicit click", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  api.failGeneration = 1;
  await open(page);
  await choose(page, "Source material", NEW.title);
  await page
    .getByRole("button", { name: "Generate draft notes", exact: true })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByText(
      "If a response is lost, generating again may create another saved draft.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: /Source material/ }),
  ).toContainText(NEW.title);
  await expect(page.getByText(SAVED.title, { exact: true })).toBeVisible();
  expect(api.generationCalls).toBe(1);
  await expect(
    page.getByText("Upstream private sentinel must not be shown"),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Generate draft notes", exact: true })
    .click();
  await expect(
    page.getByText("Draft notes generated and saved."),
  ).toBeVisible();
  expect(api.generationCalls).toBe(2);
});

test("tea02 pending generation prevents duplicate calls and ignores old course completion", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  let release!: () => void;
  api.holdGeneration = new Promise<void>((resolve) => {
    release = resolve;
  });
  await open(page);
  const generate = page.getByRole("button", {
    name: "Generate draft notes",
    exact: true,
  });
  await generate.click();
  await expect.poll(() => api.generationCalls).toBe(1);
  await expect(generate).toBeDisabled();
  await choose(page, "Course", "Programming");
  await expect(page.getByText("No saved drafts yet")).toBeVisible();
  release();
  await expect.poll(() => api.drafts.length).toBe(2);
  await expect(page.getByText(SAVED.content, { exact: true })).toHaveCount(0);
  expect(api.generationCalls).toBe(1);
  await expect(page).not.toHaveURL(/draft=/);
});

test("tea02 empty materials disable generation and inaccessible draft shows error", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  api.materials = [];
  api.drafts = [];
  await page.goto("/teacher/generate");
  await expect(
    page.getByText("Upload a source material to generate notes."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Generate draft notes", exact: true }),
  ).toBeDisabled();
  await expect(page.getByText("No saved drafts yet")).toBeVisible();
  await page.goto(
    `/teacher/generate?course=${COURSE_A}&draft=00000000-0000-4000-8000-000000000000`,
  );
  await expect(page.getByRole("alert")).toBeVisible();
  expect(api.generationCalls).toBe(0);
});

test("tea02 late course lists cannot replace newer course selections", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let held = 0;
  let completed = 0;
  await page.route(
    (url) => url.pathname === `/api/teacher/courses/${COURSE_A}/note-drafts`,
    async (route) => {
      held++;
      await gate;
      await api.handle(route);
      completed++;
    },
  );
  await page.goto("/teacher/generate");
  await expect.poll(() => held).toBeGreaterThan(0);
  await choose(page, "Course", "Programming");
  await expect(page.getByText("No saved drafts yet")).toBeVisible();
  release();
  await expect.poll(() => completed).toBe(held);
  await expect(page.getByText(SAVED.title, { exact: true })).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: /^Course/ })).toContainText(
    "Programming",
  );
});

test("tea02 late draft response cannot replace current route draft", async ({
  page,
}) => {
  const api = await mockTeacherNotesApi(page);
  const newer = {
    ...SAVED,
    id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    title: "Saved draft 2",
    content: "Newer draft contents",
  };
  api.drafts.push(newer);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let held = 0;
  let completed = 0;
  await page.route(`**/api/teacher/note-drafts/${SAVED.id}`, async (route) => {
    held++;
    await gate;
    await api.handle(route);
    completed++;
  });
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
  await expect.poll(() => held).toBeGreaterThan(0);
  await page.getByText(newer.title, { exact: true }).click();
  await expect(page.getByText(newer.content, { exact: true })).toBeVisible();
  release();
  await expect.poll(() => completed).toBe(held);
  await expect(page.getByText(newer.content, { exact: true })).toBeVisible();
  await expect(page.getByText(SAVED.content, { exact: true })).toHaveCount(0);
});

for (const theme of ["light", "dark"] as const) {
  for (const width of [390, 1440]) {
    test(`tea02 studio remains readable without overflow at ${width}px in ${theme}`, async ({
      page,
    }) => {
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 900 });
      await mockTeacherNotesApi(page);
      await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
      await expect(
        page.getByText(SAVED.content, { exact: true }),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    });
  }
}

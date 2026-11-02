import { test, expect, type Page } from "@playwright/test";
import {
  mockTeacherMcqsApi,
  BATCH,
  COURSE_A,
  COURSE_B,
  NEW,
  SAVED,
} from "./teacherMcqsApi";
const route = `/teacher/generate?tab=questions&course=${COURSE_A}&batch=${BATCH.id}`;
async function choose(page: Page, label: string, name: string) {
  await page
    .getByRole("combobox", { name: new RegExp(`^${label}(?: |$)`) })
    .click();
  await page.getByRole("option", { name, exact: true }).click();
}
const generation = (page: Page) =>
  page.getByRole("button", { name: /^(Generate 3 draft MCQs|Generating…)$/ });
async function open(page: Page) {
  await page.goto(`/teacher/generate?tab=questions&course=${COURSE_A}`);
  await expect(generation(page)).toBeEnabled();
}
test("tea02 mcqs generates three questions and reopens persistent batch by URL", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  await open(page);
  await expect(
    page.getByRole("tab", { name: "Practice questions", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(
    page.getByText("Generation sends the selected source text to the SoC LLM."),
  ).toBeVisible();
  await expect(page.getByText(/8,000 characters/)).toBeVisible();
  await expect(page.getByText(/100 pages/)).toBeVisible();
  await expect(
    page.getByText(
      "AI-generated questions may be inaccurate. Review every question before use.",
    ),
  ).toBeVisible();
  await choose(page, "Source material", NEW.title);
  await generation(page).click();
  await expect(page.getByText("Draft MCQs generated and saved.")).toBeVisible();
  await expect(page).toHaveURL(/batch=cccccccc/);
  for (const q of BATCH.questions) {
    await expect(page.getByText(q.question, { exact: true })).toBeVisible();
    await expect(page.getByText(q.explanation)).toBeVisible();
  }
  await expect(
    page.getByText("Unpublished draft · Review required"),
  ).toBeVisible();
  await expect(page.getByText(/Correct answer/)).toHaveCount(3);
  await page.reload();
  await expect(
    page.getByText(BATCH.questions[0].question, { exact: true }),
  ).toBeVisible();
  expect(api.mcqCalls).toBe(1);
  const post = api.requests.find((r) => r.method === "POST")!;
  expect(post.path).toBe(`/api/teacher/materials/${NEW.id}/mcq-drafts`);
  expect(post.body).toBeNull();
  expect(post.headers["x-demo-user-id"]).toBe("demo-teacher");
  expect(post.headers["x-student-id"]).toBeUndefined();
  expect(api.generationCalls).toBe(0);
});
test("tea02 mcqs failed generation preserves selection and retries only explicitly", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  api.failMcq = 1;
  await open(page);
  await generation(page).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByText(
      "If a response is lost, generating again may create another saved batch.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: /Source material/ }),
  ).toContainText(NEW.title);
  await expect(page.getByText("sentinel-private-provider-error")).toHaveCount(
    0,
  );
  expect(api.mcqCalls).toBe(1);
  await generation(page).click();
  await expect(page.getByText("Draft MCQs generated and saved.")).toBeVisible();
  expect(api.mcqCalls).toBe(2);
});
test("tea02 mcqs pending generation disables selection and ignores late tab completion", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  let release!: () => void;
  api.holdMcq = new Promise<void>((r) => {
    release = r;
  });
  await open(page);
  await generation(page).click();
  await expect.poll(() => api.mcqCalls).toBe(1);
  await expect(generation(page)).toBeDisabled();
  await expect(page.getByRole("combobox", { name: /^Course/ })).toBeDisabled();
  await expect(
    page.getByRole("combobox", { name: /Source material/ }),
  ).toBeDisabled();
  await page.getByRole("tab", { name: "Study notes", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Generate draft notes", exact: true }),
  ).toBeVisible();
  release();
  await expect.poll(() => api.batches.length).toBe(2);
  await expect(page).not.toHaveURL(/batch=/);
  await expect(
    page.getByText(BATCH.questions[0].question, { exact: true }),
  ).toHaveCount(0);
  expect(api.mcqCalls).toBe(1);
});
test("tea02 mcqs empty sources and inaccessible explicit course or batch", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  api.materials = [];
  api.batches = [];
  await page.goto(`/teacher/generate?tab=questions&course=${COURSE_A}`);
  await expect(generation(page)).toBeDisabled();
  await expect(page.getByText("No saved MCQ batches yet")).toBeVisible();
  await page.goto(route);
  await expect(page.getByRole("alert")).toBeVisible();
  await page.goto(
    "/teacher/generate?tab=questions&course=00000000-0000-4000-8000-000000000000",
  );
  await expect(page.getByRole("alert")).toBeVisible();
  expect(api.mcqCalls).toBe(0);
});
test("tea02 mcqs escapes model HTML instead of interpreting it", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  const unsafe = '<img src=x onerror="window.__mcqInjected=true">';
  api.batches[0].questions[0].question = unsafe;
  api.batches[0].questions[1].choices[0] = "<script>alert(1)</script>";
  api.batches[0].questions[2].explanation =
    '<a href="javascript:alert(1)">bad</a>';
  await page.goto(route);
  await expect(page.getByText(unsafe, { exact: true })).toBeVisible();
  await expect(page.locator('img[src="x"]')).toHaveCount(0);
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  expect(
    await page.evaluate(
      () => (window as unknown as Record<string, unknown>).__mcqInjected,
    ),
  ).toBeUndefined();
});
test("tea02 mcqs malformed and cross-course detail responses are rejected", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  api.batches[0].questions[0].correct_choice_index = 4;
  await page.goto(route);
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByText(BATCH.questions[0].question, { exact: true }),
  ).toHaveCount(0);
  api.batches[0] = { ...structuredClone(BATCH), course_id: COURSE_B };
  await page.reload();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByText(BATCH.questions[0].question, { exact: true }),
  ).toHaveCount(0);
});
test("tea02 mcqs ignores stale batch response after course switch", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  let release!: () => void;
  const gate = new Promise<void>((r) => {
    release = r;
  });
  let held = 0;
  await page.route(`**/api/teacher/mcq-drafts/${BATCH.id}`, async (r) => {
    held++;
    await gate;
    await api.handle(r);
  });
  await page.goto(route);
  await expect.poll(() => held).toBeGreaterThan(0);
  await choose(page, "Course", "Programming");
  await expect(page.getByText("No saved MCQ batches yet")).toBeVisible();
  release();
  await expect(page).toHaveURL(new RegExp(`course=${COURSE_B}`));
  await expect(
    page.getByText(BATCH.questions[0].question, { exact: true }),
  ).toHaveCount(0);
});
test("tea02 mcqs tab switch preserves dirty notes until discard", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
  await page.getByRole("button", { name: "Edit notes", exact: true }).click();
  await page
    .getByLabel("Note title", { exact: true })
    .fill("Keep this local title");
  await page
    .getByRole("tab", { name: "Practice questions", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Unsaved changes",
    exact: true,
  });
  await expect(dialog).toBeVisible();
  await dialog
    .getByRole("button", { name: "Keep editing", exact: true })
    .click();
  await expect(page.getByLabel("Note title", { exact: true })).toHaveValue(
    "Keep this local title",
  );
  await page
    .getByRole("tab", { name: "Practice questions", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Discard changes", exact: true })
    .click();
  await expect(generation(page)).toBeEnabled();
  expect(api.patchCalls).toBe(0);
  expect(api.mcqCalls).toBe(0);
});
test("tea02 mcqs tab departure is blocked during note save", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  let release!: () => void;
  api.holdPatch = new Promise<void>((r) => {
    release = r;
  });
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
  await page.getByRole("button", { name: "Edit notes", exact: true }).click();
  await page
    .getByLabel("Note title", { exact: true })
    .fill("Save before leaving");
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect.poll(() => api.patchCalls).toBe(1);
  await page
    .getByRole("tab", { name: "Practice questions", exact: true })
    .click();
  await expect(
    page.getByRole("dialog", { name: "Saving changes", exact: true }),
  ).toBeVisible();
  release();
  await expect(
    page.getByText("Draft changes saved.", { exact: true }),
  ).toBeVisible();
  await expect(page).not.toHaveURL(/tab=questions/);
});
for (const theme of ["light", "dark"] as const)
  for (const width of [390, 1440]) {
    test(`tea02 mcqs readable and keyboard accessible ${theme} ${width}`, async ({
      page,
    }, info) => {
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 1000 });
      const api = await mockTeacherMcqsApi(page);
      api.batches[0].source_title = "W".repeat(200);
      api.batches[0].created_by = "U".repeat(64);
      api.batches[0].questions[0].question = "Q".repeat(200);
      api.batches[0].questions[0].choices[0] = "C".repeat(80);
      api.batches[0].questions[0].explanation = "E".repeat(200);
      await page.goto(route);
      await expect(
        page.getByText("Q".repeat(200), { exact: true }),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      const tab = page.getByRole("tab", {
        name: "Practice questions",
        exact: true,
      });
      await tab.focus();
      await expect(tab).toBeFocused();
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({
        path: info.outputPath(`mcqs-${theme}-${width}.png`),
        fullPage: true,
      });
    });
  }

test("tea02 mcqs generation uses forty-five second timeout without automatic retry", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  let release!: () => void;
  api.holdMcq = new Promise<void>((r) => {
    release = r;
  });
  await open(page);
  await page.clock.install();
  await generation(page).click();
  await expect.poll(() => api.mcqCalls).toBe(1);
  await page.clock.fastForward(44000);
  await expect(generation(page)).toBeDisabled();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.clock.fastForward(1500);
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(generation(page)).toBeEnabled();
  await expect(
    page.getByRole("combobox", { name: /Source material/ }),
  ).toContainText(NEW.title);
  expect(api.mcqCalls).toBe(1);
  release();
});

test("tea02 mcqs independent list and detail failures recover on explicit retry", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  api.failBatches = 1;
  await page.goto(`/teacher/generate?tab=questions&course=${COURSE_A}`);
  await expect(page.getByRole("alert")).toBeVisible();
  await page.getByRole("button", { name: /Retry/ }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  api.failBatch = 1;
  await page.goto(route);
  await expect(page.getByRole("alert")).toBeVisible();
  await page.getByRole("button", { name: /Retry/ }).click();
  await expect(
    page.getByText(BATCH.questions[0].question, { exact: true }),
  ).toBeVisible();
  expect(api.mcqCalls).toBe(0);
});

for (const outcome of ["success", "failure"] as const) {
  test(`tea02 mcqs ignores old generation ${outcome} after back-forward returns to the same batch URL`, async ({
    page,
  }) => {
    const api = await mockTeacherMcqsApi(page);
    let release!: () => void;
    api.holdMcq = new Promise<void>((resolve) => {
      release = resolve;
    });
    api.failMcq = outcome === "failure" ? 1 : 0;
    await open(page);
    await page
      .getByRole("button", { name: new RegExp(BATCH.source_title) })
      .click();
    await expect(page).toHaveURL(route);
    await expect(
      page.getByText(BATCH.questions[0].question, { exact: true }),
    ).toBeVisible();
    await generation(page).click();
    await expect.poll(() => api.mcqCalls).toBe(1);
    await page.goBack();
    await expect(page).not.toHaveURL(/batch=/);
    await page.goForward();
    await expect(page).toHaveURL(route);
    await expect(
      page.getByText(BATCH.questions[0].question, { exact: true }),
    ).toBeVisible();
    const settled = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/mcq-drafts"),
    );
    release();
    await settled;
    await expect(generation(page)).toBeEnabled();
    await expect(page).toHaveURL(route);
    await expect(
      page.getByText("Draft MCQs generated and saved.", { exact: true }),
    ).toHaveCount(0);
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(
      page.getByText(BATCH.questions[0].question, { exact: true }),
    ).toBeVisible();
    expect(api.mcqCalls).toBe(1);
  });
}

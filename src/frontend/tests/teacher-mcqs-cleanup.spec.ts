import { test, expect, type Page } from "@playwright/test";
import {
  mockTeacherMcqsApi,
  BATCH,
  COURSE_A,
  NEW,
  SAVED,
} from "./teacherMcqsApi";
import { mockAuthApi } from "./authApi";

const url = `/teacher/generate?tab=questions&course=${COURSE_A}&batch=${BATCH.id}`;
const conflict =
  "This draft has changed. Load the latest saved version before trying again.";
async function edit(page: Page) {
  await page.goto(url);
  await page
    .getByRole("button", { name: "Edit questions", exact: true })
    .click();
  await expect(page.getByLabel("Question 1", { exact: true })).toHaveValue(
    BATCH.questions[0].question,
  );
}
async function change(page: Page) {
  await page
    .getByLabel("Question 1", { exact: true })
    .fill("Changed local question?");
}
async function discard(page: Page) {
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Discard changes", exact: true })
    .click();
}

test("tea03 MCQ editing saves exact three existing IDs and reopens with audit metadata", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  await edit(page);
  await expect(
    page.getByRole("button", { name: "Save changes", exact: true }),
  ).toBeDisabled();
  await change(page);
  await page
    .getByLabel("Question 1 choice A", { exact: true })
    .fill("An edited choice");
  await page
    .getByRole("radiogroup", { name: "Question 1 correct answer", exact: true })
    .getByRole("radio", { name: "Choice C", exact: true })
    .check();
  await page
    .getByLabel("Question 1 explanation", { exact: true })
    .fill("Edited explanation");
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByText("Question changes saved.", { exact: true }),
  ).toBeVisible();
  expect(api.mcqPatchCalls).toBe(1);
  const request = api.requests.find((r) => r.method === "PATCH")!;
  expect(request.headers["x-demo-user-id"]).toBeUndefined();
  expect(request.headers["x-csrf-token"]).toBe("csrf-token-fixture-0001");
  const payload = JSON.parse(request.body!);
  expect(Object.keys(payload).sort()).toEqual(["questions", "version"]);
  expect(payload.version).toBe(1);
  expect(payload.questions.map((q: { id: string }) => q.id).sort()).toEqual(
    BATCH.questions.map((q) => q.id).sort(),
  );
  expect(payload.questions[0].correct_choice_index).toBe(2);
  expect(api.batches[0].version).toBe(2);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Changed local question?", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Last edited by: demo-teacher/)).toBeVisible();
  expect(api.mcqCalls).toBe(0);
});

test("tea03 MCQ counters, required fields, duplicate checks and dirty cancel", async ({
  page,
}) => {
  await mockTeacherMcqsApi(page);
  await edit(page);
  const stem = page.getByLabel("Question 1", { exact: true }),
    save = page.getByRole("button", { name: "Save changes", exact: true });
  await stem.fill("");
  await expect(save).toBeDisabled();
  await stem.fill("😀".repeat(201));
  await expect(save).toBeDisabled();
  await expect(
    page.getByText("201 / 200 characters", { exact: true }),
  ).toBeVisible();
  await stem.fill("😀".repeat(200));
  await expect(save).toBeEnabled();
  await page
    .getByLabel("Question 1 choice B", { exact: true })
    .fill(BATCH.questions[0].choices[0]);
  await expect(
    page.getByText("Choices must be distinct.").first(),
  ).toBeVisible();
  await expect(save).toBeDisabled();
  await page
    .getByLabel("Question 1 choice B", { exact: true })
    .fill("Unique choice");
  await stem.fill(BATCH.questions[1].question.toUpperCase());
  await expect(
    page.getByText("Questions must be distinct.").first(),
  ).toBeVisible();
  await expect(save).toBeDisabled();
  await change(page);
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  const dialog = page.getByRole("dialog", {
    name: "Unsaved changes",
    exact: true,
  });
  await expect(dialog).toContainText("Discard your unsaved question changes?");
  await dialog
    .getByRole("button", { name: "Keep editing", exact: true })
    .click();
  await expect(stem).toHaveValue("Changed local question?");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await discard(page);
  await page
    .getByRole("button", { name: "Edit questions", exact: true })
    .click();
  await expect(stem).toHaveValue(BATCH.questions[0].question);
});

test("tea03 failed MCQ save retains edits and conflict requires explicit latest version", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  await edit(page);
  await change(page);
  api.failMcqPatch = 503;
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Teacher service is unavailable. Please try again.",
  );
  await expect(page.getByLabel("Question 1", { exact: true })).toHaveValue(
    "Changed local question?",
  );
  expect(api.mcqPatchCalls).toBe(1);
  api.failMcqPatch = 409;
  await page.getByRole("button", { name: "Retry save", exact: true }).click();
  await expect(page.getByText(conflict, { exact: true })).toBeVisible();
  api.batches[0].version = 3;
  api.batches[0].questions[0].question = "Latest remote question";
  await page
    .getByRole("button", { name: "Load latest saved version", exact: true })
    .click();
  await expect(
    page.getByRole("dialog", {
      name: "Load latest saved version?",
      exact: true,
    }),
  ).toContainText(
    "Loading the latest saved version will discard your local changes.",
  );
  await discard(page);
  await expect(page.getByLabel("Question 1", { exact: true })).toHaveValue(
    "Latest remote question",
  );
  expect(api.mcqPatchCalls).toBe(2);
});

test("tea03 dirty MCQ navigation protects tabs, sidebar, Back and Forward", async ({
  page,
}) => {
  await mockTeacherMcqsApi(page);
  await page.goto("/teacher/overview");
  await page.getByRole("link", { name: /AI content studio/ }).click();
  await page
    .getByRole("tab", { name: "Practice questions", exact: true })
    .click();
  await page
    .getByRole("button", { name: new RegExp(`^${BATCH.source_title}`) })
    .click();
  await page
    .getByRole("button", { name: "Edit questions", exact: true })
    .click();
  await change(page);
  await page.getByRole("tab", { name: "Study notes", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Keep editing", exact: true })
    .click();
  await expect(page.getByLabel("Question 1", { exact: true })).toHaveValue(
    "Changed local question?",
  );
  await page.goBack();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Keep editing", exact: true })
    .click();
  await page.goBack();
  await discard(page);
  await expect(page.getByLabel("Question 1", { exact: true })).toHaveCount(0);
  await page.goForward();
  await expect(
    page.getByRole("button", { name: "Edit questions", exact: true }),
  ).toBeVisible();
});

test("tea03 pending MCQ save prevents duplicate requests and departure", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  await edit(page);
  await change(page);
  let release!: () => void;
  api.holdMcqPatch = new Promise<void>((r) => {
    release = r;
  });
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect.poll(() => api.mcqPatchCalls).toBe(1);
  await expect(page.getByLabel("Question 1", { exact: true })).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Cancel", exact: true }),
  ).toBeDisabled();
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
    page.getByText("Question changes saved.", { exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(url);
  expect(api.mcqPatchCalls).toBe(1);
});

for (const [kind, label, title, keep, success] of [
  [
    "notes",
    "Delete note draft",
    "Delete note draft?",
    "Keep draft",
    "Note draft deleted.",
  ],
  [
    "mcqs",
    "Delete MCQ batch",
    "Delete MCQ batch?",
    "Keep batch",
    "MCQ batch deleted.",
  ],
  [
    "material",
    `Delete material ${NEW.title}`,
    "Delete material?",
    "Keep material",
    "Material deleted.",
  ],
] as const) {
  test(`tea03 confirmed ${kind} deletion accepts 204 and clears selected item`, async ({
    page,
  }) => {
    const api = await mockTeacherMcqsApi(page);
    await page.goto(
      kind === "notes"
        ? `/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`
        : kind === "material"
          ? "/teacher/materials"
          : url,
    );
    await page.getByRole("button", { name: label, exact: true }).click();
    let dialog = page.getByRole("dialog", { name: title, exact: true });
    await expect(dialog).toContainText("This cannot be undone.");
    if (kind === "mcqs")
      await expect(dialog).toContainText("all three questions");
    expect(api.deleteCalls).toBe(0);
    await dialog.getByRole("button", { name: keep, exact: true }).click();
    expect(api.deleteCalls).toBe(0);
    await page.getByRole("button", { name: label, exact: true }).click();
    dialog = page.getByRole("dialog", { name: title, exact: true });
    let release!: () => void;
    api.holdDelete = new Promise<void>((r) => {
      release = r;
    });
    await dialog
      .getByRole("button", { name: "Delete permanently", exact: true })
      .click();
    await expect.poll(() => api.deleteCalls).toBe(1);
    await expect(
      dialog.getByRole("button", { name: "Delete permanently", exact: true }),
    ).toBeDisabled();
    release();
    await expect(page.getByText(success, { exact: true })).toBeVisible();
    if (kind !== "material")
      await expect(page).not.toHaveURL(kind === "notes" ? /draft=/ : /batch=/);
    const request = api.requests.find((r) => r.method === "DELETE")!;
    expect(request.headers["x-csrf-token"]).toBe("csrf-token-fixture-0001");
    expect(request.headers["x-demo-user-id"]).toBeUndefined();
    expect(api.deleteCalls).toBe(1);
  });
}

test("tea03 referenced source failure preserves item and gives recovery", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  api.failDeleteStatus = 409;
  api.failDeleteCode = "material_in_use";
  await page.goto("/teacher/materials");
  await page
    .getByRole("button", { name: `Delete material ${NEW.title}`, exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete permanently", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Delete the note drafts and MCQ batches referencing this material first.",
  );
  await expect(
    page.getByRole("button", {
      name: `Delete material ${NEW.title}`,
      exact: true,
    }),
  ).toBeVisible();
  expect(api.deleteCalls).toBe(1);
  await expect(page.getByText("sentinel-private")).toHaveCount(0);
});

test("tea03 delete conflict loads latest before a new confirmation", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  await page.goto(url);
  await expect(
    page.getByRole("button", { name: "Delete MCQ batch", exact: true }),
  ).toBeVisible();
  api.batches[0].version = 2;
  await page
    .getByRole("button", { name: "Delete MCQ batch", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete permanently", exact: true })
    .click();
  await expect(page.getByText(conflict, { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Load latest saved version", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Delete MCQ batch", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete permanently", exact: true })
    .click();
  await expect(
    page.getByText("MCQ batch deleted.", { exact: true }),
  ).toBeVisible();
  expect(api.deleteCalls).toBe(2);
});

test("tea03 anonymous teacher data screens issue no teacher requests", async ({
  page,
}) => {
  await mockAuthApi(page, { user: null });
  let calls = 0;
  await page.route("**/api/teacher/**", (r) => {
    calls++;
    return r.fulfill({
      status: 401,
      json: {
        detail: { code: "unauthenticated", message: "Sign in to continue." },
      },
    });
  });
  for (const route of ["/teacher/materials", url]) {
    await page.goto(route);
    await expect(
      page.getByText("Sign in to manage teacher materials and drafts.", {
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Sign in", exact: true }),
    ).toBeVisible();
  }
  expect(calls).toBe(0);
});

test("tea03 expired session overrides dirty buffers and never retries save", async ({
  page,
}) => {
  const api = await mockTeacherMcqsApi(page);
  await edit(page);
  await change(page);
  await page.route(`**/api/teacher/mcq-drafts/${BATCH.id}`, (route) =>
    route.request().method() === "PATCH"
      ? route.fulfill({
          status: 401,
          json: {
            detail: {
              code: "unauthenticated",
              message: "Sign in to continue.",
            },
          },
        })
      : route.fallback(),
  );
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByLabel("Question 1", { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("dialog", { name: "Unsaved changes", exact: true }),
  ).toHaveCount(0);
  expect(api.mcqPatchCalls).toBe(0);
});

for (const width of [390, 1440])
  for (const theme of ["light", "dark"] as const) {
    test(`tea03 MCQ editor and delete confirmation ${width}px ${theme}`, async ({
      page,
    }, info) => {
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await mockTeacherMcqsApi(page);
      await edit(page);
      await change(page);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await page.screenshot({
        path: info.outputPath(`mcq-editor-${width}-${theme}.png`),
        fullPage: true,
      });
      await page.getByRole("button", { name: "Cancel", exact: true }).click();
      await discard(page);
      await page
        .getByRole("button", { name: "Delete MCQ batch", exact: true })
        .click();
      await expect(
        page
          .getByRole("dialog")
          .getByRole("button", { name: "Keep batch", exact: true }),
      ).toBeFocused();
      await page.screenshot({
        path: info.outputPath(`mcq-delete-${width}-${theme}.png`),
        fullPage: true,
      });
    });
  }

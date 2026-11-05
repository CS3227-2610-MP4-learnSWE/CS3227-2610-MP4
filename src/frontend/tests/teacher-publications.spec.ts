import { test, expect, type Page } from "@playwright/test";
import {
  mockTeacherPublicationsApi,
  snapshot,
  SAVED,
  BATCH,
  COURSE_A,
  TOPIC_A,
} from "./teacherPublicationsApi";
async function select(page: Page, label: string, option: string) {
  await page
    .getByRole("combobox", { name: new RegExp(`^${label}(?: |$)`) })
    .click();
  await page.getByRole("option", { name: option, exact: true }).click();
}
for (const kind of ["note", "practice_set"] as const) {
  const name = kind === "note" ? "Publish notes" : "Publish practice set";
  const query =
    kind === "note" ? `draft=${SAVED.id}` : `tab=questions&batch=${BATCH.id}`;
  test(`publishing ${kind}: saved snapshot, one POST, metadata, reopen and protected origin`, async ({
    page,
  }) => {
    const api = await mockTeacherPublicationsApi(page);
    await page.goto(`/teacher/generate?course=${COURSE_A}&${query}`);
    const trigger = page.getByRole("button", { name, exact: true });
    await expect(trigger).toBeEnabled();
    expect(
      api.requests.filter((r) => r.path.endsWith("/publications")),
    ).toHaveLength(1);
    await trigger.click();
    const dialog = page.getByRole("dialog", { name: `${name}?`, exact: true });
    await expect(dialog).toBeVisible();
    await expect(
      dialog.getByLabel("Publication title", { exact: true }),
    ).toHaveValue(kind === "note" ? SAVED.title : BATCH.source_title);
    await expect(
      dialog.getByText(
        "Publishing saves a permanent version once. Later draft changes will not update it.",
      ),
    ).toBeVisible();
    await dialog
      .getByLabel("Publication title", { exact: true })
      .fill(" Published testing ");
    await dialog
      .getByRole("button", { name: "Confirm publication", exact: true })
      .click();
    await expect(
      page.getByText(
        kind === "note"
          ? "Notes published. Enrolled students can read them in Study materials."
          : "Practice set published. Student practice integration is pending.",
        { exact: true },
      ),
    ).toBeVisible();
    expect(api.publicationCalls).toBe(1);
    const post = api.requests.find((r) => r.path.endsWith("/publish"))!;
    expect(JSON.parse(post.body!)).toEqual({
      version: 1,
      title: "Published testing",
      topic_id: TOPIC_A,
    });
    expect(post.headers["x-csrf-token"]).toBe("csrf-token-fixture-0001");
    expect(post.headers["x-demo-user-id"]).toBeUndefined();
    await expect(
      page.getByText("Working draft · Published snapshot exists", {
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", {
        name: kind === "note" ? "Delete draft notes" : "Delete question batch",
        exact: true,
      }),
    ).toBeDisabled();
    await page
      .getByRole("button", { name: "View published version", exact: true })
      .click();
    await expect(page).toHaveURL(/\/teacher\/review\?.*publication=/);
    await expect(
      page.getByRole("heading", { name: "Published content", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Published testing", { exact: true }).last(),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByText("Published testing", { exact: true }).last(),
    ).toBeVisible();
    expect(api.publicationCalls).toBe(1);
  });
}
test("publication status failure disables mutation and scoped retry only repeats status", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  api.failStatus = 1;
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
  await expect(
    page.getByText("Published content is unavailable. Please try again.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Publish notes", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Edit notes", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Retry publication status", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Publish notes", exact: true }),
  ).toBeEnabled();
  expect(
    api.requests.filter((r) => r.path.endsWith("/publications")),
  ).toHaveLength(2);
  expect(
    api.requests.filter((r) => r.path.endsWith("/materials")),
  ).toHaveLength(1);
  expect(
    api.requests.filter((r) => r.path.endsWith("/note-drafts")),
  ).toHaveLength(1);
});
test("publication dialog cancel clears entries; invalid title and pending duplicate prevention", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
  await page
    .getByRole("button", { name: "Publish notes", exact: true })
    .click();
  let dialog = page.getByRole("dialog", {
    name: "Publish notes?",
    exact: true,
  });
  await dialog.getByLabel("Publication title", { exact: true }).fill("   ");
  await expect(
    dialog.getByRole("button", { name: "Confirm publication", exact: true }),
  ).toBeDisabled();
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
  await page
    .getByRole("button", { name: "Publish notes", exact: true })
    .click();
  dialog = page.getByRole("dialog", { name: "Publish notes?", exact: true });
  await expect(
    dialog.getByLabel("Publication title", { exact: true }),
  ).toHaveValue(SAVED.title);
  let release!: () => void;
  api.holdPublish = new Promise<void>((resolve) => {
    release = resolve;
  });
  await dialog
    .getByRole("button", { name: "Confirm publication", exact: true })
    .click();
  await expect(
    dialog.getByRole("button", { name: "Publishing…", exact: true }),
  ).toBeDisabled();
  await expect(
    dialog.getByRole("button", { name: "Cancel", exact: true }),
  ).toBeDisabled();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeVisible();
  expect(api.publicationCalls).toBe(1);
  release();
  await expect(dialog).not.toBeVisible();
});
test("lost publication response requires status refresh, never automatically repeats POST", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  api.loseResponse = true;
  await page.goto(`/teacher/generate?course=${COURSE_A}&draft=${SAVED.id}`);
  await page
    .getByRole("button", { name: "Publish notes", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirm publication", exact: true })
    .click();
  await expect(
    page.getByText(
      "Could not confirm publication. Refresh publication status before retrying.",
      { exact: true },
    ),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Refresh publication status", exact: true })
    .click();
  await expect(
    page.getByText("Working draft · Published snapshot exists", {
      exact: true,
    }),
  ).toBeVisible();
  expect(api.publicationCalls).toBe(1);
});
test("catalogue filter is local; detail failure retry is scoped and text is escaped", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  const note = snapshot();
  note.title = '<img src=x onerror="alert(1)">';
  api.publications = [snapshot("practice_set"), note];
  api.failDetail = 1;
  await page.goto(`/teacher/review?course=${COURSE_A}`);
  await expect(
    page.getByRole("heading", { name: "Published content", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: `Open ${note.title}`, exact: true })
    .click();
  await expect(
    page.getByText("Published content is unavailable. Please try again.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByText(SAVED.content, { exact: true })).toBeVisible();
  await expect(page.locator('img[src="x"]')).toHaveCount(0);
  expect(
    api.requests.filter((r) => r.path.endsWith("/publications")),
  ).toHaveLength(1);
  expect(
    api.requests.filter((r) => r.path.includes("/published-notes/")),
  ).toHaveLength(2);
  await select(page, "Content type", "Practice sets");
  expect(
    api.requests.filter((r) => r.path.endsWith("/publications")),
  ).toHaveLength(1);
  await expect(page).toHaveURL(/type=practice_set/);
});

test("legacy catalogue preserves withdrawn and unavailable provenance", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  const legacy = {
    ...snapshot(),
    withdrawn: true,
    topic_id: null,
    topic_name: null,
    source_draft_id: null,
    source_version: null,
  };
  api.publications = [legacy];
  await page.goto(
    `/teacher/review?course=${COURSE_A}&kind=note&publication=${legacy.id}`,
  );
  for (const text of [
    "Withdrawn",
    "General",
    "Source draft unavailable",
    "Source version unavailable",
  ])
    await expect(page.getByText(text, { exact: true }).last()).toBeVisible();
  for (const name of [
    "Edit notes",
    "Delete draft notes",
    "Publish notes",
    "Withdraw",
  ])
    await expect(page.getByRole("button", { name, exact: true })).toHaveCount(
      0,
    );
});
test("completed reads are not cached across catalogue A-B-A navigation", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  api.publications = [snapshot()];
  await page.goto(`/teacher/review?course=${COURSE_A}`);
  await expect(
    page.getByRole("button", { name: `Open ${SAVED.title}`, exact: true }),
  ).toBeVisible();
  await select(page, "Course", "Programming");
  await expect(
    page.getByText("No published content yet.", { exact: true }),
  ).toBeVisible();
  api.publications[0].title = "Changed externally";
  await select(page, "Course", "Software Engineering");
  await expect(
    page.getByRole("button", { name: "Open Changed externally", exact: true }),
  ).toBeVisible();
  expect(
    api.requests.filter(
      (r) => r.path === `/api/teacher/courses/${COURSE_A}/publications`,
    ),
  ).toHaveLength(2);
});
for (const theme of ["light", "dark"] as const) {
  test(`publication catalogue ${theme} mobile stays readable and keyboard accessible`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
    const api = await mockTeacherPublicationsApi(page);
    api.publications = [snapshot("practice_set")];
    await page.goto(
      `/teacher/review?course=${COURSE_A}&kind=practice_set&publication=${api.publications[0].id}`,
    );
    await expect(
      page.getByRole("heading", { name: "Published content", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText(BATCH.questions[0].explanation, { exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.keyboard.press("Tab");
    expect(
      await page.evaluate(() => document.activeElement !== document.body),
    ).toBe(true);
  });
}

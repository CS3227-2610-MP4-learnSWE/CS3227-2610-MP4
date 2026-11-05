import { test, expect } from "@playwright/test";
import {
  mockTeacherPublicationsApi,
  snapshot,
  SAVED,
  BATCH,
  COURSE_A,
} from "./teacherPublicationsApi";
for (const kind of ["note", "practice_set"] as const) {
  test(`identical ${kind} HTTP200 retry identifies the existing snapshot`, async ({
    page,
  }) => {
    const api = await mockTeacherPublicationsApi(page);
    const name = kind === "note" ? "Publish notes" : "Publish practice set";
    await page.goto(
      `/teacher/generate?course=${COURSE_A}&${kind === "note" ? `draft=${SAVED.id}` : `tab=questions&batch=${BATCH.id}`}`,
    );
    await page.getByRole("button", { name, exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Confirm publication", exact: true }),
    ).toBeEnabled();
    // Another teacher publishes the same reviewed version after our completed status read.
    api.publications = [snapshot(kind)];
    await page
      .getByRole("button", { name: "Confirm publication", exact: true })
      .click();
    await expect(
      page.getByText("Already published. Showing the existing version.", {
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "View published version", exact: true }),
    ).toBeVisible();
    expect(api.publicationCalls).toBe(1);
    expect(api.publications).toHaveLength(1);
  });
}
test("catalogue type change clears selected detail and Back Forward restores URL selections", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  const note = snapshot();
  api.publications = [note, snapshot("practice_set")];
  await page.goto(
    `/teacher/review?course=${COURSE_A}&kind=note&publication=${note.id}`,
  );
  await expect(page.getByText(SAVED.content, { exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: /^Content type(?: |$)/ }).click();
  await page
    .getByRole("option", { name: "Practice sets", exact: true })
    .click();
  await expect(page).toHaveURL(
    new RegExp(`course=${COURSE_A}.*type=practice_set`),
  );
  expect(new URL(page.url()).searchParams.has("kind")).toBe(false);
  expect(new URL(page.url()).searchParams.has("publication")).toBe(false);
  await expect(page.getByText(SAVED.content, { exact: true })).toHaveCount(0);
  await expect(
    page.getByText("Choose a published item to view it.", { exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`publication=${note.id}`));
  await expect(page.getByText(SAVED.content, { exact: true })).toBeVisible();
  await page.goForward();
  expect(new URL(page.url()).searchParams.has("publication")).toBe(false);
  await expect(
    page.getByText("Choose a published item to view it.", { exact: true }),
  ).toBeVisible();
  expect(
    api.requests.filter((r) => r.path.endsWith("/publications")),
  ).toHaveLength(1);
});
for (const kind of ["note", "practice_set"] as const) {
  test(`published ${kind} editor retains the private-change warning`, async ({
    page,
  }) => {
    const api = await mockTeacherPublicationsApi(page);
    api.publications = [snapshot(kind)];
    await page.goto(
      `/teacher/generate?course=${COURSE_A}&${kind === "note" ? `draft=${SAVED.id}` : `tab=questions&batch=${BATCH.id}`}`,
    );
    const warning =
      "This draft was published once. Changes here remain private and cannot update or republish the published version.";
    await expect(page.getByText(warning, { exact: true })).toBeVisible();
    await page
      .getByRole("button", {
        name: kind === "note" ? "Edit notes" : "Edit questions",
        exact: true,
      })
      .click();
    await expect(
      page.getByRole("button", { name: "Save changes", exact: true }),
    ).toBeVisible();
    await expect(page.getByText(warning, { exact: true })).toBeVisible();
  });
}

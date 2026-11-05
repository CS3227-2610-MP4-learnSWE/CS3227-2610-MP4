import { test, expect } from "@playwright/test";
import {
  mockTeacherPublicationsApi,
  snapshot,
  COURSE_A,
} from "./teacherPublicationsApi";

test("abandoned pending publication list cannot revive across course A-B-A", async ({
  page,
}) => {
  const api = await mockTeacherPublicationsApi(page);
  const old = snapshot();
  api.publications = [old];
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let requests = 0,
    completed = 0;
  await page.route(
    (url) => url.pathname === `/api/teacher/courses/${COURSE_A}/publications`,
    async (route) => {
      requests++;
      if (requests !== 1) return api.handle(route);
      await gate;
      const metadata = { ...old };
      delete metadata.content;
      await route.fulfill({ json: [metadata] });
      completed++;
    },
  );
  await page.goto(`/teacher/review?course=${COURSE_A}`);
  await expect.poll(() => requests).toBe(1);
  await page.getByRole("combobox", { name: /^Course(?: |$)/ }).click();
  await page.getByRole("option", { name: "Programming", exact: true }).click();
  await expect(
    page.getByText("No published content yet.", { exact: true }),
  ).toBeVisible();
  api.publications = [{ ...old, title: "New external publication title" }];
  await page.getByRole("combobox", { name: /^Course(?: |$)/ }).click();
  await page
    .getByRole("option", { name: "Software Engineering", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Open New external publication title",
      exact: true,
    }),
  ).toBeVisible();
  expect(requests).toBe(2);
  release();
  await expect.poll(() => completed).toBe(1);
  await expect(
    page.getByRole("button", {
      name: "Open New external publication title",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: `Open ${old.title}`, exact: true }),
  ).toHaveCount(0);
});

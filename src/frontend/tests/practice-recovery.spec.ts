import { test, expect, type Page } from "@playwright/test";
import {
  FIXTURE_KEY,
  TWO_OF_THREE,
  apiError,
  mockPracticeApi,
} from "./practiceApi";

/** STU-02-frontend AC6: the attempt disappears on the server at the results step. */

const FIRST_EXPLANATION = Object.values(FIXTURE_KEY)[0].explanation;

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

async function fillAndSubmit(page: Page) {
  await page.goto("/student/practice");
  await page
    .getByRole("radio", { name: "A single, focused responsibility" })
    .check();
  await page
    .getByRole("radio", { name: "To catch regressions when code changes" })
    .check();
  await page.getByRole("radio", { name: "2", exact: true }).check();
  await page.getByRole("button", { name: "Submit practice set" }).click();
}

test("stu02fe AC6 results 404 attempt_not_found once: new attempt, save, submit, results", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { results: [apiError(404, "attempt_not_found")] },
  });
  await fillAndSubmit(page);
  await expect(page.getByText(FIRST_EXPLANATION).first()).toBeVisible();
  expect(mock.count("start")).toBe(2);
  const saves = mock.of("save");
  expect(saves).toHaveLength(2);
  expect(saves[1].body).toEqual({ answers: TWO_OF_THREE });
  expect(mock.count("submit")).toBe(2);
  expect(mock.of("results")).toHaveLength(2);
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
});

test("stu02fe AC6 results 404 attempt_not_found twice shows Try again", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: {
      results: [
        apiError(404, "attempt_not_found"),
        apiError(404, "attempt_not_found"),
      ],
    },
  });
  await fillAndSubmit(page);
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  expect(mock.count("start")).toBe(2);
  expect(mock.count("save")).toBe(2);
  expect(mock.count("submit")).toBe(2);
  expect(mock.count("results")).toBe(2);
  await expect(page.getByText(FIRST_EXPLANATION)).toHaveCount(0);
});

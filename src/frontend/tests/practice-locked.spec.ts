import { test, expect, type Page } from "@playwright/test";
import { TWO_OF_THREE, apiError, mockPracticeApi } from "./practiceApi";

/** STU-02-frontend: locked state after a failure past the save, and shape-checked replies. */

const RAW = "RAW-BODY-MARKER-93f1";
const LOCKED_TEXT = "Your answers are saved; try again to finish.";
const RADIO = "A single, focused responsibility";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

async function fillAndSubmit(page: Page) {
  await page.goto("/student/practice");
  await page.getByRole("radio", { name: RADIO }).check();
  await page
    .getByRole("radio", { name: "To catch regressions when code changes" })
    .check();
  await page.getByRole("radio", { name: "2", exact: true }).check();
  await page.getByRole("button", { name: "Submit practice set" }).click();
}

test("stu02fe locked: after a 500 on submit the radios are disabled and Try again finishes", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { submit: [apiError(500, "boom")] },
  });
  await fillAndSubmit(page);
  await expect(page.getByText(LOCKED_TEXT)).toBeVisible();
  await expect(page.getByRole("radio", { name: RADIO })).toBeDisabled();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("Correct answer:").first()).toBeVisible();
  expect(mock.count("save")).toBe(1);
  expect(mock.count("submit")).toBe(2);
});

test("stu02fe locked: a wrong-shaped save response shows the retry message and no raw body", async ({
  page,
}) => {
  await mockPracticeApi(page, {
    replies: { save: [{ json: { marker: RAW } }] },
  });
  await fillAndSubmit(page);
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain(RAW);
  await expect(page.getByRole("radio", { name: RADIO })).toBeChecked();
});

test("stu02fe locked: a wrong-shaped submit response shows the retry message and no raw body", async ({
  page,
}) => {
  await mockPracticeApi(page, {
    replies: { submit: [{ json: { marker: RAW } }] },
  });
  await fillAndSubmit(page);
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain(RAW);
});

test("stu02fe locked: after results 404 the new attempt id is used for save, submit and results", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { results: [apiError(404, "attempt_not_found")] },
  });
  await fillAndSubmit(page);
  await expect(page.getByText("Correct answer:").first()).toBeVisible();
  const [save1, save2] = mock.of("save");
  const [submit1, submit2] = mock.of("submit");
  const [results1, results2] = mock.of("results");
  expect(save2.attemptId).not.toBe(save1.attemptId);
  expect(submit1.attemptId).toBe(save1.attemptId);
  expect(results1.attemptId).toBe(save1.attemptId);
  expect(submit2.attemptId).toBe(save2.attemptId);
  expect(results2.attemptId).toBe(save2.attemptId);
  expect(save2.body).toEqual({ answers: TWO_OF_THREE });
});

test("stu02fe locked: a 422 incomplete after a locked state unlocks the radios", async ({
  page,
}) => {
  await mockPracticeApi(page, {
    replies: {
      submit: [
        apiError(500, "boom"),
        apiError(422, "incomplete", { missing: ["q2"] }),
      ],
    },
  });
  await fillAndSubmit(page);
  await expect(page.getByRole("radio", { name: RADIO })).toBeDisabled();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("alert")).toContainText("2");
  await expect(page.getByRole("radio", { name: RADIO })).toBeEnabled();
});

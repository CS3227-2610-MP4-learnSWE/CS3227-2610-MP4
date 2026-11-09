import { test, expect } from "@playwright/test";
import { PATH, setup } from "./adm01Api";

const unavailable =
  "AI grading is unavailable because the local privacy scanner is not ready. Try again later.";

test("adm01 privacy strict mode shows counts and disables grading without extra requests", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.tweak.quality = (body) => {
    body.grades.privacy_mode = "strict";
    body.grades.privacy_blocked_count = 7;
  };
  await page.goto(PATH);
  await expect(
    page.getByRole("status").filter({
      hasText:
        "AI grading is disabled until free-text privacy protection is approved. Counts and timings remain available.",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Grade ungraded responses", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText("7 responses excluded by privacy protection.", {
      exact: true,
    }),
  ).toBeVisible();
  expect(mock.count()).toBe(3);
  expect(mock.count("start")).toBe(0);
});

for (const status of [409, 503]) {
  test(`adm01 privacy ${status} start preserves results and uses exact privacy copy`, async ({
    page,
  }) => {
    const mock = await setup(page);
    const disabled = status === 409;
    mock.next("start", {
      status,
      code: disabled
        ? "privacy_grading_disabled"
        : "privacy_scanner_unavailable",
    });
    await page.goto(PATH);
    const button = page.getByRole("button", {
      name: "Grade ungraded responses",
      exact: true,
    });
    await expect(button).toBeEnabled();
    const original = page.url();
    if (disabled)
      mock.tweak.quality = (body) => {
        body.grades.privacy_mode = "strict";
      };
    await button.click();
    await page
      .getByRole("dialog", { name: "Grade responses with AI?", exact: true })
      .getByRole("button", { name: "Start grading", exact: true })
      .click();
    await expect(
      page.getByRole("alert").filter({
        hasText: disabled
          ? "AI grading is disabled because free-text privacy protection has not been approved."
          : unavailable,
      }),
    ).toBeVisible();
    expect(page.url()).toBe(original);
    expect(mock.count("start")).toBe(1);
    if (disabled) {
      await expect(button).toBeDisabled();
      expect(mock.count("quality")).toBe(2);
    } else {
      await expect(button).toBeEnabled();
      expect(mock.count("quality")).toBe(1);
    }
  });
}

test("adm01 privacy blocked count remains visible when no responses are eligible", async ({
  page,
}) => {
  const mock = await setup(page);
  mock.tweak.quality = (body) => {
    body.grades.privacy_blocked_count = 4;
    body.grades.pending_count = 0;
    body.grades.assessed_count = 0;
  };
  await page.goto(PATH);
  await expect(
    page.getByText("4 responses excluded by privacy protection.", {
      exact: true,
    }),
  ).toBeVisible();
  expect(mock.count("start")).toBe(0);
});

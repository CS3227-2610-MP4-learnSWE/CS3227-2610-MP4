// ADM-08 phase 5 port of adm02-review.spec.ts onto hub paths; assertions unchanged (see workflow/specs/ADM-08/phase5-test-mapping.md).
import { expect, test } from "@playwright/test";
import { ADMIN, STUDENT } from "./authApi";
import {
  FORM_ID,
  MSG,
  TIME,
  setup,
  questions,
  alert,
  status,
  firstAnswer,
} from "./adm08-ported-adm02Api";

test("ADM-02 uncertain publication cannot be replayed by cancelling and reopening audience", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  ctx.form.state = "draft";
  ctx.form.version = 1;
  await page.goto(`/admin/feedback-hub/forms/${FORM_ID}`);
  const open = page.getByRole("button", {
    name: "Review audience",
    exact: true,
  });
  const dialog = page.getByRole("dialog", {
    name: "Review audience",
    exact: true,
  });
  await open.click();
  await dialog
    .getByRole("checkbox", {
      name: `${STUDENT.display_name} (${STUDENT.id})`,
      exact: true,
    })
    .check();
  await dialog
    .getByRole("button", { name: "Review selected recipients", exact: true })
    .click();
  ctx.steps.push({ method: "POST", path: "/publish", abort: true });
  await dialog
    .getByRole("button", { name: "Publish form", exact: true })
    .click();
  await expect(alert(page, MSG.network)).toBeVisible();
  expect(ctx.of("POST", "/publish")).toHaveLength(1);
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  if (await open.isEnabled()) {
    await open.click();
    const selection = dialog.getByRole("checkbox", {
      name: `${STUDENT.display_name} (${STUDENT.id})`,
      exact: true,
    });
    if (await selection.isVisible()) {
      await selection.check();
      await dialog
        .getByRole("button", {
          name: "Review selected recipients",
          exact: true,
        })
        .click();
    }
    await expect(
      dialog.getByRole("button", { name: "Publish form", exact: true }),
    ).toBeDisabled();
  }
  const reload = page.getByRole("button", {
    name: "Reload saved form",
    exact: true,
  });
  await expect(reload).toBeVisible();
  expect(ctx.of("GET", FORM_ID)).toHaveLength(1);
  await reload.click();
  await expect.poll(() => ctx.of("GET", FORM_ID).length).toBe(2);
  expect(ctx.of("POST", "/publish")).toHaveLength(1);
});

test("ADM-02 successful create hands off its response to detail without a follow-up GET", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  await page.goto("/admin/feedback-hub/forms/new");
  await page
    .getByRole("textbox", { name: "Form title", exact: true })
    .fill("Response handoff form");
  await page.getByRole("button", { name: "Add question", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Question 1 prompt", exact: true })
    .fill("Your feedback?");
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page).toHaveURL(
    new RegExp(`/admin/feedback-hub/forms/${FORM_ID}$`),
  );
  await expect(status(page, "Draft saved.")).toBeVisible();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Response handoff form",
      exact: true,
    }),
  ).toBeVisible();
  expect(ctx.of("POST")).toHaveLength(1);
  expect(ctx.of("GET", FORM_ID)).toHaveLength(0);
});

test("ADM-02 transient submit failure on an unchanged saved draft recovers without extra editing", async ({
  page,
}) => {
  const ctx = await setup(page);
  ctx.draft = {
    version: 1,
    answers: [
      { question_id: questions()[0].id, value: "Already saved answer" },
    ],
    updated_at: TIME,
  };
  await page.goto(`/student/feedback/${FORM_ID}`);
  await expect(firstAnswer(page)).toHaveValue("Already saved answer");
  ctx.steps.push({
    method: "POST",
    path: "/responses",
    status: 429,
    code: "feedback_rate_limited",
  });
  const submit = page.getByRole("button", {
    name: "Submit feedback",
    exact: true,
  });
  await submit.click();
  await expect(alert(page, MSG.limited)).toBeVisible();
  await page
    .getByRole("button", { name: "Retry saving draft", exact: true })
    .click();
  await expect(submit).toBeEnabled();
  await expect(firstAnswer(page)).toHaveValue("Already saved answer");
  await submit.click();
  await expect(status(page, "Feedback submitted. Thank you.")).toBeVisible();
  expect(ctx.of("POST", "/responses")).toHaveLength(2);
});

for (const denial of [
  { status: 403, code: "forbidden", text: MSG.forbidden },
  { status: 404, code: "feedback_not_found", text: MSG.missing },
]) {
  test(`ADM-02 lost access ${denial.status} permanently stops draft editing and retry writes`, async ({
    page,
  }) => {
    const ctx = await setup(page);
    await page.goto(`/student/feedback/${FORM_ID}`);
    const field = firstAnswer(page);
    await expect(field).toBeVisible();
    ctx.steps.push({
      method: "PUT",
      path: "/draft",
      status: denial.status,
      code: denial.code,
    });
    await field.fill("Private before access loss");
    await expect(alert(page, denial.text)).toBeVisible();
    if (await field.count()) {
      await expect.soft(field).toBeDisabled();
      if (await field.isEnabled())
        await field.fill("More edits must not be accepted");
    }
    const retry = page.getByRole("button", {
      name: "Retry saving draft",
      exact: true,
    });
    if ((await retry.isVisible()) && (await retry.isEnabled()))
      await retry.click();
    await page.waitForTimeout(1200);
    expect(ctx.of("PUT", "/draft")).toHaveLength(1);
    const submit = page.getByRole("button", {
      name: "Submit feedback",
      exact: true,
    });
    if (await submit.count()) await expect(submit).toBeDisabled();
  });
}

test("ADM-02 audience role floating label remains inside visible dialog content", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  ctx.form.state = "draft";
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto(`/admin/feedback-hub/forms/${FORM_ID}`);
  await page
    .getByRole("button", { name: "Review audience", exact: true })
    .click();
  const control = page.getByRole("combobox", {
    name: "Audience role",
    exact: true,
  });
  await expect(control).toBeVisible();
  const clipped = await control.evaluate((element) => {
    const select = element as HTMLSelectElement;
    const label = select.labels?.[0];
    if (!label) return true;
    const labelTop = label.getBoundingClientRect().top;
    let ancestor = label.parentElement;
    while (ancestor) {
      const style = getComputedStyle(ancestor);
      if (
        ["auto", "scroll", "hidden", "clip"].includes(style.overflowY) &&
        labelTop < ancestor.getBoundingClientRect().top - 1
      )
        return true;
      ancestor = ancestor.parentElement;
    }
    return false;
  });
  expect(clipped).toBe(false);
});

test("ADM-02 a rejected draft save names the field to fix and focuses it", async ({
  page,
}) => {
  const ctx = await setup(page, ADMIN);
  await page.goto("/admin/feedback-hub/forms/new");
  await page
    .getByRole("textbox", { name: "Form title", exact: true })
    .fill("Hint form");
  await page.getByRole("button", { name: "Add question", exact: true }).click();
  ctx.steps.push({
    method: "POST",
    status: 422,
    code: "invalid_feedback_questions",
  });
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  const message = page.getByRole("alert").filter({ hasText: "Add 1 to 30" });
  await expect(message).toContainText(
    'Fix "Question 1 prompt": enter the question text.',
  );
  await expect(
    page.getByRole("textbox", { name: "Question 1 prompt", exact: true }),
  ).toBeFocused();
  await page
    .getByRole("textbox", { name: "Question 1 prompt", exact: true })
    .fill("Now filled");
  await expect(message).toHaveCount(0);
});

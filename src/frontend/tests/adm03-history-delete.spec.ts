import { expect, test, type Page } from "@playwright/test";
import { MSG, TITLE, analysis, setup, uuid, type Analysis } from "./adm03Api";

const PAGE = "/admin/feedback/analysis";
const many = (
  n: number,
  state: "running" | "complete" | "failed" = "complete",
): Analysis[] => Array.from({ length: n }, (_, i) => analysis(i + 1, state));
const rowLink = (page: Page, ai = "complete") =>
  page.getByRole("link", {
    name: new RegExp(`^${TITLE}, .+, 137 responses, AI ${ai}$`),
  });
const dialog = (page: Page) =>
  page.getByRole("alertdialog", { name: "Delete this analysis permanently?" });
const deleteRow = (page: Page) =>
  page.getByRole("button", {
    name: new RegExp(`^Delete analysis, ${TITLE}, `),
  });
const confirm = (page: Page) =>
  page.getByRole("button", { name: "Delete permanently", exact: true });

test("adm03 AC30 previous analyses: newest first, Load more appends one page and hides at the end", async ({
  page,
}) => {
  const ctx = await setup(page, { analyses: many(25) });
  await page.goto(PAGE);
  await expect(
    page.getByRole("heading", { name: "Previous analyses", level: 2 }),
  ).toBeVisible();
  await expect(rowLink(page)).toHaveCount(20);
  expect(ctx.analysesCalls()).toHaveLength(1);
  await page
    .getByRole("button", { name: "Load more analyses", exact: true })
    .click();
  await expect(rowLink(page)).toHaveCount(25);
  expect(ctx.analysesCalls()).toHaveLength(2);
  expect(ctx.analysesCalls()[1].query.get("offset")).toBe("20");
  await expect(
    page.getByRole("button", { name: "Load more analyses" }),
  ).toHaveCount(0);
});

test("adm03 previous analyses: empty text, status in the link name, and link pushes history", async ({
  page,
}) => {
  await setup(page);
  await page.goto(PAGE);
  await expect(page.getByText("No analyses yet.")).toBeVisible();
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await setup(page, {
    analyses: [analysis(1, "running"), analysis(2, "failed")],
  });
  await page.goto(PAGE);
  await expect(rowLink(page, "running")).toBeVisible();
  await rowLink(page, "failed").click();
  await expect(page).toHaveURL(new RegExp(`${PAGE}/${uuid(2)}$`));
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${PAGE}$`));
});

test("adm03 previous analyses load failure shows the exact message and Retry repeats only that request", async ({
  page,
}) => {
  const ctx = await setup(page, { analyses: many(2) });
  ctx.steps.push({ suffix: "/analyses", abort: true });
  await page.goto(PAGE);
  await expect(
    page.getByRole("alert").filter({ hasText: MSG.load("previous analyses") }),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Feedback form" }),
  ).toBeVisible();
  const mark = ctx.requests.length;
  await page.getByRole("button", { name: "Retry" }).first().click();
  await expect(rowLink(page)).toHaveCount(2);
  expect(ctx.requests.slice(mark).map((r) => r.path.split("/").pop())).toEqual([
    "analyses",
  ]);
});

// ---- AC38 delete dialog ----

test("adm03 AC38 dialog: role, texts, initial focus on Cancel, focus trap, Escape and Cancel close with focus back and no request", async ({
  page,
}) => {
  const ctx = await setup(page, { analyses: many(2) });
  await page.goto(PAGE);
  const trigger = deleteRow(page).first();
  await expect(trigger).toBeVisible();
  await expect
    .poll(
      () =>
        ctx.requests.filter(
          (r) => r.path.endsWith("/forms") || r.path.endsWith("/analyses"),
        ).length,
    )
    .toBe(2);
  const before = ctx.requests.length;
  await trigger.click();
  await expect(dialog(page)).toBeVisible();
  await expect(dialog(page)).toContainText(`Form: ${TITLE}. Created `);
  await expect(dialog(page)).toContainText("Responses analysed: 137.");
  await expect(dialog(page)).toContainText(
    "This permanently deletes the analysis: its statistics and charts, the AI summary, themes and suggestions, and the links to supporting responses. This cannot be undone.",
  );
  await expect(dialog(page)).toContainText(
    "The original feedback responses and forms are not deleted.",
  );
  await expect(
    page.getByRole("button", { name: "Cancel", exact: true }),
  ).toBeFocused();
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press("Tab");
    expect(
      await page.evaluate(
        () => !!document.activeElement?.closest('[role="alertdialog"]'),
      ),
    ).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(dialog(page)).toHaveCount(0);
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(dialog(page)).toHaveCount(0);
  await expect(trigger).toBeFocused();
  expect(ctx.requests.length).toBe(before);
  expect(ctx.of("DELETE")).toHaveLength(0);
});

test("adm03 AC38 confirm from the list: one DELETE on double click, Deleting... state, row removed, status, focus on the heading", async ({
  page,
}) => {
  const ctx = await setup(page, { analyses: many(3) });
  ctx.steps.push({ method: "DELETE", hold: true });
  await page.goto(PAGE);
  await deleteRow(page).first().click();
  await confirm(page).dblclick();
  const busy = page.getByRole("button", { name: "Deleting...", exact: true });
  await expect(busy).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Cancel", exact: true }),
  ).toBeDisabled();
  await page.keyboard.press("Escape");
  await expect(dialog(page)).toBeVisible();
  expect(ctx.of("DELETE")).toHaveLength(1);
  const gets = ctx.analysesCalls().length;
  ctx.release();
  await expect(dialog(page)).toHaveCount(0);
  await expect(rowLink(page)).toHaveCount(2);
  await expect(
    page.getByRole("status").filter({ hasText: MSG.deleteDone }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Previous analyses", level: 2 }),
  ).toBeFocused();
  expect(ctx.of("DELETE")).toHaveLength(1);
  expect(ctx.analysesCalls()).toHaveLength(gets); // no GET after a delete from the list
  expect(ctx.of("DELETE")[0].path.endsWith(`/analyses/${uuid(1)}`)).toBe(true);
});

test("adm03 AC38 list consistency: next_offset drops by one, no row repeated or skipped, emptied list refetches", async ({
  page,
}) => {
  const ctx = await setup(page, { analyses: many(25) });
  await page.goto(PAGE);
  await deleteRow(page).first().click();
  await confirm(page).click();
  await expect(rowLink(page)).toHaveCount(19);
  await page
    .getByRole("button", { name: "Load more analyses", exact: true })
    .click();
  expect(ctx.analysesCalls().at(-1)?.query.get("offset")).toBe("19");
  await expect(rowLink(page)).toHaveCount(24); // 25 minus the deleted one, each shown once
  const names = await rowLink(page).evaluateAll((els) =>
    els.map((e) => e.getAttribute("href")),
  );
  expect(new Set(names).size).toBe(24);

  await page.unrouteAll({ behavior: "ignoreErrors" });
  const ctx2 = await setup(page, { analyses: many(21) });
  await page.goto(PAGE);
  for (let i = 0; i < 20; i++) {
    await deleteRow(page).first().click();
    await confirm(page).click();
    await expect(dialog(page)).toHaveCount(0);
  }
  await expect(rowLink(page)).toHaveCount(1); // the list emptied while more existed: one GET at offset 0
  expect(ctx2.analysesCalls().at(-1)?.query.get("offset")).toBe("0");
});

test("adm03 AC38 delete from the result page replaces to the selection page with the status shown once", async ({
  page,
}) => {
  const ctx = await setup(page, { analyses: [analysis(1, "complete")] });
  await page.goto(PAGE);
  await rowLink(page).click();
  await page
    .getByRole("button", { name: "Delete analysis", exact: true })
    .click();
  await expect(dialog(page)).toContainText(`Form: ${TITLE}.`);
  await confirm(page).click();
  await expect(page).toHaveURL(new RegExp(`${PAGE}$`));
  await expect(
    page.getByRole("status").filter({ hasText: MSG.deleteDone }),
  ).toBeVisible();
  expect(ctx.of("DELETE")).toHaveLength(1);
  await page.goBack(); // replace: Back does not return to the deleted result
  await expect(page).not.toHaveURL(new RegExp(`${uuid(1)}`));
  await page.goto(PAGE);
  await page.reload();
  await expect(
    page.getByRole("status").filter({ hasText: MSG.deleteDone }),
  ).toHaveCount(0);
  await page.goto(`${PAGE}/${uuid(1)}`);
  await expect(
    page.getByRole("alert").filter({ hasText: MSG.analysisNotFound }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Back to Feedback analysis" }),
  ).toBeVisible();
});

for (const [name, step, message] of [
  [
    "409 analysis_running",
    { status: 409, code: "analysis_running", message: MSG.deleteRunning },
    MSG.deleteRunning,
  ],
  ["network", { abort: true }, MSG.deleteNetwork],
  [
    "500 internal_error",
    { status: 500, code: "internal_error", message: MSG.deleteInternal },
    MSG.deleteInternal,
  ],
  ["403", { status: 403, code: "forbidden", message: "x" }, MSG.forbidden],
] as const) {
  test(`adm03 AC38 delete failure ${name}: exact message as an alert inside the dialog, row kept, buttons enabled`, async ({
    page,
  }) => {
    const ctx = await setup(page, { analyses: many(2) });
    ctx.steps.push({ method: "DELETE", ...step });
    await page.goto(PAGE);
    await deleteRow(page).first().click();
    await confirm(page).click();
    await expect(
      dialog(page).getByRole("alert").filter({ hasText: message }),
    ).toBeVisible();
    await expect(rowLink(page)).toHaveCount(2);
    await expect(confirm(page)).toBeEnabled();
    await expect(
      page.getByRole("button", { name: "Cancel", exact: true }),
    ).toBeEnabled();
    await expect(
      page.getByText(/something went wrong|an error occurred/i),
    ).toHaveCount(0);
    ctx.release();
  });
}

test("adm03 AC38 delete 404 closes the dialog, removes the row and shows the delete-specific message in the status", async ({
  page,
}) => {
  const ctx = await setup(page, { analyses: many(2) });
  ctx.steps.push({
    method: "DELETE",
    status: 404,
    code: "analysis_not_found",
    message: MSG.analysisNotFound,
  });
  await page.goto(PAGE);
  await deleteRow(page).first().click();
  await confirm(page).click();
  await expect(dialog(page)).toHaveCount(0);
  await expect(
    page.getByRole("status").filter({ hasText: MSG.delete404 }),
  ).toBeVisible();
  await expect(rowLink(page)).toHaveCount(1);
});

test("adm03 AC38 delete 401 sends the user to sign in", async ({ page }) => {
  const ctx = await setup(page, { analyses: many(1) });
  ctx.steps.push({
    method: "DELETE",
    status: 401,
    code: "unauthenticated",
    message: "x",
  });
  await page.goto(PAGE);
  await deleteRow(page).first().click();
  await confirm(page).click();
  await expect(page.getByText(MSG.expired)).toBeVisible();
});

test("adm03 AC38 a retry after a network failure sends one more DELETE and succeeds", async ({
  page,
}) => {
  const ctx = await setup(page, { analyses: many(1) });
  ctx.steps.push({ method: "DELETE", abort: true });
  await page.goto(PAGE);
  await deleteRow(page).first().click();
  await confirm(page).click();
  await expect(dialog(page).getByRole("alert")).toBeVisible();
  await confirm(page).click();
  await expect(dialog(page)).toHaveCount(0);
  expect(ctx.of("DELETE")).toHaveLength(2);
  await expect(page.getByText("No analyses yet.")).toBeVisible();
});

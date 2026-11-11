import { expect, test, type Page } from "@playwright/test";
import {
  COUNT_FOLLOWUP,
  DRAFT_FORM_ID,
  FORM_ID,
  HUB,
  MSG,
  RESPONSE_ID,
  REVIEW_ID,
  SECOND_FORM_ID,
  STUDENT,
  TIME,
  TITLE,
  analysisFor,
  analysisUuid,
  button,
  heading,
  link,
  makeForm,
  noStorage,
  open,
  pickerText,
  settle,
  setup,
  statusWith,
  tab,
  type Ctx,
} from "./adm08Api";

const ANALYSIS_ID = analysisUuid(1);
const DONE_RESPONSE =
  "Response deleted. The form, the respondent's account and stored analyses were not changed. The respondent can submit again only if the form is open.";
const NOT_FOUND_RESPONSE =
  "This response was not found. It may already have been deleted, or it does not belong to this form.";
const DONE_ANALYSIS =
  "Analysis deleted. The original feedback responses and forms were not changed.";
const OLD_ADDRESS = /\/admin\/(feedback(\/|$|\?)|announcements)/;

/** Record every address the single page visits (push, replace and full loads). */
function trackUrls(page: Page) {
  const urls: string[] = [];
  page.on("framenavigated", (frame) => {
    if (frame === page.mainFrame()) urls.push(frame.url());
  });
  return urls;
}
const expectNoOldAddress = (urls: string[]) =>
  expect(urls.filter((u) => OLD_ADDRESS.test(new URL(u).pathname + new URL(u).search))).toEqual([]);

async function arrange(page: Page, over: Parameters<typeof setup>[1] = {}) {
  return setup(page, {
    forms: [
      makeForm(FORM_ID, TITLE, "open", 2),
      makeForm(SECOND_FORM_ID, "Closed form", "closed", 3),
      makeForm(DRAFT_FORM_ID, "Draft form", "draft", 0),
    ],
    analyses: [analysisFor(1, "complete")],
    followUp: 4,
    ...over,
  });
}
const badge = (page: Page, name: string) =>
  tab(page, name).locator("span[aria-hidden='true']");
const selectAllBox = (page: Page, n: number) =>
  page.getByRole("checkbox", { name: `Select all ${n} responses`, exact: true });
async function chooseAnalysisForm(page: Page) {
  await page.getByRole("combobox", { name: "Feedback form" }).click();
  await page.getByRole("option", { name: TITLE }).click();
}
async function composeAndReview(page: Page) {
  await page.getByRole("textbox", { name: "Subject", exact: true }).fill("A subject");
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("A message.");
  await button(page, "Review message").click();
  await expect(heading(page, "Review message")).toBeVisible();
}
const confirmSend = (page: Page) => button(page, "Confirm send");

// ================================================================ J1 Forms
test("adm08 J1 Forms: list row, Edit draft, New feedback form with first-save replace, audience review, publish, close, Review responses", async ({
  page,
}) => {
  const urls = trackUrls(page);
  const ctx = await arrange(page);
  await open(page, `${HUB}/forms`);
  await expect(heading(page, "Feedback forms")).toBeVisible();
  // list row opens detail (push)
  await link(page, `${TITLE} · Open · Responses: 2`).click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms/${FORM_ID}$`));
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
  // draft detail, Edit draft
  await page.getByRole("link", { name: /^Draft form/ }).click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms/${DRAFT_FORM_ID}$`));
  await link(page, "Edit draft").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms/${DRAFT_FORM_ID}/edit$`));
  // New feedback form, then the first save replaces /forms/new
  await tab(page, "Forms").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
  await link(page, "New feedback form").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms/new$`));
  await page.getByRole("textbox", { name: "Form title", exact: true }).fill("Journey form");
  await button(page, "Add question").click();
  await page.getByRole("textbox", { name: "Question 1 prompt", exact: true }).fill("Your feedback?");
  const gets = ctx.of("GET").length;
  await button(page, "Save draft").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms/[^/]+$`));
  await expect(page).not.toHaveURL(/\/forms\/new$/);
  await expect(statusWith(page, "Draft saved.")).toBeVisible();
  expect(ctx.of("POST", "/forms")).toHaveLength(1);
  expect(
    ctx.of("GET").slice(gets).filter((r) => /\/forms\/[^/]+$/.test(r.path)),
  ).toHaveLength(0); // hand-off without a follow-up GET
  await page.goBack(); // replace: Back skips /forms/new
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms$`));
  // audience review and publish on the draft
  await page.goto(`${HUB}/forms/${DRAFT_FORM_ID}`);
  await button(page, "Review audience").click();
  const dialog = page.getByRole("dialog", { name: "Review audience", exact: true });
  await dialog
    .getByRole("checkbox", { name: `${STUDENT.display_name} (${STUDENT.id})`, exact: true })
    .check();
  await dialog.getByRole("button", { name: "Review selected recipients", exact: true }).click();
  await dialog.getByRole("button", { name: "Publish form", exact: true }).click();
  await expect.poll(() => ctx.of("POST", "/publish").length).toBe(1);
  // close an open form
  await page.goto(`${HUB}/forms/${FORM_ID}`);
  await button(page, "Close collection").click();
  await page
    .getByRole("dialog", { name: "Close collection", exact: true })
    .getByRole("button", { name: "Confirm close", exact: true })
    .click();
  await expect(statusWith(page, "Collection closed.")).toBeVisible();
  expect(ctx.of("POST", "/close")).toHaveLength(1);
  // Review responses goes to the hub list
  await link(page, "Review responses").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses/${FORM_ID}$`));
  expectNoOldAddress(urls);
});

// ================================================================ J2 guard
test("adm08 J2 dirty editor: browser Back shows the dialog; Keep editing stays; Discard leaves", async ({
  page,
}) => {
  await arrange(page);
  await open(page, `${HUB}/forms`);
  await link(page, "New feedback form").click();
  await page.getByRole("textbox", { name: "Form title", exact: true }).fill("Dirty");
  await page.goBack();
  const dialog = page.getByRole("dialog", { name: MSG.discard, exact: true });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Keep editing", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/forms/new$`));
  await expect(page.getByRole("textbox", { name: "Form title", exact: true })).toHaveValue("Dirty");
});

// ================================================================ J3 Responses
test("adm08 J3 Responses: chooser to list to detail, Choose another form, Back sequence", async ({
  page,
}) => {
  const urls = trackUrls(page);
  const ctx = await arrange(page);
  await open(page, `${HUB}/responses`);
  await settle(ctx);
  await page
    .getByRole("combobox", { name: "Feedback form", exact: true })
    .selectOption({ label: `${TITLE} · Open · Responses: 2` });
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses/${FORM_ID}$`));
  await expect(heading(page, "Submitted responses", 2)).toBeVisible();
  const row = link(page, `Response ${RESPONSE_ID} · ${STUDENT.display_name} · ${TIME}`);
  await row.click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses/${FORM_ID}/${RESPONSE_ID}$`));
  await expect(heading(page, "Feedback response")).toBeVisible();
  expect(ctx.of("GET", `/responses/${RESPONSE_ID}`)).toHaveLength(1);
  await expect(link(page, "Respond to feedback")).toHaveAttribute(
    "href",
    `${HUB}/follow-up/reply/${FORM_ID}/${RESPONSE_ID}`,
  );
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses/${FORM_ID}$`));
  await link(page, "Choose another form").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses$`));
  await page.goBack();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses$`));
  expectNoOldAddress(urls);
});

test("adm08 J3 the response list in the hub has Choose another form before the Submitted responses heading", async ({
  page,
}) => {
  await arrange(page);
  await open(page, `${HUB}/responses/${FORM_ID}`);
  const choose = await link(page, "Choose another form").boundingBox();
  const head = await heading(page, "Submitted responses", 2).boundingBox();
  expect(choose!.y).toBeLessThan(head!.y);
});

// ================================================================ J3b / AC27 shortcut
test("adm08 AC27 J3b: Analyse this form sits after Choose another form, pushes /analysis?form=, sends nothing itself, preselects, generates and ticks nothing, Back returns to the list", async ({
  page,
}) => {
  const urls = trackUrls(page);
  const ctx = await arrange(page);
  await open(page, `${HUB}/responses/${FORM_ID}`);
  await settle(ctx);
  const analyse = link(page, "Analyse this form");
  await expect(analyse).toHaveAttribute(
    "href",
    `${HUB}/analysis?form=${encodeURIComponent(FORM_ID)}`,
  );
  const a = await link(page, "Choose another form").boundingBox();
  const b = await analyse.boundingBox();
  expect(b!.x > a!.x || b!.y > a!.y).toBe(true);
  const mark = ctx.mark();
  await analyse.click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis\\?form=${FORM_ID}$`));
  await expect(heading(page, "Feedback analysis")).toBeVisible();
  await expect.poll(async () => pickerText(page)).toContain(TITLE);
  await expect(selectAllBox(page, 2)).toBeVisible();
  await expect(page.getByRole("checkbox", { checked: true })).toHaveCount(0);
  await expect(page.getByText(MSG.notAvailableForAnalysis)).toHaveCount(0);
  expect(ctx.of("POST")).toHaveLength(0);
  expect(ctx.since(mark).filter((r) => r.path.endsWith("/response-count"))).toHaveLength(1);
  expect(ctx.since(mark).filter((r) => r.path.endsWith(`${FORM_ID}/responses`))).toHaveLength(1);
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses/${FORM_ID}$`));
  expectNoOldAddress(urls);
});

test("adm08 AC27 preselection equals the manual choice in requests", async ({ page }) => {
  const ctx = await arrange(page);
  await open(page, `${HUB}/analysis`);
  await expect(heading(page, "Feedback analysis")).toBeVisible();
  await settle(ctx);
  const m0 = ctx.mark();
  await chooseAnalysisForm(page);
  await expect(selectAllBox(page, 2)).toBeVisible();
  await page.waitForTimeout(300);
  const manual = ctx.since(m0).map((r) => `${r.method} ${r.path}${r.search}`).sort();
  const m1 = ctx.mark();
  await page.goto(`${HUB}/analysis?form=${FORM_ID}`);
  await expect.poll(async () => pickerText(page)).toContain(TITLE);
  await expect(selectAllBox(page, 2)).toBeVisible();
  await page.waitForTimeout(300);
  const linked = ctx
    .since(m1)
    .filter((r) => r.path.includes(`/forms/${FORM_ID}/`))
    .map((r) => `${r.method} ${r.path}${r.search}`)
    .sort();
  expect(linked).toEqual(manual.filter((k) => k.includes(`/forms/${FORM_ID}/`)));
  expect(linked.length).toBeGreaterThan(0);
});

test("adm08 AC27 uppercase UUID is accepted (case-insensitive canonical compare)", async ({ page }) => {
  await arrange(page);
  await open(page, `${HUB}/analysis?form=${FORM_ID.toUpperCase()}`);
  await expect.poll(async () => pickerText(page)).toContain(TITLE);
  await expect(page.getByText(MSG.notAvailableForAnalysis)).toHaveCount(0);
});

for (const [name, value] of [
  ["an unknown form id", "a2000000-0000-4000-8000-0000000000ee"],
  ["a draft form id", DRAFT_FORM_ID],
  ["a malformed id", "not-a-uuid"],
  ["a traversal string", "../"],
  ["an encoded traversal string", "..%2f..%2fadmin"],
  ["script text", "%3Cscript%3Ewindow.__x%3D1%3C%2Fscript%3E"],
  ["a very long value", "a".repeat(3000)],
  ["a repeated value", `${FORM_ID}&form=${DRAFT_FORM_ID}`],
] as const) {
  test(`adm08 AC27 ${name} shows the not-available status, preselects nothing and sends no extra request`, async ({
    page,
  }) => {
    const ctx = await arrange(page);
    await open(page, `${HUB}/analysis?form=${value}`);
    await expect(statusWith(page, MSG.notAvailableForAnalysis)).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    expect(await pickerText(page)).not.toContain(TITLE);
    await page.waitForTimeout(300);
    expect(ctx.of("GET", "/response-count")).toHaveLength(0);
    expect(ctx.of("POST")).toHaveLength(0);
    expect(
      await page.evaluate(() => (window as unknown as { __x?: number }).__x),
    ).toBeUndefined();
    expect(await noStorage(page)).toBe(0);
  });
}

test("adm08 AC27 tab click goes to /analysis with no query and no preselection; refresh repeats the preselection", async ({
  page,
}) => {
  await arrange(page);
  await open(page, `${HUB}/analysis?form=${FORM_ID}`);
  await expect.poll(async () => pickerText(page)).toContain(TITLE);
  await page.reload();
  await expect.poll(async () => pickerText(page)).toContain(TITLE);
  await tab(page, "Responses").click();
  await tab(page, "Analysis").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis$`));
  expect(await pickerText(page)).not.toContain(TITLE);
  await expect(page.getByText(MSG.notAvailableForAnalysis)).toHaveCount(0);
});

test("adm08 AC27 the link is absent on the old route", async ({ page }) => {
  await arrange(page);
  await page.goto(`/admin/feedback/${FORM_ID}/responses`);
  await expect(heading(page, "Submitted responses", 2)).toBeVisible();
  await expect(link(page, "Analyse this form")).toHaveCount(0);
});

// ================================================================ J4 response delete
const trigger = (page: Page) => button(page, "Delete response");
const confirmDelete = (page: Page) => button(page, "Delete permanently");

test("adm08 J4 response delete: dialog, one DELETE on double click, replace to the hub list with status and focus", async ({
  page,
}) => {
  const urls = trackUrls(page);
  const ctx = await arrange(page);
  ctx.steps.push({ method: "DELETE", hold: true });
  await open(page, `${HUB}/responses/${FORM_ID}/${RESPONSE_ID}`);
  await trigger(page).click();
  const dialog = page.getByRole("alertdialog", { name: "Delete this response permanently?" });
  await expect(dialog).toBeVisible();
  await expect(button(page, "Cancel")).toBeFocused();
  await confirmDelete(page).dblclick();
  expect(ctx.of("DELETE")).toHaveLength(1);
  ctx.release();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses/${FORM_ID}$`));
  await expect(statusWith(page, DONE_RESPONSE)).toBeVisible();
  await expect(heading(page, "Submitted responses", 2)).toBeFocused();
  expect(ctx.of("DELETE")).toHaveLength(1);
  await page.goBack();
  await expect(page).not.toHaveURL(new RegExp(`${RESPONSE_ID}$`));
  expectNoOldAddress(urls);
});

test("adm08 J4 response delete answered 404 closes the dialog and replaces to the hub list with the not-found status", async ({
  page,
}) => {
  const ctx = await arrange(page);
  ctx.steps.push({
    method: "DELETE",
    status: 404,
    code: "feedback_response_not_found",
    json: { detail: { code: "feedback_response_not_found", message: NOT_FOUND_RESPONSE } },
  });
  await open(page, `${HUB}/responses/${FORM_ID}/${RESPONSE_ID}`);
  await trigger(page).click();
  await confirmDelete(page).click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses/${FORM_ID}$`));
  await expect(statusWith(page, NOT_FOUND_RESPONSE)).toBeVisible();
});

// ================================================================ J5 / J6 Analysis
test("adm08 J5 Analysis: select, Select all, Generate replaces to /analysis/{id}, polling, evidence chip push, Back and Forward, Back links", async ({
  page,
}) => {
  const urls = trackUrls(page);
  const ctx = await arrange(page);
  await open(page, `${HUB}/analysis`);
  await chooseAnalysisForm(page);
  await selectAllBox(page, 2).check();
  const generated = button(page, "Generate analysis");
  await generated.click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis/[^/?]+$`));
  expect(ctx.of("POST", "/analyses")).toHaveLength(1);
  await page.goBack(); // replace: Back does not return to the selection with the form
  await expect(page).not.toHaveURL(new RegExp(`${HUB}/analysis/[^/?]+$`));
  await open(page, `${HUB}/analysis`);
  await page.getByRole("link", { name: new RegExp(`^${TITLE}, .+, \\d+ responses, AI complete$`) }).click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis/${ANALYSIS_ID}$`));
  const gets = () => ctx.of("GET", `/analyses/${ANALYSIS_ID}`).length;
  await expect.poll(gets).toBe(1);
  await link(page, "Response R3").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis/${ANALYSIS_ID}/responses/R3$`));
  await expect(heading(page, "Response R3")).toBeVisible();
  await link(page, "Back to analysis").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis/${ANALYSIS_ID}$`));
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/responses/R3$`));
  await page.goForward();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis/${ANALYSIS_ID}$`));
  await link(page, "Back to Feedback analysis").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis$`));
  expectNoOldAddress(urls);
});

test("adm08 J6 analysis delete from the result replaces to /analysis with the status; from the list removes the row", async ({
  page,
}) => {
  const urls = trackUrls(page);
  const ctx = await arrange(page, { analyses: [analysisFor(1), analysisFor(2)] });
  await open(page, `${HUB}/analysis/${ANALYSIS_ID}`);
  await button(page, "Delete analysis").click();
  await confirmDelete(page).click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis$`));
  await expect(statusWith(page, DONE_ANALYSIS)).toBeVisible();
  expect(ctx.of("DELETE")).toHaveLength(1);
  await page.goBack();
  await expect(page).not.toHaveURL(new RegExp(ANALYSIS_ID));
  await open(page, `${HUB}/analysis`);
  await page.getByRole("button", { name: new RegExp(`^Delete analysis, ${TITLE}, `) }).first().click();
  await confirmDelete(page).click();
  await expect(statusWith(page, DONE_ANALYSIS)).toBeVisible();
  expect(ctx.of("DELETE")).toHaveLength(2);
  expectNoOldAddress(urls);
});

// ================================================================ J7 / J8 Follow-up
test("adm08 J7 announcement: compose, review (?review= replace), send, receipt, New announcement; refresh with ?review= reads once and never sends", async ({
  page,
}) => {
  const urls = trackUrls(page);
  const ctx = await arrange(page);
  await open(page, `${HUB}/follow-up`);
  await expect(heading(page, "New announcement")).toBeVisible();
  await expect(page.getByText(MSG.followUpNote, { exact: true })).toBeVisible();
  await composeAndReview(page);
  await expect(page).toHaveURL(new RegExp(`${HUB}/follow-up\\?review=${REVIEW_ID}$`));
  await expect(page.getByText(MSG.followUpNote)).toHaveCount(0); // note only without a review query
  await page.reload();
  await expect(heading(page, "Review message")).toBeVisible();
  expect(ctx.of("GET", REVIEW_ID)).toHaveLength(1);
  expect(ctx.of("POST", "/send")).toHaveLength(0);
  await confirmSend(page).click();
  await expect(heading(page, "Message sent")).toBeVisible();
  expect(ctx.of("POST", "/send")).toHaveLength(1);
  await button(page, "New announcement").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/follow-up$`));
  await expect(page.getByRole("textbox", { name: "Subject", exact: true })).toHaveValue("");
  expect(ctx.of("POST", "/send")).toHaveLength(1);
  expectNoOldAddress(urls);
});

test("adm08 J8 reply: Respond to feedback pushes the hub reply URL, review, receipt, Back to feedback pushes the hub response detail", async ({
  page,
}) => {
  const urls = trackUrls(page);
  const ctx = await arrange(page);
  await open(page, `${HUB}/responses/${FORM_ID}/${RESPONSE_ID}`);
  await link(page, "Respond to feedback").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/follow-up/reply/${FORM_ID}/${RESPONSE_ID}$`));
  await expect(tab(page, "Follow-up")).toHaveAttribute("aria-selected", "true");
  await expect(heading(page, "Respond to feedback")).toBeVisible();
  await expect(page.getByText(`Recipient: ${STUDENT.display_name} (student)`, { exact: true })).toBeVisible();
  expect(ctx.of("GET", "/recipient")).toHaveLength(1);
  await composeAndReview(page);
  await expect(page).toHaveURL(new RegExp(`/reply/${FORM_ID}/${RESPONSE_ID}\\?review=${REVIEW_ID}$`));
  await confirmSend(page).click();
  await expect(heading(page, "Message sent")).toBeVisible();
  await link(page, "Back to feedback").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/responses/${FORM_ID}/${RESPONSE_ID}$`));
  expectNoOldAddress(urls);
});

// ================================================================ AC29 event-driven counts
async function mounted(page: Page, over: Parameters<typeof setup>[1] = {}) {
  const ctx = await arrange(page, over);
  return ctx;
}
async function deltas(ctx: Ctx, mark: { f: number; a: number; u: number }) {
  return {
    f: ctx.formsCountGets().length - mark.f,
    a: ctx.analysesCountGets().length - mark.a,
    u: ctx.followUpGets().length - mark.u,
  };
}
const snap = (ctx: Ctx) => ({
  f: ctx.formsCountGets().length,
  a: ctx.analysesCountGets().length,
  u: ctx.followUpGets().length,
});
const settled = async (page: Page) => page.waitForTimeout(400);

test("adm08 AC29 create form adds exactly one forms-list GET and updates the Forms badge description", async ({
  page,
}) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/forms/new`);
  await settle(ctx);
  const before = snap(ctx);
  await page.getByRole("textbox", { name: "Form title", exact: true }).fill("Counted form");
  await button(page, "Add question").click();
  await page.getByRole("textbox", { name: "Question 1 prompt", exact: true }).fill("Q?");
  await button(page, "Save draft").click();
  await expect(statusWith(page, "Draft saved.")).toBeVisible();
  await settled(page);
  expect(await deltas(ctx, before)).toEqual({ f: 1, a: 0, u: 0 });
  await expect(tab(page, "Forms")).toHaveAccessibleDescription("1 open form, 2 drafts");
});

test("adm08 AC29 Save draft on an existing form, preview creation and announcement send add no count request", async ({
  page,
}) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/forms/${DRAFT_FORM_ID}/edit`);
  await settle(ctx);
  const before = snap(ctx);
  await button(page, "Save draft").click();
  await expect.poll(() => ctx.of("PUT").length).toBe(1);
  await settled(page);
  expect(await deltas(ctx, before)).toEqual({ f: 0, a: 0, u: 0 });
  await tab(page, "Follow-up").click();
  await composeAndReview(page);
  await confirmSend(page).click();
  await expect(heading(page, "Message sent")).toBeVisible();
  await settled(page);
  expect(await deltas(ctx, before)).toEqual({ f: 0, a: 0, u: 0 });
});

test("adm08 AC29 publish and close each add exactly one forms-list GET; Forms badge follows", async ({
  page,
}) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/forms/${DRAFT_FORM_ID}`);
  await settle(ctx);
  let before = snap(ctx);
  await button(page, "Review audience").click();
  const dialog = page.getByRole("dialog", { name: "Review audience", exact: true });
  await dialog
    .getByRole("checkbox", { name: `${STUDENT.display_name} (${STUDENT.id})`, exact: true })
    .check();
  await dialog.getByRole("button", { name: "Review selected recipients", exact: true }).click();
  await dialog.getByRole("button", { name: "Publish form", exact: true }).click();
  await expect(badge(page, "Forms")).toHaveText("2");
  expect(await deltas(ctx, before)).toEqual({ f: 1, a: 0, u: 0 });
  before = snap(ctx);
  await page.goto(`${HUB}/forms/${FORM_ID}`);
  await settle(ctx);
  before = snap(ctx);
  await button(page, "Close collection").click();
  await page
    .getByRole("dialog", { name: "Close collection", exact: true })
    .getByRole("button", { name: "Confirm close", exact: true })
    .click();
  await expect(statusWith(page, "Collection closed.")).toBeVisible();
  await expect(badge(page, "Forms")).toHaveText("1");
  expect(await deltas(ctx, before)).toEqual({ f: 1, a: 0, u: 0 });
});

test("adm08 AC29 response delete adds one forms GET and one follow-up GET; Responses and Follow-up badges drop", async ({
  page,
}) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/responses/${FORM_ID}/${RESPONSE_ID}`);
  await settle(ctx);
  await expect(badge(page, "Follow-up")).toHaveText("4");
  await expect(badge(page, "Responses")).toHaveText("5");
  const before = snap(ctx);
  await trigger(page).click();
  await confirmDelete(page).click();
  await expect(statusWith(page, DONE_RESPONSE)).toBeVisible();
  await settled(page);
  expect(await deltas(ctx, before)).toEqual({ f: 1, a: 0, u: 1 });
  await expect(badge(page, "Follow-up")).toHaveText("3");
  await expect(badge(page, "Responses")).toHaveText("4");
});

test("adm08 AC29 a response delete answered 404 still refetches both sources", async ({ page }) => {
  const ctx = await mounted(page);
  ctx.steps.push({
    method: "DELETE",
    status: 404,
    json: { detail: { code: "feedback_response_not_found", message: NOT_FOUND_RESPONSE } },
  });
  await open(page, `${HUB}/responses/${FORM_ID}/${RESPONSE_ID}`);
  await settle(ctx);
  const before = snap(ctx);
  await trigger(page).click();
  await confirmDelete(page).click();
  await expect(statusWith(page, NOT_FOUND_RESPONSE)).toBeVisible();
  await settled(page);
  expect(await deltas(ctx, before)).toEqual({ f: 1, a: 0, u: 1 });
});

test("adm08 AC29 generate analysis and analysis delete each add exactly one analyses GET (limit=50); Analysis badge follows", async ({
  page,
}) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/analysis`);
  await settle(ctx);
  await expect(badge(page, "Analysis")).toHaveText("1");
  let before = snap(ctx);
  await chooseAnalysisForm(page);
  await selectAllBox(page, 2).check();
  await button(page, "Generate analysis").click();
  await expect(page).toHaveURL(new RegExp(`${HUB}/analysis/[^/?]+$`));
  await expect(badge(page, "Analysis")).toHaveText("2");
  await settled(page);
  expect(await deltas(ctx, before)).toEqual({ f: 0, a: 1, u: 0 });
  await page.goto(`${HUB}/analysis/${ANALYSIS_ID}`);
  await settle(ctx);
  before = snap(ctx);
  await button(page, "Delete analysis").click();
  await confirmDelete(page).click();
  await expect(statusWith(page, DONE_ANALYSIS)).toBeVisible();
  await expect(badge(page, "Analysis")).toHaveText("1");
  await settled(page);
  expect(await deltas(ctx, before)).toEqual({ f: 0, a: 1, u: 0 });
});

test("adm08 AC29 an analysis delete answered 404 still refetches the analyses count", async ({ page }) => {
  const ctx = await mounted(page);
  ctx.steps.push({
    method: "DELETE",
    status: 404,
    json: { detail: { code: "analysis_not_found", message: "That analysis is not available. It does not exist or is not in your history." } },
  });
  await open(page, `${HUB}/analysis/${ANALYSIS_ID}`);
  await settle(ctx);
  const before = snap(ctx);
  await button(page, "Delete analysis").click();
  await confirmDelete(page).click();
  await expect.poll(async () => (await deltas(ctx, before)).a).toBe(1);
});

test("adm08 AC29 sending a reply adds exactly one follow-up GET and lowers the badge; an announcement adds none", async ({
  page,
}) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/follow-up/reply/${FORM_ID}/${RESPONSE_ID}`);
  await settle(ctx);
  const before = snap(ctx);
  await composeAndReview(page);
  await confirmSend(page).click();
  await expect(heading(page, "Message sent")).toBeVisible();
  await expect(badge(page, "Follow-up")).toHaveText("3");
  await settled(page);
  expect(await deltas(ctx, before)).toEqual({ f: 0, a: 0, u: 1 });
});

test("adm08 AC29 opening a receipt for an already sent message with ?review= emits nothing", async ({ page }) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/follow-up/reply/${FORM_ID}/${RESPONSE_ID}`);
  await composeAndReview(page);
  await confirmSend(page).click();
  await expect(heading(page, "Message sent")).toBeVisible();
  await settle(ctx);
  await settled(page);
  const before = snap(ctx);
  await page.reload();
  await expect(heading(page, "Message sent")).toBeVisible();
  await settled(page);
  // the reload remounts the hub: exactly the three mount counts, no event-driven extra
  expect(await deltas(ctx, before)).toEqual({ f: 1, a: 1, u: 1 });
});

for (const [name, fail] of [
  ["500", { status: 500, code: "feedback_error" }],
  ["409", { status: 409, code: "feedback_conflict" }],
  ["network", { abort: true }],
] as const) {
  test(`adm08 AC29 a failed publish (${name}) adds no count request`, async ({ page }) => {
    const ctx = await mounted(page);
    ctx.steps.push({ method: "POST", suffix: "/publish", ...fail });
    await open(page, `${HUB}/forms/${DRAFT_FORM_ID}`);
    await settle(ctx);
    const before = snap(ctx);
    await button(page, "Review audience").click();
    const dialog = page.getByRole("dialog", { name: "Review audience", exact: true });
    await dialog
      .getByRole("checkbox", { name: `${STUDENT.display_name} (${STUDENT.id})`, exact: true })
      .check();
    await dialog.getByRole("button", { name: "Review selected recipients", exact: true }).click();
    await dialog.getByRole("button", { name: "Publish form", exact: true }).click();
    await expect.poll(() => ctx.of("POST", "/publish").length).toBe(1);
    await settled(page);
    expect(await deltas(ctx, before)).toEqual({ f: 0, a: 0, u: 0 });
    await page.keyboard.press("Escape"); // the modal stays open after the failure and hides the tab
    await expect(dialog).toHaveCount(0);
    await expect(badge(page, "Forms")).toHaveText("1");
  });
}

test("adm08 AC29 a failed refetch keeps the previous badge and shows no text; a later success replaces it", async ({
  page,
}) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/responses/${FORM_ID}/${RESPONSE_ID}`);
  await settle(ctx);
  await expect(badge(page, "Follow-up")).toHaveText("4");
  ctx.steps.push({ method: "GET", suffix: "/followup-counts", status: 500, code: "MESSAGING_ERROR" });
  await trigger(page).click();
  await confirmDelete(page).click();
  await expect(statusWith(page, DONE_RESPONSE)).toBeVisible();
  await settled(page);
  await expect(badge(page, "Follow-up")).toHaveText("4"); // stale beats blank
  await expect(tab(page, "Follow-up")).toHaveAccessibleDescription("4 responses without a reply");
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(button(page, "Retry")).toHaveCount(0);
});

for (const [name, fail] of [
  ["429", { status: 429, code: "MESSAGING_RATE_LIMITED" }],
  ["network", { abort: true }],
] as const) {
  test(`adm08 AC29 a refetch failing with ${name} keeps the old value`, async ({ page }) => {
    const ctx = await mounted(page);
    await open(page, `${HUB}/follow-up/reply/${FORM_ID}/${RESPONSE_ID}`);
    await settle(ctx);
    ctx.steps.push({ method: "GET", suffix: "/followup-counts", ...fail });
    await composeAndReview(page);
    await confirmSend(page).click();
    await expect(heading(page, "Message sent")).toBeVisible();
    await settled(page);
    await expect(badge(page, "Follow-up")).toHaveText("4");
  });
}

test("adm08 AC29 a 401 on a refetch goes to sign-in", async ({ page }) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/follow-up/reply/${FORM_ID}/${RESPONSE_ID}`);
  await settle(ctx);
  ctx.steps.push({ method: "GET", suffix: "/followup-counts", status: 401, code: "unauthenticated" });
  await composeAndReview(page);
  await confirmSend(page).click();
  await expect(page).toHaveURL(/\/login/);
  expect(await noStorage(page)).toBe(0);
});

test("adm08 AC29 latest wins: a late answer of an older refetch never replaces the newer value", async ({
  page,
}) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/responses/${FORM_ID}/${RESPONSE_ID}`);
  await settle(ctx);
  // first reply send: its refetch is held and would answer 50 late
  await link(page, "Respond to feedback").click();
  ctx.steps.push({
    method: "GET",
    suffix: "/followup-counts",
    hold: true,
    json: { unanswered_responses: 50 },
  });
  await composeAndReview(page);
  await confirmSend(page).click();
  await expect(heading(page, "Message sent")).toBeVisible();
  await expect.poll(() => ctx.followUpGets().length).toBe(2);
  // second send while the first refetch is still pending
  await link(page, "Back to feedback").click();
  await link(page, "Respond to feedback").click();
  await composeAndReview(page);
  await confirmSend(page).click();
  await expect(heading(page, "Message sent")).toBeVisible();
  await expect.poll(() => ctx.followUpGets().length).toBe(3);
  await expect(badge(page, "Follow-up")).toHaveText("2");
  ctx.release(); // the older answer (50) arrives late
  await settled(page);
  await expect(badge(page, "Follow-up")).toHaveText("2");
});

test("adm08 AC29 the same actions on the old routes send no count request and behave as before", async ({
  page,
}) => {
  const ctx = await mounted(page);
  await page.goto(`/admin/feedback/${FORM_ID}/responses/${RESPONSE_ID}/reply`);
  await composeAndReview(page);
  await confirmSend(page).click();
  await expect(heading(page, "Message sent")).toBeVisible();
  await page.goto(`/admin/feedback/${FORM_ID}/responses/${RESPONSE_ID}`);
  await trigger(page).click();
  await confirmDelete(page).click();
  await expect(statusWith(page, DONE_RESPONSE)).toBeVisible();
  await settled(page);
  expect(ctx.followUpGets()).toHaveLength(0);
  expect(ctx.analysesCountGets()).toHaveLength(0);
  expect(ctx.requests.filter((r) => r.path === COUNT_FOLLOWUP)).toHaveLength(0);
});

test("adm08 AC29 changes by an unseen other admin are not reflected after tab clicks, only after reload", async ({
  page,
}) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/forms`);
  await settle(ctx);
  await expect(badge(page, "Follow-up")).toHaveText("4");
  ctx.followUp = 9;
  for (const name of ["Responses", "Analysis", "Follow-up", "Forms"])
    await tab(page, name).click();
  await settled(page);
  await expect(badge(page, "Follow-up")).toHaveText("4");
  await page.reload();
  await expect(badge(page, "Follow-up")).toHaveText("9");
  expect(await noStorage(page)).toBe(0);
});

test("adm08 AC29 leaving the hub leaves no pending or stray count request", async ({ page }) => {
  const ctx = await mounted(page);
  await open(page, `${HUB}/follow-up/reply/${FORM_ID}/${RESPONSE_ID}`);
  await settle(ctx);
  await page.goto("/admin/overview");
  const before = snap(ctx);
  await settled(page);
  expect(await deltas(ctx, before)).toEqual({ f: 0, a: 0, u: 0 });
});

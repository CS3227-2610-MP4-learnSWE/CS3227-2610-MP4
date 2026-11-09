import { expect, test } from "@playwright/test";
import { STUDENT, TEACHER } from "./authApi";
import { MSG, ROOT, TITLE, chooseForm, setup, uuid } from "./adm03Api";

const PAGE = "/admin/feedback/analysis";
const generate = (page: import("@playwright/test").Page) =>
  page.getByRole("button", { name: "Generate analysis", exact: true });
const selectAll = (page: import("@playwright/test").Page, n = 137) =>
  page.getByRole("checkbox", { name: `Select all ${n} responses`, exact: true });

test("adm03 wrong role is redirected with no ADM-03 request; anonymous goes to sign in", async ({ page }) => {
  for (const user of [STUDENT, TEACHER]) {
    const ctx = await setup(page, { user });
    await page.goto(PAGE);
    await expect(page).not.toHaveURL(new RegExp(PAGE));
    expect(ctx.requests.filter((r) => r.path.startsWith(ROOT))).toHaveLength(0);
    await page.unrouteAll({ behavior: "ignoreErrors" });
  }
  const ctx = await setup(page, { user: null });
  await page.goto(PAGE);
  await expect(page).not.toHaveURL(new RegExp(PAGE + "$"));
  expect(ctx.requests).toHaveLength(0);
});

test("adm03 AC5 page load: one forms and one analyses request; nothing selected shows the exact alert and sends no POST", async ({ page }) => {
  const ctx = await setup(page);
  await page.goto(PAGE);
  await expect(page.getByRole("heading", { name: "Feedback analysis", level: 1, exact: true })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Feedback form" })).toBeVisible();
  expect(ctx.of("GET", "/forms")).toHaveLength(1);
  expect(ctx.analysesCalls()).toHaveLength(1);
  expect(ctx.analysesCalls()[0].query.get("limit")).toBe("20");
  await generate(page).click();
  await expect(page.getByRole("alert").filter({ hasText: MSG.selection })).toBeVisible();
  expect(ctx.of("POST")).toHaveLength(0);
  await expect(generate(page)).toBeEnabled();
});

test("adm03 AC18 Select all: counting state, label, checked and disabled rows, POST body, Clear selection", async ({ page }) => {
  const ctx = await setup(page);
  ctx.steps.push({ suffix: "/response-count", hold: true });
  await page.goto(PAGE);
  await chooseForm(page);
  await expect(page.getByText("Loading responses...")).toBeVisible();
  await expect(page.getByText("Counting responses...")).toBeVisible();
  ctx.release();
  expect(ctx.of("GET", "/responses")).toHaveLength(1);
  expect(ctx.of("GET", "/responses")[0].query.get("limit")).toBe("100");
  await expect(selectAll(page)).toBeEnabled();
  await selectAll(page).check();
  await expect(page.getByRole("checkbox", { name: "All 137 responses selected", exact: true })).toBeChecked();
  const row = page.getByRole("checkbox", { name: /^Select response from Person 1, submitted /, });
  await expect(row.first()).toBeChecked();
  await expect(row.first()).toBeDisabled();
  await expect(page.getByText("137 selected")).toBeVisible();
  await generate(page).click();
  await expect(page).toHaveURL(new RegExp(`${PAGE}/${uuid(901)}$`));
  const post = ctx.of("POST")[0];
  expect(post.body.select_all).toBe(true);
  expect(post.body.expected_count).toBe(137);
  expect("response_ids" in post.body).toBe(false);
  expect(String(post.body.request_id)).toMatch(/^[0-9a-f-]{36}$/);
});

test("adm03 Clear selection turns Select all off; Refresh list reloads list and count and keeps Select all on", async ({ page }) => {
  const ctx = await setup(page);
  await page.goto(PAGE);
  await chooseForm(page);
  await selectAll(page).check();
  ctx.total = 140;
  const before = ctx.requests.length;
  await page.getByRole("button", { name: "Refresh list", exact: true }).click();
  await expect(page.getByRole("checkbox", { name: "All 140 responses selected", exact: true })).toBeChecked();
  const added = ctx.requests.slice(before);
  expect(added.filter((r) => r.path.endsWith("/responses"))).toHaveLength(1);
  expect(added.filter((r) => r.path.endsWith("/response-count"))).toHaveLength(1);
  await page.getByRole("button", { name: "Clear selection", exact: true }).click();
  await expect(selectAll(page, 140)).not.toBeChecked();
  await expect(page.getByText("0 selected")).toBeVisible();
});

test("adm03 AC1 explicit ticks are kept across pages and sent as response_ids; Generate replaces history", async ({ page }) => {
  const ctx = await setup(page, { responses: 130 });
  await page.goto("/admin/feedback");
  await page.getByRole("link", { name: "Feedback analysis", exact: true }).click();
  await chooseForm(page);
  await page.getByRole("checkbox", { name: /^Select response from Person 1,/ }).first().check();
  await page.getByRole("checkbox", { name: /^Select response from Person 2,/ }).first().check();
  await expect(page.getByText("2 selected")).toBeVisible();
  await page.getByRole("button", { name: "Next page", exact: true }).click();
  await expect(page.getByRole("checkbox", { name: /^Select response from Person 101,/ })).toBeVisible();
  await page.getByRole("checkbox", { name: /^Select response from Person 101,/ }).check();
  await page.getByRole("button", { name: "Previous page", exact: true }).click();
  await expect(page.getByText("3 selected")).toBeVisible();
  expect(ctx.of("GET", "/responses")).toHaveLength(3);
  await generate(page).click();
  await expect(page).toHaveURL(new RegExp(`${PAGE}/${uuid(901)}$`));
  expect((ctx.of("POST")[0].body.response_ids as string[]).length).toBe(3);
  await page.goBack();
  await expect(page).toHaveURL(/\/admin\/feedback$/); // Generate success replaced the selection page entry
});

test("adm03 Generate is disabled and shows Starting... while pending and sends one POST even on double click", async ({ page }) => {
  const ctx = await setup(page);
  ctx.steps.push({ method: "POST", hold: true });
  await page.goto(PAGE);
  await chooseForm(page);
  await selectAll(page).check();
  await generate(page).dblclick();
  const busy = page.getByRole("button", { name: "Starting...", exact: true });
  await expect(busy).toBeDisabled();
  expect(ctx.of("POST")).toHaveLength(1);
  ctx.release();
  await expect(page).toHaveURL(new RegExp(`${PAGE}/`));
  expect(ctx.of("POST")).toHaveLength(1);
});

test("adm03 request_id is kept after a network failure and replaced after a server rejection", async ({ page }) => {
  const ctx = await setup(page);
  ctx.steps.push({ method: "POST", abort: true });
  ctx.steps.push({ method: "POST", status: 409, code: "analysis_in_progress", message: MSG.inProgress });
  await page.goto(PAGE);
  await chooseForm(page);
  await selectAll(page).check();
  await generate(page).click();
  await expect(page.getByRole("alert").filter({ hasText: MSG.generateNetwork })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "All 137 responses selected" })).toBeChecked();
  await generate(page).click();
  await expect(page.getByRole("alert").filter({ hasText: MSG.inProgress })).toBeVisible();
  await generate(page).click();
  await expect(page).toHaveURL(new RegExp(`${PAGE}/`));
  const ids = ctx.of("POST").map((r) => r.body.request_id);
  expect(ids).toHaveLength(3);
  expect(ids[1]).toBe(ids[0]);
  expect(ids[2]).not.toBe(ids[1]);
});

for (const [name, step, message] of [
  ["no_responses", { status: 422, code: "no_responses", message: "This form has no submitted responses, so there is nothing to analyse." }, "This form has no submitted responses, so there is nothing to analyse."],
  ["too_many_responses", { status: 422, code: "too_many_responses", message: "You selected 501 responses, but one analysis can cover at most 500. Select fewer responses." }, "You selected 501 responses, but one analysis can cover at most 500. Select fewer responses."],
  ["form_not_found", { status: 404, code: "form_not_found", message: "That form is not available. It may have been deleted. Choose another form." }, "That form is not available. It may have been deleted. Choose another form."],
  ["401", { status: 401, code: "unauthenticated", message: "x" }, MSG.expired],
  ["403", { status: 403, code: "forbidden", message: "x" }, MSG.forbidden],
] as const) {
  test(`adm03 Generate failure ${name} shows its exact message and keeps the selection`, async ({ page }) => {
    const ctx = await setup(page);
    ctx.steps.push({ method: "POST", ...step });
    await page.goto(PAGE);
    await chooseForm(page);
    await selectAll(page).check();
    await generate(page).click();
    if (name === "401") {
      await expect(page).toHaveURL(/sign-?in|login/i);
      await expect(page.getByText(message)).toBeVisible();
      return;
    }
    await expect(page.getByRole("alert").filter({ hasText: message })).toBeVisible();
    await expect(page.getByRole("checkbox", { name: "All 137 responses selected" })).toBeChecked();
    await expect(page.getByText(/something went wrong|an error occurred/i)).toHaveCount(0);
  });
}

test("adm03 load failures use their exact message with Retry that repeats only the failed request", async ({ page }) => {
  const ctx = await setup(page);
  ctx.steps.push({ suffix: "/forms", abort: true });
  await page.goto(PAGE);
  await expect(page.getByRole("alert").filter({ hasText: MSG.load("forms") })).toBeVisible();
  const before = ctx.requests.length;
  await page.getByRole("button", { name: "Retry" }).first().click();
  await expect(page.getByRole("combobox", { name: "Feedback form" })).toBeVisible();
  expect(ctx.requests.slice(before).filter((r) => r.path.endsWith("/forms"))).toHaveLength(1);
  expect(ctx.requests.slice(before).filter((r) => r.path.endsWith("/analyses"))).toHaveLength(0);
  ctx.steps.push({ suffix: "/response-count", abort: true });
  await chooseForm(page);
  await expect(page.getByRole("alert").filter({ hasText: MSG.load("the response count") })).toBeVisible();
  await expect(page.getByText("Counting responses...")).toBeVisible();
  const mark = ctx.requests.length;
  await page.getByRole("button", { name: "Retry" }).first().click();
  await expect(selectAll(page)).toBeEnabled();
  expect(ctx.requests.slice(mark).map((r) => r.path.split("/").pop())).toEqual(["response-count"]);
});

test("adm03 no responses: empty text and Select all hidden", async ({ page }) => {
  await setup(page, { responses: 0 });
  await page.goto(PAGE);
  await chooseForm(page);
  await expect(page.getByText("This form has no responses yet.")).toBeVisible();
  await expect(page.getByRole("checkbox", { name: /^Select all/ })).toHaveCount(0);
  void TITLE;
});

for (const width of [320, 390]) {
  test(`adm03 ${width}px selection page has no horizontal overflow`, async ({ page }) => {
    await setup(page);
    await page.setViewportSize({ width, height: 800 });
    await page.goto(PAGE);
    await chooseForm(page);
    await expect(selectAll(page)).toBeEnabled();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await expect(generate(page)).toBeVisible();
  });
}

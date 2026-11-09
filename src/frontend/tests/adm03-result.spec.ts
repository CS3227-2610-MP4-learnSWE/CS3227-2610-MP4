import { expect, test, type Page } from "@playwright/test";
import { STUDENT } from "./authApi";
import { COMPLETE_RESULT, MSG, ROOT, analysis, setup, uuid } from "./adm03Api";

const URL = (n: number) => `/admin/feedback/analysis/${uuid(n)}`;
const gets = (ctx: Awaited<ReturnType<typeof setup>>, n: number) =>
  ctx.of("GET", `/analyses/${uuid(n)}`);
const aiSection = (page: Page) =>
  page.getByRole("heading", { name: "AI analysis", level: 2, exact: true });

test("adm03 AC24 charts and tables show at once while the AI step runs", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "running")] });
  await page.goto(URL(1));
  await expect(page.getByRole("heading", { name: "Feedback analysis result", level: 1, exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Question results", level: 2 })).toBeVisible();
  await expect(page.getByText("Computed from the selected responses without AI.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "How clear were the deadlines?", level: 3 })).toBeVisible();
  const table = page.getByRole("table", { name: "Results for How clear were the deadlines?" });
  await expect(table.getByRole("columnheader")).toHaveText(["Option", "Responses", "Percent"]);
  await expect(table.getByRole("row")).toHaveCount(6);
  await expect(page.getByText("120 answered, 17 skipped")).toBeVisible();
  await expect(page.getByText("Mean 3.4, median 4")).toBeVisible();
  const slides = page.getByRole("table", { name: "Results for Which tools helped?" });
  await expect(slides.getByRole("row", { name: /Slides/ })).toContainText("70");
  await expect(page.getByText("100 answered, 37 skipped")).toBeVisible();
  await expect(page.getByText("90 answered, 47 skipped")).toBeVisible();
  expect(await table.locator('[aria-hidden="true"]').count()).toBeGreaterThan(0);
  const status = page.getByRole("status").filter({ hasText: "AI analysis running. Step 1 of 3: batch 2 of 2." });
  await expect(status).toBeVisible();
  const bar = page.getByRole("progressbar", { name: "AI analysis progress" });
  await expect(bar).toHaveAttribute("aria-valuenow", "1");
  await expect(bar).toHaveAttribute("aria-valuemax", "3");
  await expect(page.getByRole("link", { name: "Back to Feedback analysis" })).toBeVisible();
  expect(gets(ctx, 1)).toHaveLength(1);
});

test("adm03 AC22 the sampled notice appears only when N is below M, and the selection-change note when counts differ", async ({ page }) => {
  await setup(page, {
    analyses: [
      analysis(1, "complete", { free_text: { total: 412, used: 296 }, expected_count: 150, response_count: 137 }),
      analysis(2, "complete"),
    ],
  });
  await page.goto(URL(1));
  await expect(page.getByText("AI themes based on 296 of 412 free-text answers.")).toBeVisible();
  await expect(page.getByText("You selected 150 responses; 137 were analysed because responses changed after you opened the list.")).toBeVisible();
  await page.goto(URL(2));
  await expect(page.getByRole("heading", { name: "Summary", level: 3 })).toBeVisible();
  await expect(page.getByText(/AI themes based on/)).toHaveCount(0);
  await expect(page.getByText(/You selected \d+ responses; \d+ were analysed/)).toHaveCount(0);
});

test("adm03 AC2-4 complete result: sections, labels, evidence chips and plain-text rendering", async ({ page }) => {
  const evil = "<script>window.__pwned=1</script> **bold** <b>x</b>";
  const result = {
    ...COMPLETE_RESULT,
    summary: evil,
    themes: [{ title: evil, description: "d", evidence: ["R3"] }],
  };
  const ctx = await setup(page, { analyses: [analysis(1, "complete", { ai: { ...analysis(1, "complete").ai, result } })] });
  await page.goto(URL(1));
  await expect(page.getByRole("heading", { name: "Summary", level: 3 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recurring issues", level: 3 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Suggested improvements", level: 3 })).toBeVisible();
  await expect(page.getByText(evil).first()).toBeVisible(); // literal text, not markup
  expect(await page.evaluate(() => (window as unknown as { __pwned?: number }).__pwned)).toBeUndefined();
  await expect(page.locator("main b")).toHaveCount(0);
  await expect(page.getByText("Reported in feedback")).toBeVisible();
  await expect(page.getByText("Based on feedback")).toBeVisible();
  await expect(page.getByText("AI suggestion (no supporting feedback)")).toBeVisible();
  await expect(page.getByText("AI-generated. Check the supporting responses before acting.")).toBeVisible();
  const chip = page.getByRole("link", { name: "Response R3", exact: true });
  await expect(chip).toHaveText("R3");
  const before = ctx.requests.length;
  await chip.click();
  await expect(page).toHaveURL(new RegExp(`${URL(1)}/responses/R3$`));
  await expect(page.getByRole("heading", { name: "Response R3", level: 1, exact: true })).toBeVisible();
  expect(ctx.requests.slice(before).filter((r) => r.path.includes("/responses/R3"))).toHaveLength(1);
  expect(gets(ctx, 1)).toHaveLength(1); // opening a chip sends no analysis request
  await page.getByRole("link", { name: "Back to analysis", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`${URL(1)}$`));
  await expect.poll(() => gets(ctx, 1).length).toBe(2); // the result page reloads once
  await page.goBack(); // chips and Back links push entries
  await expect(page).toHaveURL(new RegExp(`${URL(1)}/responses/R3$`));
  await expect(page.getByRole("heading", { name: "Response R3", level: 1 })).toBeVisible();
  await page.waitForTimeout(300);
  expect(gets(ctx, 1)).toHaveLength(2); // Back adds no analysis request
});

test("adm03 evidence opened directly loads the analysis too; unavailable evidence shows only the message", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "complete")] });
  await page.goto(`${URL(1)}/responses/R1`);
  await expect(page.getByRole("heading", { name: "Response R1", level: 1 })).toBeVisible();
  await expect.poll(() => gets(ctx, 1).length).toBe(1);
  expect(ctx.of("GET", "/responses/R1")).toHaveLength(1);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Response R1", level: 1 })).toBeVisible();
  await expect.poll(() => gets(ctx, 1).length).toBe(2);
  expect(ctx.of("GET", "/responses/R1")).toHaveLength(2);
  ctx.steps.push({ suffix: "/responses/R9", status: 404, code: "evidence_not_found", message: MSG.evidenceNotFound });
  await page.goto(`${URL(1)}/responses/R9`);
  await expect(page.getByRole("alert").filter({ hasText: MSG.evidenceNotFound })).toBeVisible();
  await expect(page.getByText("Person 1")).toHaveCount(0);
});

for (const failure of [{ status: 500, code: "internal_error", message: "x" }, { abort: true }] as const) {
  test(`adm03 evidence opened directly still shows when the extra analysis GET fails (${"abort" in failure ? "abort" : failure.status}): no alert, no retry`, async ({ page }) => {
    const ctx = await setup(page, { analyses: [analysis(1, "complete")] });
    ctx.steps.push({ method: "GET", suffix: `/analyses/${uuid(1)}`, ...failure });
    await page.goto(`${URL(1)}/responses/R1`);
    await expect(page.getByRole("heading", { name: "Response R1", level: 1 })).toBeVisible();
    await expect.poll(() => gets(ctx, 1).length).toBe(1);
    await page.waitForTimeout(500);
    expect(gets(ctx, 1)).toHaveLength(1);
    expect(ctx.of("GET", "/responses/R1")).toHaveLength(1);
    await expect(page.getByRole("alert")).toHaveCount(0);
  });
}

for (const [name, error, text] of [
  ["ai_timeout", { code: "ai_timeout", message: MSG.aiTimeout, step: { kind: "batch", index: 2, total: 3 }, details: {} }, MSG.aiTimeout],
  ["rate_limited_minute", { code: "rate_limited_minute", message: MSG.aiRate, step: { kind: "batch", index: 3, total: 6 }, details: {} }, MSG.aiRate],
  ["ai_reply_invalid", { code: "ai_reply_invalid", message: MSG.aiInvalid, step: { kind: "merge", index: null, total: null }, details: {} }, MSG.aiInvalid],
  ["analysis_interrupted", { code: "analysis_interrupted", message: MSG.aiInterrupted, step: { kind: "batch", index: 2, total: 3 }, details: {} }, MSG.aiInterrupted],
] as const) {
  test(`adm03 AC6 AC24 AC31 failed AI step ${name}: its stored message only in the AI section, charts stay, no result`, async ({ page }) => {
    const base = analysis(1, "failed");
    await setup(page, { analyses: [analysis(1, "failed", { ai: { ...base.ai, error } })] });
    await page.goto(URL(1));
    await expect(page.getByRole("heading", { name: "Question results", level: 2 })).toBeVisible();
    await expect(page.getByText("Computed from the selected responses without AI.")).toBeVisible();
    await expect(page.getByRole("table", { name: "Results for How clear were the deadlines?" })).toBeVisible();
    const alert = page.getByRole("alert").filter({ hasText: text });
    await expect(alert).toHaveCount(1);
    await expect(page.getByText("Stopped at step 1 of 3. The statistics above are still correct.")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Summary", level: 3 })).toHaveCount(0);
    await expect(page.getByRole("progressbar")).toHaveCount(0);
    await expect(page.getByText(/something went wrong|an error occurred|unknown error/i)).toHaveCount(0);
    expect(await aiSection(page).count()).toBe(1);
  });
}

test("adm03 analysis_not_found shows its message with a link back", async ({ page }) => {
  await setup(page);
  await page.goto(URL(7));
  await expect(page.getByRole("alert").filter({ hasText: MSG.analysisNotFound })).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to Feedback analysis", exact: true })).toBeVisible();
});

test("adm03 load failure of the analysis offers Retry that repeats only that request", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "complete")] });
  ctx.steps.push({ suffix: `/analyses/${uuid(1)}`, abort: true });
  await page.goto(URL(1));
  await expect(page.getByRole("alert").filter({ hasText: MSG.load("the analysis") })).toBeVisible();
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByRole("heading", { name: "Question results", level: 2 })).toBeVisible();
  expect(gets(ctx, 1)).toHaveLength(2);
});

// ---- polling (fake clock) ----

async function running(page: Page, ctx: Awaited<ReturnType<typeof setup>>, states: ReturnType<typeof analysis>[]) {
  ctx.script.set(uuid(1), states);
  await page.clock.install();
  await page.goto(URL(1));
  await expect(page.getByRole("heading", { name: "Question results", level: 2 })).toBeVisible();
}

test("adm03 polling: one GET at mount, then one per 2 s while running, then stops at complete", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "running")] });
  const step = (done: number) => analysis(1, "running", { ai: { ...analysis(1).ai, progress: { done, total: 3, step: { kind: "batch", index: done + 1, total: 2 } } } });
  await running(page, ctx, [analysis(1, "running"), step(2), analysis(1, "complete")]);
  expect(gets(ctx, 1)).toHaveLength(1);
  await page.clock.runFor(1900);
  expect(gets(ctx, 1)).toHaveLength(1);
  await page.clock.runFor(200);
  await expect.poll(() => gets(ctx, 1).length).toBe(2);
  await expect(page.getByRole("status").filter({ hasText: "Step 2 of 3" })).toBeVisible();
  await page.clock.runFor(2100);
  await expect.poll(() => gets(ctx, 1).length).toBe(3);
  await expect(page.getByRole("heading", { name: "Summary", level: 3 })).toBeVisible();
  await page.clock.runFor(10_000);
  expect(gets(ctx, 1)).toHaveLength(3);
});

test("adm03 polling stops at failed and never goes backwards", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "running")] });
  const behind = analysis(1, "running", { ai: { ...analysis(1).ai, progress: { done: 0, total: 3, step: { kind: "batch", index: 1, total: 2 } } } });
  await running(page, ctx, [analysis(1, "running"), behind, analysis(1, "failed")]);
  await page.clock.runFor(2100);
  await expect.poll(() => gets(ctx, 1).length).toBe(2);
  await expect(page.getByRole("status").filter({ hasText: "Step 1 of 3" })).toBeVisible(); // not rewound to 0
  await page.clock.runFor(2100);
  await expect.poll(() => gets(ctx, 1).length).toBe(3);
  await expect(page.getByRole("alert").filter({ hasText: MSG.aiTimeout })).toBeVisible();
  await page.clock.runFor(10_000);
  expect(gets(ctx, 1)).toHaveLength(3);
});

test("adm03 polling: 3 consecutive network failures stop it with the exact message and Retry resumes", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "running")] });
  await running(page, ctx, [analysis(1, "running")]);
  for (let i = 0; i < 3; i++) ctx.steps.push({ suffix: `/analyses/${uuid(1)}`, abort: true });
  for (let i = 0; i < 3; i++) {
    await page.clock.runFor(2100);
    await expect.poll(() => gets(ctx, 1).length).toBe(2 + i);
  }
  await expect(page.getByRole("alert").filter({ hasText: MSG.progressNetwork })).toBeVisible();
  await page.clock.runFor(10_000);
  expect(gets(ctx, 1)).toHaveLength(4);
  await page.getByRole("button", { name: "Retry" }).click();
  await expect.poll(() => gets(ctx, 1).length).toBeGreaterThanOrEqual(5);
  await expect(page.getByRole("alert").filter({ hasText: MSG.progressNetwork })).toHaveCount(0);
});

test("adm03 polling: an unreadable 5xx reply stops it with the status in the message", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "running")] });
  await running(page, ctx, [analysis(1, "running")]);
  ctx.steps.push({ suffix: `/analyses/${uuid(1)}`, status: 502, raw: "<html>Bad gateway</html>" });
  await page.clock.runFor(2100);
  await expect(page.getByRole("alert").filter({ hasText: MSG.progressUnreadable(502) })).toBeVisible();
  const n = gets(ctx, 1).length;
  await page.clock.runFor(10_000);
  expect(gets(ctx, 1)).toHaveLength(n);
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
});

test("adm03 polling gives up after 810 seconds with the exact message", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "running")] });
  await running(page, ctx, [analysis(1, "running")]);
  for (let i = 0; i < 415; i++) {
    await page.clock.runFor(2000);
    await page.waitForTimeout(5);
  }
  await expect(page.getByRole("alert").filter({ hasText: MSG.stoppedWaiting })).toBeVisible();
  const n = gets(ctx, 1).length;
  await page.clock.runFor(20_000);
  expect(gets(ctx, 1)).toHaveLength(n);
});

test("adm03 polling pauses while the tab is hidden and does one GET when visible again", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "running")] });
  await running(page, ctx, [analysis(1, "running")]);
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    Object.defineProperty(document, "hidden", { value: true, configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  const n = gets(ctx, 1).length;
  await page.clock.runFor(10_000);
  expect(gets(ctx, 1)).toHaveLength(n);
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
    Object.defineProperty(document, "hidden", { value: false, configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect.poll(() => gets(ctx, 1).length).toBe(n + 1);
});

test("adm03 a complete or failed analysis is read once and never polled", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "complete")] });
  await page.clock.install();
  await page.goto(URL(1));
  await expect(page.getByRole("heading", { name: "Summary", level: 3 })).toBeVisible();
  await page.clock.runFor(10_000);
  expect(gets(ctx, 1)).toHaveLength(1);
});

test("adm03 a 401 while loading sends the user to sign in with the session message and clears the data", async ({ page }) => {
  const ctx = await setup(page, { analyses: [analysis(1, "complete")] });
  ctx.steps.push({ suffix: `/analyses/${uuid(1)}`, status: 401, code: "unauthenticated", message: "x" });
  await page.goto(URL(1));
  await expect(page.getByText(MSG.expired)).toBeVisible();
  await expect(page.getByText("How clear were the deadlines?")).toHaveCount(0);
});

test("adm03 wrong role on a result URL makes no ADM-03 request", async ({ page }) => {
  const ctx = await setup(page, { user: STUDENT, analyses: [analysis(1, "complete")] });
  await page.goto(URL(1));
  await expect(page).not.toHaveURL(new RegExp("/admin/feedback/analysis"));
  expect(ctx.requests.filter((r) => r.path.startsWith(ROOT))).toHaveLength(0);
});

for (const width of [320, 390]) {
  test(`adm03 ${width}px result page has no horizontal overflow`, async ({ page }) => {
    await setup(page, { analyses: [analysis(1, "complete")] });
    await page.setViewportSize({ width, height: 800 });
    await page.goto(URL(1));
    await expect(page.getByRole("heading", { name: "Summary", level: 3 })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}

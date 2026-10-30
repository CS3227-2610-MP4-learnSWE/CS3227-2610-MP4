import { test, expect, type Locator, type Page } from "@playwright/test";
import {
  ALL_CORRECT,
  FIXTURE_SET,
  SET_ID,
  mockPracticeApi,
  type PracticeApiMock,
} from "./practiceApi";
import {
  companionError,
  companionOk,
  mockCompanionApi,
  type CompanionApiMock,
  type CompanionReply,
} from "./companionApi";

/**
 * STU-03 widget: sends to the companion endpoint (mocked), pending and error
 * states, plain-text rendering, context reporting, request timeout.
 * Wording of the failure messages is not fixed by the spec, so checks are loose:
 * what must hold is that the message is fixed page text (never the raw server
 * body), shown with role="alert", and that the draft survives.
 */

const SUBMIT = "Submit practice set";
const BOX = "Message your study companion";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

function chatOf(page: Page) {
  return page.getByRole("dialog", { name: "Your study companion" });
}

async function openChat(page: Page) {
  await page.getByRole("button", { name: "Open study companion" }).click();
  await expect(chatOf(page)).toBeVisible();
  return chatOf(page);
}

async function minimise(page: Page) {
  await page.getByRole("button", { name: "Minimise study companion" }).click();
  await expect(chatOf(page)).not.toBeVisible();
}

async function send(page: Page, text: string) {
  await page.getByLabel(BOX).fill(text);
  await page.getByRole("button", { name: "Send question" }).click();
}

function sendButton(page: Page) {
  return page.getByRole("button", { name: "Send question" });
}

async function setup(
  page: Page,
  replies: CompanionReply[] = [],
): Promise<CompanionApiMock> {
  await mockPracticeApi(page);
  return mockCompanionApi(page, replies);
}

function choiceText(questionId: string, choiceId: string) {
  const q = FIXTURE_SET.questions.find((x) => x.id === questionId)!;
  return q.choices.find((c) => c.id === choiceId)!.text;
}

async function openPractice(page: Page) {
  await page.goto("/student/practice");
  await expect(
    page.getByRole("radio", { name: choiceText("q1", "a"), exact: true }),
  ).toBeVisible();
}

async function submitAll(page: Page, practice: PracticeApiMock) {
  for (const [q, c] of Object.entries(ALL_CORRECT))
    await page
      .getByRole("radio", { name: choiceText(q, c), exact: true })
      .check();
  await page.getByRole("button", { name: SUBMIT }).click();
  await expect.poll(() => practice.count("results")).toBe(1);
}

async function expectNoRawServerText(chat: Locator) {
  await expect(chat).not.toContainText("RAW-SERVER-TEXT");
}

// ------------------------------------------------------------------ AC27
test("stu03 AC27 sending shows the message, a pending state, then the reply as text", async ({
  page,
}) => {
  const mock = await setup(page, [{ hold: true }]);
  await page.goto("/student/overview");
  const chat = await openChat(page);
  await send(page, "Help me understand functions");
  await expect(chat).toContainText("Help me understand functions");
  await expect(chat.getByText(/thinking/i).first()).toBeVisible();
  await expect.poll(() => mock.count).toBe(1);
  // typing a new question during the wait must not enable sending
  await page.getByLabel(BOX).fill("second question");
  await expect(sendButton(page)).toBeDisabled();
  mock.release();
  await expect(chat).toContainText("Mock companion reply 1");
  await expect(chat.getByText(/thinking/i)).toHaveCount(0);
  await expect(sendButton(page)).toBeEnabled();
});

test("stu03 AC27 reply HTML and markdown stay literal text", async ({
  page,
}) => {
  const evil = "<img src=x onerror=alert(1)> and **bold** and [link](http://x)";
  await setup(page, [companionOk(evil)]);
  const dialogs: string[] = [];
  page.on("dialog", (d) => {
    dialogs.push(d.message());
    void d.dismiss();
  });
  await page.goto("/student/overview");
  const chat = await openChat(page);
  await send(page, "show me something");
  await expect(chat).toContainText(evil);
  await expect(chat.locator('img[src="x"]')).toHaveCount(0);
  await expect(chat.locator("strong, b, em, a[href='http://x']")).toHaveCount(
    0,
  );
  expect(dialogs).toEqual([]);
});

test("stu03 AC27 a withheld reply is shown like any other reply", async ({
  page,
}) => {
  await setup(page, [
    companionOk("I can't share or confirm answers right now.", "hint", true),
  ]);
  await page.goto("/student/overview");
  const chat = await openChat(page);
  await send(page, "is it b?");
  await expect(chat).toContainText("I can't share or confirm answers");
});

// ------------------------------------------------------------------ AC28
const FAILURES: [string, CompanionReply, RegExp | null][] = [
  ["network failure", { abort: true }, null],
  ["401", companionError(401, "missing_student"), null],
  ["404", companionError(404, "attempt_not_found"), null],
  ["422", companionError(422, "invalid_message"), null],
  [
    "429 rate_limited",
    companionError(429, "rate_limited", {
      scope: "student_minute",
      retry_after_seconds: 17,
    }),
    /17/,
  ],
  [
    "429 llm_busy",
    companionError(429, "llm_busy", { retry_after_seconds: 23 }),
    /23/,
  ],
  ["502", companionError(502, "llm_bad_response"), null],
  ["503", companionError(503, "llm_unavailable"), null],
  ["503 not configured", companionError(503, "llm_not_configured"), null],
  ["200 with the wrong shape", { status: 200, json: { oops: true } }, null],
];

for (const [name, failure, wait] of FAILURES) {
  test(`stu03 AC28 ${name}: fixed message, draft kept, second send retries`, async ({
    page,
  }) => {
    const mock = await setup(page, [failure]);
    await page.goto("/student/overview");
    const chat = await openChat(page);
    const question = "Why is my loop never ending?";
    await send(page, question);
    const alert = chat.getByRole("alert");
    await expect(alert).toBeVisible();
    await expect(alert).not.toBeEmpty();
    if (wait) await expect(alert).toContainText(wait);
    await expectNoRawServerText(chat);
    await expect(page.getByLabel(BOX)).toHaveValue(question);
    await expect(chat.getByText(/thinking/i)).toHaveCount(0);
    // second send goes out again with the same question and now succeeds
    await sendButton(page).click();
    await expect(chat).toContainText("Mock companion reply 1");
    expect(mock.count).toBe(2);
    expect(mock.last.body.message).toBe(question);
    await expect(chat.getByRole("alert")).toHaveCount(0);
    await expectNoRawServerText(chat);
  });
}

test("stu03 AC28 a failure does not clear earlier history", async ({
  page,
}) => {
  await setup(page, [
    companionOk("first answer"),
    companionError(503, "llm_unavailable"),
  ]);
  await page.goto("/student/overview");
  const chat = await openChat(page);
  await send(page, "first question");
  await expect(chat).toContainText("first answer");
  await send(page, "second question");
  await expect(chat.getByRole("alert")).toBeVisible();
  await expect(chat).toContainText("first question");
  await expect(chat).toContainText("first answer");
  await expect(page.getByLabel(BOX)).toHaveValue("second question");
});

// ------------------------------------------------------------------ AC29
test("stu03 AC29 other pages report page other and no attempt", async ({
  page,
}) => {
  const mock = await setup(page);
  await page.goto("/student/materials");
  await openChat(page);
  await send(page, "what is a class?");
  await expect.poll(() => mock.count).toBe(1);
  const { context, message } = mock.last.body;
  expect(message).toBe("what is a class?");
  expect(context.page).toBe("other");
  expect(context.attempt_id ?? null).toBeNull();
  expect(mock.last.method).toBe("POST");
});

test("stu03 AC29 practice page reports the set before submit and the attempt after", async ({
  page,
}) => {
  const practice = await mockPracticeApi(page);
  const mock = await mockCompanionApi(page);
  await openPractice(page);
  await openChat(page);
  await send(page, "give me a hint for question 1");
  await expect.poll(() => mock.count).toBe(1);
  expect(mock.requests[0].body.context.page).toBe("practice");
  expect(mock.requests[0].body.context.set_id).toBe(SET_ID);
  expect(mock.requests[0].body.context.attempt_id ?? null).toBeNull();
  await minimise(page);

  await submitAll(page, practice);
  const attemptId = practice.of("submit")[0].attemptId;
  expect(attemptId).toBeTruthy();
  await openChat(page);
  await send(page, "explain my result");
  await expect.poll(() => mock.count).toBe(2);
  expect(mock.requests[1].body.context.page).toBe("practice");
  expect(mock.requests[1].body.context.attempt_id).toBe(attemptId);
  await minimise(page);

  await page.getByRole("button", { name: "Start another attempt" }).click();
  await openChat(page);
  await send(page, "another hint please");
  await expect.poll(() => mock.count).toBe(3);
  expect(mock.requests[2].body.context.page).toBe("practice");
  expect(mock.requests[2].body.context.attempt_id ?? null).toBeNull();
});

test("stu03 AC29 requests never carry a mode, a score or an answer key", async ({
  page,
}) => {
  const practice = await mockPracticeApi(page);
  const mock = await mockCompanionApi(page);
  await openPractice(page);
  await submitAll(page, practice);
  await openChat(page);
  await send(page, "why did I get this wrong?");
  await expect.poll(() => mock.count).toBe(1);
  const raw = mock.last.raw ?? "";
  expect(raw).not.toMatch(/"mode"/i);
  expect(raw).not.toMatch(/score/i);
  expect(raw).not.toMatch(/correct/i);
  expect(raw).not.toMatch(/explanation/i);
  expect(raw).not.toMatch(/key_version/i);
  const ctx = Object.keys(mock.last.body.context);
  for (const k of ctx)
    expect(["page", "set_id", "attempt_id", "label"]).toContain(k);
  expect(Object.keys(mock.last.body).sort()).toEqual(
    ["context", "history", "message"].sort(),
  );
  if (mock.last.body.context.label)
    expect(mock.last.body.context.label.length).toBeLessThanOrEqual(80);
});

test("stu03 AC29 history sent is at most four recent items", async ({
  page,
}) => {
  const mock = await setup(page);
  await page.goto("/student/overview");
  const chat = await openChat(page);
  for (let i = 1; i <= 6; i++) {
    await send(page, `question number ${i}`);
    await expect(chat).toContainText(`Mock companion reply ${i}`);
  }
  expect(mock.count).toBe(6);
  const { history } = mock.last.body;
  expect(history.length).toBeGreaterThan(0);
  expect(history.length).toBeLessThanOrEqual(4);
  for (const item of history) {
    expect(["user", "assistant"]).toContain(item.role);
    expect(typeof item.text).toBe("string");
  }
  // the newest kept item is recent, and the oldest question is no longer sent
  expect(history.map((h) => h.text).join("\n")).not.toContain(
    "question number 1",
  );
  expect(history.map((h) => h.text).join("\n")).toContain(
    "Mock companion reply 5",
  );
});

test("stu03 AC29 clear chat empties history for the next request", async ({
  page,
}) => {
  const mock = await setup(page);
  await page.goto("/student/overview");
  const chat = await openChat(page);
  await send(page, "remember this");
  await expect(chat).toContainText("Mock companion reply 1");
  await page.getByRole("button", { name: "Clear chat" }).click();
  await send(page, "fresh start");
  await expect.poll(() => mock.count).toBe(2);
  expect(mock.last.body.history).toEqual([]);
});

test("stu03 AC29 existing widget behaviour holds after a real exchange", async ({
  page,
}) => {
  await setup(page);
  await page.setViewportSize({ width: 390, height: 700 });
  await page.goto("/student/overview");
  const chat = await openChat(page);
  await send(page, "Help me understand functions");
  await expect(chat).toContainText("Mock companion reply 1");
  await page.getByLabel(BOX).fill("Unsent thought");
  await page.keyboard.press("Escape");
  await expect(chat).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Open study companion" }),
  ).toBeFocused();
  await page.getByRole("button", { name: "Open study companion" }).click();
  await expect(chat).toContainText("Help me understand functions");
  await expect(chat).toContainText("Mock companion reply 1");
  await expect(page.getByLabel(BOX)).toHaveValue("Unsent thought");
  await page.reload();
  await page.getByRole("button", { name: "Open study companion" }).click();
  await expect(chatOf(page)).not.toContainText("Help me understand functions");
});

test("stu03 AC29 the old preview wording is gone", async ({ page }) => {
  await setup(page);
  await page.goto("/student/overview");
  const chat = await openChat(page);
  await expect(chat).not.toContainText("No AI connected");
  await expect(chat).not.toContainText(/preview/i);
  await send(page, "hello");
  await expect(chat).toContainText("Mock companion reply 1");
  await expect(chat).not.toContainText("No AI connected");
  await expect(chat).not.toContainText(/preview/i);
});

// ------------------------------------------------------------------ AC30
test("stu03 AC30 a reply arriving after 30 s is still shown", async ({
  page,
}) => {
  const mock = await setup(page, [{ hold: true }]);
  await page.clock.install();
  await page.goto("/student/overview");
  const chat = await openChat(page);
  await send(page, "slow question");
  await expect.poll(() => mock.count).toBe(1);
  await page.clock.fastForward(30_000);
  await expect(chat.getByText(/thinking/i).first()).toBeVisible();
  await expect(chat.getByRole("alert")).toHaveCount(0);
  mock.release();
  await expect(chat).toContainText("Mock companion reply 1");
  await expect(chat.getByRole("alert")).toHaveCount(0);
});

test("stu03 AC30 no reply by 41 s shows the failure message and keeps the draft", async ({
  page,
}) => {
  const mock = await setup(page, [{ hold: true }]);
  await page.clock.install();
  await page.goto("/student/overview");
  const chat = await openChat(page);
  await send(page, "very slow question");
  await expect.poll(() => mock.count).toBe(1);
  await page.clock.fastForward(41_000);
  await expect(chat.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel(BOX)).toHaveValue("very slow question");
  await expect(chat.getByText(/thinking/i)).toHaveCount(0);
  mock.release();
});

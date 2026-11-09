import { test, expect, type Locator, type Page } from "@playwright/test";
import {
  companionError,
  companionGrounded,
  companionOk,
  mockCompanionApi,
  type CompanionApiMock,
  type CompanionReply,
} from "./companionApi";
import { L_DESIGN, L_GENERAL, L_TESTING, signedInStudy } from "./lessonsApi";
import { SET_ID, mockPracticeApi } from "./practiceApi";

/**
 * STU-03-grounding widget: lesson id from the URL (AC5), "Based on:" source links (AC21),
 * request shape and the new 404 message (AC22), draft kept on every error (AC4).
 * Contract: workflow/specs/STU-03-grounding/{spec,plan}.md ("UI states and copy", "UI contract").
 * The companion endpoint and the study API are mocked; no backend or model is used.
 */

const BOX = "Message your study companion";
const NOTE = "Answers use the lesson you are viewing.";
const NETWORK_MESSAGE =
  "I could not reach the study companion. Check your connection and try again.";
const LESSON_NOT_FOUND_MESSAGE =
  "I could not find this lesson. It may have been withdrawn, or you may no longer have access. Go to Study materials and try again.";

const TESTING = { lesson_id: L_TESTING, title: "Unit testing basics" };
const DESIGN = { lesson_id: L_DESIGN, title: "Design for change" };

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

async function send(page: Page, text: string) {
  await page.getByLabel(BOX).fill(text);
  await page.getByRole("button", { name: "Send question" }).click();
}

function sourcesOf(chat: Locator) {
  return chat.getByRole("group", { name: "Sources" });
}

async function setup(
  page: Page,
  replies: CompanionReply[] = [],
): Promise<CompanionApiMock> {
  await signedInStudy(page);
  return mockCompanionApi(page, replies);
}

async function openLesson(page: Page, id = L_TESTING) {
  await page.goto(`/student/materials/${id}`);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
}

// ------------------------------------------------------------------ AC5
test("stu03 grounding AC5 a lesson page sends page lesson and the lesson id, with no request on load", async ({
  page,
}) => {
  const mock = await setup(page);
  await openLesson(page, L_TESTING);
  expect(mock.count).toBe(0);
  const chat = await openChat(page);
  expect(mock.count).toBe(0);
  await send(page, "What is a unit test?");
  await expect(chat).toContainText("Mock companion reply 1");
  expect(mock.count).toBe(1);
  expect(mock.last.method).toBe("POST");
  expect(mock.last.body.context.page).toBe("lesson");
  expect(mock.last.body.context.lesson_id).toBe(L_TESTING);
});

test("stu03 grounding AC5 the lesson id follows navigation, Back and leaving the lesson pages", async ({
  page,
}) => {
  const mock = await setup(page, [
    companionGrounded("See the design lesson.", [DESIGN]),
  ]);
  await openLesson(page, L_TESTING);
  const chat = await openChat(page);

  await send(page, "first question");
  await expect(chat).toContainText("See the design lesson.");
  expect(mock.requests[0].body.context.lesson_id).toBe(L_TESTING);

  // follow the source link to another lesson: the widget stays open with its history
  await sourcesOf(chat).getByRole("link", { name: DESIGN.title }).click();
  await expect(page).toHaveURL(new RegExp(`/student/materials/${L_DESIGN}$`));
  await expect(chat).toBeVisible();
  await expect(chat).toContainText("first question");
  await expect(chat).toContainText("See the design lesson.");
  expect(mock.count).toBe(1); // navigation sends nothing

  await send(page, "second question");
  await expect(chat).toContainText("Mock companion reply 1");
  expect(mock.requests[1].body.context.page).toBe("lesson");
  expect(mock.requests[1].body.context.lesson_id).toBe(L_DESIGN);

  // Back returns to the first lesson and the next send carries its id
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/student/materials/${L_TESTING}$`));
  await expect(chat).toContainText("second question");
  await send(page, "third question");
  await expect(chat).toContainText("Mock companion reply 2");
  expect(mock.requests[2].body.context.lesson_id).toBe(L_TESTING);

  // the study-materials list is neither a lesson nor a practice page
  await page.getByRole("button", { name: "Minimise study companion" }).click();
  await page.getByRole("link", { name: "All study materials" }).click();
  await expect(page).toHaveURL(/\/student\/materials(\?.*)?$/);
  await openChat(page);
  await send(page, "fourth question");
  await expect(chat).toContainText("Mock companion reply 3");
  expect(mock.requests[3].body.context.page).toBe("other");
  expect(mock.requests[3].body.context.lesson_id ?? null).toBeNull();
  expect(mock.count).toBe(4);
});

test("stu03 grounding AC5 practice and overview pages send no lesson id", async ({
  page,
}) => {
  await signedInStudy(page);
  await mockPracticeApi(page);
  const mock = await mockCompanionApi(page);

  await page.goto(`/student/practice/${SET_ID}`);
  await expect(page.getByRole("radio").first()).toBeVisible();
  await openChat(page);
  await send(page, "give me a hint");
  await expect.poll(() => mock.count).toBe(1);
  expect(mock.requests[0].body.context.page).toBe("practice");
  expect(mock.requests[0].body.context.set_id).toBe(SET_ID);
  expect(mock.requests[0].body.context.lesson_id ?? null).toBeNull();

  await page.goto("/student/overview");
  await openChat(page);
  await send(page, "what should I do next?");
  await expect.poll(() => mock.count).toBe(2);
  expect(mock.requests[1].body.context.page).toBe("other");
  expect(mock.requests[1].body.context.lesson_id ?? null).toBeNull();
});

test("stu03 grounding AC5 the welcome note names the lesson only on a lesson page", async ({
  page,
}) => {
  await setup(page);
  await openLesson(page, L_GENERAL);
  const chat = await openChat(page);
  await expect(chat.getByText(NOTE)).toBeVisible();
  await page.getByRole("button", { name: "Minimise study companion" }).click();
  await page.getByRole("link", { name: "All study materials" }).click();
  await expect(page).toHaveURL(/\/student\/materials(\?.*)?$/);
  await openChat(page);
  await expect(chat.getByText(NOTE)).toHaveCount(0);
});

// ------------------------------------------------------------------ AC22
test("stu03 grounding AC22 the request never carries a mode, sources, title or lesson text", async ({
  page,
}) => {
  const mock = await setup(page);
  await openLesson(page, L_TESTING);
  await openChat(page);
  await send(page, "explain this lesson");
  await expect.poll(() => mock.count).toBe(1);
  const raw = mock.last.raw ?? "";
  expect(raw).not.toMatch(/"mode"/i);
  expect(raw).not.toMatch(/"sources"/i);
  expect(raw).not.toMatch(/"title"/i);
  expect(raw).not.toMatch(/"content"/i);
  expect(raw).not.toContain("Unit testing basics");
  expect(raw).not.toContain("Write small tests first");
  for (const k of Object.keys(mock.last.body.context))
    expect(["page", "set_id", "attempt_id", "lesson_id", "label"]).toContain(k);
  expect(Object.keys(mock.last.body).sort()).toEqual(
    ["context", "history", "message"].sort(),
  );
});

test("stu03 grounding AC22 404 lesson_not_found shows its own message and keeps the draft", async ({
  page,
}) => {
  const mock = await setup(page, [companionError(404, "lesson_not_found")]);
  await openLesson(page, L_TESTING);
  const chat = await openChat(page);
  await send(page, "what is a stub?");
  const alert = chat.getByRole("alert");
  await expect(alert).toContainText(LESSON_NOT_FOUND_MESSAGE);
  await expect(chat).not.toContainText("RAW-SERVER-TEXT");
  await expect(page.getByLabel(BOX)).toHaveValue("what is a stub?");
  // a second send retries once and succeeds
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(chat).toContainText("Mock companion reply 1");
  expect(mock.count).toBe(2);
  expect(mock.last.body.message).toBe("what is a stub?");
  await expect(chat.getByRole("alert")).toHaveCount(0);
});

test("stu03 grounding AC22 404 attempt_not_found keeps its own older message", async ({
  page,
}) => {
  await setup(page, [companionError(404, "attempt_not_found")]);
  await page.goto("/student/overview");
  const chat = await openChat(page);
  await send(page, "why was I wrong?");
  const alert = chat.getByRole("alert");
  await expect(alert).toBeVisible();
  await expect(alert).not.toBeEmpty();
  await expect(alert).not.toContainText("I could not find this lesson");
  await expect(chat).not.toContainText("RAW-SERVER-TEXT");
});

// ------------------------------------------------------------------ AC4
const LESSON_FAILURES: [string, CompanionReply][] = [
  ["network failure", { abort: true }],
  ["404 lesson_not_found", companionError(404, "lesson_not_found")],
  ["422 invalid_context", companionError(422, "invalid_context")],
  ["422 invalid_message", companionError(422, "invalid_message")],
  [
    "429 rate_limited",
    companionError(429, "rate_limited", {
      scope: "student_minute",
      retry_after_seconds: 17,
    }),
  ],
  [
    "429 llm_busy",
    companionError(429, "llm_busy", { retry_after_seconds: 23 }),
  ],
  ["502", companionError(502, "llm_bad_response")],
  ["503", companionError(503, "llm_unavailable")],
  ["503 not configured", companionError(503, "llm_not_configured")],
  ["200 with a bad shape", { status: 200, json: { oops: true } }],
];

for (const [name, failure] of LESSON_FAILURES) {
  test(`stu03 grounding AC4 lesson page ${name}: alert, draft kept, second send retries`, async ({
    page,
  }) => {
    const mock = await setup(page, [failure]);
    await openLesson(page, L_TESTING);
    const chat = await openChat(page);
    const question = "What does a test double do?";
    await send(page, question);
    await expect(chat.getByRole("alert")).toBeVisible();
    await expect(chat).not.toContainText("RAW-SERVER-TEXT");
    await expect(page.getByLabel(BOX)).toHaveValue(question);
    await expect(chat.getByText(/thinking/i)).toHaveCount(0);
    await page.getByRole("button", { name: "Send question" }).click();
    await expect(chat).toContainText("Mock companion reply 1");
    expect(mock.count).toBe(2);
    expect(mock.last.body.message).toBe(question);
    expect(mock.last.body.context.lesson_id).toBe(L_TESTING);
    await expect(chat.getByRole("alert")).toHaveCount(0);
  });
}

// ------------------------------------------------------------------ AC21
test("stu03 grounding AC21 a grounded reply shows Based on with a link per source", async ({
  page,
}) => {
  await setup(page, [
    companionGrounded("Tests check small units of code.", [TESTING, DESIGN]),
  ]);
  await openLesson(page, L_GENERAL);
  const chat = await openChat(page);
  await send(page, "what is a unit test?");
  await expect(chat).toContainText("Tests check small units of code.");
  const group = sourcesOf(chat);
  await expect(group).toBeVisible();
  await expect(group).toContainText("Based on:");
  const links = group.getByRole("link");
  await expect(links).toHaveCount(2);
  await expect(links.nth(0)).toHaveAccessibleName(TESTING.title);
  await expect(links.nth(1)).toHaveAccessibleName(DESIGN.title);
  await expect(links.nth(0)).toHaveAttribute(
    "href",
    `/student/materials/${L_TESTING}`,
  );
  await expect(links.nth(1)).toHaveAttribute(
    "href",
    `/student/materials/${L_DESIGN}`,
  );
});

test("stu03 grounding AC21 a source title stays literal text", async ({
  page,
}) => {
  const evil = "<img src=x onerror=alert(1)>";
  await setup(page, [
    companionGrounded("Here is the idea.", [
      { lesson_id: L_TESTING, title: evil },
    ]),
  ]);
  const dialogs: string[] = [];
  page.on("dialog", (d) => {
    dialogs.push(d.message());
    void d.dismiss();
  });
  await openLesson(page, L_DESIGN);
  const chat = await openChat(page);
  await send(page, "tell me more");
  const link = sourcesOf(chat).getByRole("link");
  await expect(link).toHaveCount(1);
  await expect(link).toHaveAccessibleName(evil);
  await expect(chat.locator('img[src="x"]')).toHaveCount(0);
  expect(dialogs).toEqual([]);
});

test("stu03 grounding AC21 a reply with no sources shows no Based on line", async ({
  page,
}) => {
  await setup(page, [
    companionOk(
      "This isn't covered in the lesson materials I can see.",
      "lesson",
    ),
    companionOk("General help text.", "help"),
    companionOk("I can't share or confirm practice answers.", "lesson", true),
  ]);
  await openLesson(page, L_TESTING);
  const chat = await openChat(page);
  const replies = [
    "This isn't covered in the lesson materials I can see.",
    "General help text.",
    "I can't share or confirm practice answers.",
  ];
  for (const [n, text] of replies.entries()) {
    await send(page, `question ${n + 1}`);
    await expect(chat).toContainText(text);
    await expect(chat.getByText(/thinking/i)).toHaveCount(0);
  }
  await expect(sourcesOf(chat)).toHaveCount(0);
  await expect(chat).not.toContainText("Based on:");
});

test("stu03 grounding AC21 following a source link keeps the widget open with its history", async ({
  page,
}) => {
  const mock = await setup(page, [
    companionGrounded("Look at the testing lesson.", [TESTING]),
  ]);
  await openLesson(page, L_DESIGN);
  const chat = await openChat(page);
  await send(page, "how do I test this?");
  await expect(chat).toContainText("Look at the testing lesson.");
  await page.getByLabel(BOX).fill("an unsent draft");
  await sourcesOf(chat).getByRole("link", { name: TESTING.title }).click();
  await expect(page).toHaveURL(new RegExp(`/student/materials/${L_TESTING}$`));
  await expect(chat).toBeVisible();
  await expect(chat).toContainText("how do I test this?");
  await expect(chat).toContainText("Look at the testing lesson.");
  await expect(page.getByLabel(BOX)).toHaveValue("an unsent draft");
  expect(mock.count).toBe(1);
});

const BAD_SOURCES: [string, unknown][] = [
  ["a string", "x"],
  ["null", null],
  ["missing", undefined],
  ["an element without a title", [{ lesson_id: L_TESTING }]],
  ["an element with a numeric id", [{ lesson_id: 7, title: "T" }]],
  ["a non-object element", ["Unit testing basics"]],
];

for (const [name, sources] of BAD_SOURCES) {
  test(`stu03 grounding AC21 sources as ${name} counts as a failed response`, async ({
    page,
  }) => {
    const mock = await setup(page, [
      {
        status: 200,
        json: {
          reply: "UNTRUSTED-BAD-SHAPE-REPLY",
          mode: "lesson",
          withheld: false,
          ...(sources === undefined ? {} : { sources }),
        },
      },
    ]);
    await openLesson(page, L_TESTING);
    const chat = await openChat(page);
    await send(page, "what is a mock?");
    await expect(chat.getByRole("alert")).toContainText(NETWORK_MESSAGE);
    await expect(chat).not.toContainText("UNTRUSTED-BAD-SHAPE-REPLY");
    await expect(sourcesOf(chat)).toHaveCount(0);
    await expect(page.getByLabel(BOX)).toHaveValue("what is a mock?");
    expect(mock.count).toBe(1);
  });
}

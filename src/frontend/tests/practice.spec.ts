import { test, expect, type Page } from "@playwright/test";
import {
  ALL_CORRECT,
  FIXTURE_KEY,
  FIXTURE_SET,
  SET_ID,
  TWO_OF_THREE,
  apiError,
  buildResults,
  mockPracticeApi,
  type PracticeApiMock,
} from "./practiceApi";

/**
 * STU-02-frontend: Student Practice page on the (mocked) practice API.
 * Wording of messages is not fixed by the spec, so message checks are loose;
 * the stable names are the button/radio labels listed in the plan.
 */

const EXPLANATIONS = Object.values(FIXTURE_KEY).map((k) => k.explanation);
const SUBMIT = "Submit practice set";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
});

function choiceText(questionId: string, choiceId: string) {
  const q = FIXTURE_SET.questions.find((x) => x.id === questionId)!;
  return q.choices.find((c) => c.id === choiceId)!.text;
}

function radio(page: Page, questionId: string, choiceId: string) {
  return page.getByRole("radio", {
    name: choiceText(questionId, choiceId),
    exact: true,
  });
}

async function openPractice(page: Page) {
  await page.goto("/student/practice");
  await expect(
    page.getByRole("radio", { name: choiceText("q1", "a"), exact: true }),
  ).toBeVisible();
}

async function pick(page: Page, answers: Record<string, string>) {
  for (const [q, c] of Object.entries(answers)) await radio(page, q, c).check();
}

function submitButton(page: Page) {
  return page.getByRole("button", { name: SUBMIT });
}

/** Text of the whole page, for "nothing leaked" checks. */
async function pageText(page: Page) {
  return page.locator("body").innerText();
}

async function expectNoSolutions(page: Page) {
  const text = await pageText(page);
  for (const explanation of EXPLANATIONS)
    expect(text).not.toContain(explanation);
  expect(text).not.toMatch(/correct (answer|choice)/i);
}

async function submitCompleteSet(
  page: Page,
  mock: PracticeApiMock,
  answers = TWO_OF_THREE,
) {
  await openPractice(page);
  await pick(page, answers);
  await submitButton(page).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  expect(mock.count("results")).toBe(1);
}

function scoreText(correct: number, total = 3) {
  return new RegExp(`\\b${correct}\\s*(/|of|out of)\\s*${total}\\b`);
}

test("stu02fe AC1 page shows the API's title, questions, code and choices in order", async ({
  page,
}) => {
  const set = {
    id: SET_ID,
    title: "Mocked set title ZX",
    questions: [
      {
        id: "z9",
        text: "Zeta question text?",
        code: "print('zeta')",
        choices: [
          { id: "x", text: "Zeta first choice" },
          { id: "y", text: "Zeta second choice" },
        ],
      },
      {
        id: "a1",
        text: "Alpha question text?",
        code: null,
        choices: [
          { id: "m", text: "Alpha only choice" },
          { id: "n", text: "Alpha other choice" },
        ],
      },
    ],
  };
  const mock = await mockPracticeApi(page, { set });
  await page.goto("/student/practice");
  await expect(page.getByText("Mocked set title ZX").first()).toBeVisible();
  const text = await pageText(page);
  expect(text.indexOf("Zeta question text?")).toBeGreaterThan(-1);
  expect(text.indexOf("Zeta question text?")).toBeLessThan(
    text.indexOf("Alpha question text?"),
  );
  expect(text.indexOf("Zeta first choice")).toBeLessThan(
    text.indexOf("Zeta second choice"),
  );
  await expect(page.locator("pre code")).toHaveCount(1);
  await expect(page.locator("pre code")).toContainText("print('zeta')");
  await expect(page.getByRole("radio")).toHaveCount(4);
  await expect(page.getByText("0 of 2 answered")).toBeVisible();
  // Nothing of the old hard-coded demo set is shown.
  expect(text).not.toContain("What should a well-designed function have?");
  expect(mock.of("getSet")).toHaveLength(1);
  expect(mock.of("getSet")[0].path).toBe(`/api/practice-sets/${SET_ID}`);
});

test("stu02fe AC1 default fixture renders all three questions in order", async ({
  page,
}) => {
  await mockPracticeApi(page);
  await openPractice(page);
  const text = await pageText(page);
  const positions = FIXTURE_SET.questions.map((q) => text.indexOf(q.text));
  expect(positions.every((p) => p > -1)).toBe(true);
  expect([...positions].sort((a, b) => a - b)).toEqual(positions);
  await expect(page.locator("pre code")).toContainText("print(len(values))");
  await expect(page.getByRole("radio")).toHaveCount(9);
});

test("stu02fe AC1 a loading state shows while the set is loading", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { getSet: [{ delayMs: 800, passThrough: true }] },
  });
  await page.goto("/student/practice");
  await expect(page.getByText(/loading/i).first()).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(0);
  await expect(radio(page, "q1", "a")).toBeVisible();
  expect(mock.count("getSet")).toBe(1);
});

test("stu02fe AC2 choices can be changed, counter is right, nothing is revealed before submit", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page);
  await openPractice(page);
  await expect(page.getByText("0 of 3 answered")).toBeVisible();
  await radio(page, "q1", "b").check();
  await expect(page.getByText("1 of 3 answered")).toBeVisible();
  await radio(page, "q1", "a").check();
  await expect(radio(page, "q1", "a")).toBeChecked();
  await expect(radio(page, "q1", "b")).not.toBeChecked();
  await expect(page.getByText("1 of 3 answered")).toBeVisible();
  await radio(page, "q2", "b").check();
  await expect(page.getByText("2 of 3 answered")).toBeVisible();
  await page.getByRole("button", { name: "Get a hint" }).click();
  await expectNoSolutions(page);
  expect(mock.mutating).toEqual([]);
});

test("stu02fe AC2 nothing is revealed after a failed submission and answers stay", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { submit: [{ status: 500, body: "SECRET_TRACE_MARKER" }] },
  });
  await openPractice(page);
  await pick(page, ALL_CORRECT);
  await submitButton(page).click();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expectNoSolutions(page);
  await expect(page.getByText("3 of 3 answered")).toBeVisible();
  for (const [q, c] of Object.entries(ALL_CORRECT))
    await expect(radio(page, q, c)).toBeChecked();
  expect(mock.count("results")).toBe(0);
});

test("stu02fe AC3 incomplete submit sends no state-changing request and names missing questions", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page);
  await openPractice(page);
  await radio(page, "q1", "a").check();
  await radio(page, "q3", "c").check();
  await submitButton(page).click();
  const alert = page.getByRole("alert");
  await expect(alert).toBeVisible();
  await expect(alert).toContainText(/\b2\b/);
  expect(mock.mutating).toEqual([]);
  expect(mock.count("results")).toBe(0);
  await expect(radio(page, "q1", "a")).toBeChecked();
  await expect(radio(page, "q3", "c")).toBeChecked();
  await expect(page.getByText("2 of 3 answered")).toBeVisible();
});

test("stu02fe AC3 several missing questions are all named", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page);
  await openPractice(page);
  await radio(page, "q2", "b").check();
  await submitButton(page).click();
  const alert = page.getByRole("alert");
  await expect(alert).toContainText(/\b1\b/);
  await expect(alert).toContainText(/\b3\b/);
  await expect(alert).not.toContainText(/\b2\b/);
  expect(mock.mutating).toEqual([]);
});

test("stu02fe AC4 full flow runs attempt, save, submit, results in order and shows server results", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page);
  await openPractice(page);
  await pick(page, TWO_OF_THREE);
  await submitButton(page).click();
  for (const explanation of EXPLANATIONS)
    await expect(page.getByText(explanation).first()).toBeVisible();
  expect(mock.order).toEqual(["getSet", "start", "save", "submit", "results"]);
  const attemptId = mock.of("save")[0].attemptId;
  expect(attemptId).toMatch(/^attempt-/);
  expect(mock.of("save")[0].body).toEqual({ answers: TWO_OF_THREE });
  expect(mock.of("submit")[0].attemptId).toBe(attemptId);
  expect(mock.of("results")[0].attemptId).toBe(attemptId);
  expect(mock.of("start")[0].path).toBe(
    `/api/practice-sets/${SET_ID}/attempts`,
  );
  await expect(page.getByText(scoreText(2)).first()).toBeVisible();
  // q3: the student's choice "2" and the correct choice "3" are both shown.
  const q3 = page.locator(".question-panel").filter({
    hasText: FIXTURE_SET.questions[2].text,
  });
  await expect(q3).toContainText(FIXTURE_KEY.q3.explanation);
  await expect(q3).toContainText(/correct/i);
  // Choices are read-only.
  const radios = page.getByRole("radio");
  await expect(radios).toHaveCount(9);
  for (const r of await radios.all()) await expect(r).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Start another attempt" }),
  ).toBeVisible();
});

test("stu02fe AC4 a perfect score is shown from the server", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page);
  await submitCompleteSet(page, mock, ALL_CORRECT);
  await expect(page.getByText(/\b3\s*(\/|out of)\s*3\b/).first()).toBeVisible();
});

test("stu02fe AC5 server score and per-question results win over what the page would guess", async ({
  page,
}) => {
  const answers = ALL_CORRECT;
  const odd = buildResults("attempt-0001", answers);
  odd.score = { correct: 1, total: 3 };
  odd.questions[0].correct = false;
  odd.questions[0].selected = "b";
  odd.questions[1].explanation = "Server-only explanation Q2 marker.";
  odd.questions[2].correct = false;
  const mock = await mockPracticeApi(page, {
    replies: { results: [{ json: odd }] },
  });
  await openPractice(page);
  await pick(page, answers);
  await submitButton(page).click();
  await expect(
    page.getByText("Server-only explanation Q2 marker."),
  ).toBeVisible();
  await expect(page.getByText(scoreText(1)).first()).toBeVisible();
  const text = await pageText(page);
  expect(text).not.toMatch(/\b3\s*(\/|out of)\s*3\b/);
  // The page's own would-be explanation for q2 (client key) is not used.
  expect(text).not.toContain(FIXTURE_KEY.q2.explanation);
  expect(mock.count("results")).toBe(1);
});

test("stu02fe AC6 network failure on load shows an error panel with Try again, then loads", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { getSet: [{ abort: true }] },
  });
  await page.goto("/student/practice");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(0);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(radio(page, "q1", "a")).toBeVisible();
  expect(mock.count("getSet")).toBe(2);
});

test("stu02fe AC6 404 set_not_found shows an error panel without raw details", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { getSet: [apiError(404, "set_not_found")] },
  });
  await page.goto("/student/practice");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(0);
  const text = await pageText(page);
  expect(text).not.toContain("set_not_found");
  expect(text).not.toContain("Server says");
  expect(text).not.toMatch(/\b404\b/);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(radio(page, "q1", "a")).toBeVisible();
  expect(mock.count("getSet")).toBe(2);
});

test("stu02fe AC6 a response of the wrong shape on load is treated as a failure", async ({
  page,
}) => {
  await mockPracticeApi(page, {
    replies: {
      getSet: [{ json: { id: SET_ID, title: 42, questions: "nope" } }],
    },
  });
  await page.goto("/student/practice");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(0);
});

test("stu02fe AC6 HTTP 500 on load shows an error panel", async ({ page }) => {
  await mockPracticeApi(page, {
    replies: {
      getSet: [{ status: 500, body: "Traceback SECRET_TRACE_MARKER" }],
    },
  });
  await page.goto("/student/practice");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  const text = await pageText(page);
  expect(text).not.toContain("SECRET_TRACE_MARKER");
  expect(text).not.toContain("Traceback");
});

test("stu02fe AC6 500 on submit keeps answers; Try again repeats only the failed step", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { submit: [{ status: 500, body: "SECRET_TRACE_MARKER" }] },
  });
  await openPractice(page);
  await pick(page, TWO_OF_THREE);
  await submitButton(page).click();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  const text = await pageText(page);
  expect(text).not.toContain("SECRET_TRACE_MARKER");
  expect(text).not.toMatch(/\b500\b/);
  for (const [q, c] of Object.entries(TWO_OF_THREE))
    await expect(radio(page, q, c)).toBeChecked();
  expect(mock.count("results")).toBe(0);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  expect(mock.count("start")).toBe(1);
  expect(mock.count("submit")).toBe(2);
  expect(mock.count("results")).toBe(1);
  expect(mock.count("save")).toBe(1);
});

test("stu02fe AC6 results failure after a successful submit retries only the results", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { results: [{ status: 503, body: "down" }] },
  });
  await openPractice(page);
  await pick(page, TWO_OF_THREE);
  await submitButton(page).click();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expectNoSolutions(page);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  expect(mock.count("submit")).toBe(1);
  expect(mock.count("results")).toBe(2);
});

test("stu02fe AC6 network failure on save keeps answers and Try again repeats the save", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { save: [{ abort: true }] },
  });
  await openPractice(page);
  await pick(page, ALL_CORRECT);
  await submitButton(page).click();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  expect(mock.count("submit")).toBe(0);
  await expect(radio(page, "q2", "b")).toBeChecked();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  expect(mock.count("start")).toBe(1);
  expect(mock.count("save")).toBe(2);
});

test("stu02fe AC6 a response of the wrong shape on results is treated as a failure", async ({
  page,
}) => {
  await mockPracticeApi(page, {
    replies: { results: [{ json: { score: "high", questions: null } }] },
  });
  await openPractice(page);
  await pick(page, ALL_CORRECT);
  await submitButton(page).click();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expectNoSolutions(page);
});

test("stu02fe AC6 422 incomplete from the server shows the missing list from the server", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { submit: [apiError(422, "incomplete", { missing: ["q2"] })] },
  });
  await openPractice(page);
  await pick(page, ALL_CORRECT);
  await submitButton(page).click();
  const alert = page.getByRole("alert");
  await expect(alert).toContainText(/\b2\b/);
  await expect(alert).not.toContainText("Server says");
  for (const [q, c] of Object.entries(ALL_CORRECT))
    await expect(radio(page, q, c)).toBeChecked();
  expect(mock.count("results")).toBe(0);
  await expectNoSolutions(page);
});

test("stu02fe AC6 409 already_submitted on submit loads the results instead of an error", async ({
  page,
}) => {
  const results = buildResults("attempt-0001", TWO_OF_THREE);
  const mock = await mockPracticeApi(page, {
    replies: {
      submit: [apiError(409, "already_submitted")],
      results: [{ json: results }],
    },
  });
  await openPractice(page);
  await pick(page, TWO_OF_THREE);
  await submitButton(page).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  await expect(page.getByText(scoreText(2)).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  expect(mock.order.slice(-2)).toEqual(["submit", "results"]);
  expect(mock.count("submit")).toBe(1);
});

test("stu02fe AC6 404 attempt_not_found makes a new attempt, re-saves the same answers once", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { save: [apiError(404, "attempt_not_found")] },
  });
  await openPractice(page);
  await pick(page, TWO_OF_THREE);
  await submitButton(page).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  expect(mock.count("start")).toBe(2);
  const saves = mock.of("save");
  expect(saves).toHaveLength(2);
  expect(saves[1].body).toEqual({ answers: TWO_OF_THREE });
  expect(saves[1].attemptId).not.toBe(saves[0].attemptId);
  expect(mock.of("submit")[0].attemptId).toBe(saves[1].attemptId);
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
});

test("stu02fe AC6 404 attempt_not_found twice shows the error after one retry only", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: {
      save: [
        apiError(404, "attempt_not_found"),
        apiError(404, "attempt_not_found"),
        apiError(404, "attempt_not_found"),
        apiError(404, "attempt_not_found"),
      ],
    },
  });
  await openPractice(page);
  await pick(page, ALL_CORRECT);
  await submitButton(page).click();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  expect(mock.count("start")).toBe(2);
  expect(mock.count("save")).toBe(2);
  expect(mock.count("submit")).toBe(0);
  const text = await pageText(page);
  expect(text).not.toContain("attempt_not_found");
  await expect(radio(page, "q1", "a")).toBeChecked();
});

test("stu02fe AC6 slow submit past 10 seconds times out with Try again (fake clock)", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { submit: [{ hang: true }] },
  });
  await openPractice(page);
  await pick(page, ALL_CORRECT);
  await page.clock.install();
  await submitButton(page).click();
  await expect.poll(() => mock.count("submit")).toBe(1);
  await page.clock.fastForward(9_000);
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
  await page.clock.fastForward(2_000);
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(radio(page, "q1", "a")).toBeChecked();
  await expectNoSolutions(page);
  mock.release();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
});

test("stu02fe AC6 slow load past 10 seconds times out with an error panel (fake clock)", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { getSet: [{ hang: true }] },
  });
  await page.clock.install();
  await page.goto("/student/practice");
  await expect.poll(() => mock.count("getSet")).toBe(1);
  await page.clock.fastForward(11_000);
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(0);
});

test("stu02fe AC7 start another attempt gives an empty form and a new server attempt", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page);
  await submitCompleteSet(page, mock, TWO_OF_THREE);
  await page.getByRole("button", { name: "Start another attempt" }).click();
  for (const q of FIXTURE_SET.questions)
    for (const c of q.choices)
      await expect(radio(page, q.id, c.id)).not.toBeChecked();
  for (const r of await page.getByRole("radio").all())
    await expect(r).toBeEnabled();
  await expect(page.getByText("0 of 3 answered")).toBeVisible();
  const text = await pageText(page);
  for (const explanation of EXPLANATIONS)
    expect(text).not.toContain(explanation);
  // No request is made until the student submits again.
  expect(mock.count("start")).toBe(1);
  await pick(page, ALL_CORRECT);
  await submitButton(page).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  expect(mock.count("start")).toBe(2);
  const [first, second] = mock.of("save");
  if (!first || !second) throw new Error("expected two saves");
  expect(second.attemptId).not.toBe(first.attemptId);
  expect(mock.of("submit")[1].attemptId).toBe(second.attemptId);
  expect(second.body).toEqual({ answers: ALL_CORRECT });
});

test("stu02fe AC8 scripts downloaded for /student/practice contain no answer key", async ({
  page,
}) => {
  await mockPracticeApi(page);
  const bodies: { url: string; text: string }[] = [];
  const pending: Promise<void>[] = [];
  page.on("response", (response) => {
    if (response.request().resourceType() !== "script") return;
    pending.push(
      response
        .text()
        .then((text) => {
          bodies.push({ url: response.url(), text });
        })
        .catch(() => undefined),
    );
  });
  await openPractice(page);
  await page.waitForLoadState("networkidle");
  await Promise.all(pending);
  expect(bodies.length).toBeGreaterThan(0);
  for (const { url, text } of bodies) {
    for (const explanation of EXPLANATIONS)
      expect(text, `${url} leaks an explanation`).not.toContain(explanation);
    expect(text, `${url} has a correct-choice label`).not.toContain(
      "Correct choice",
    );
    expect(text, `${url} has an answer field`).not.toMatch(
      /answer:\s*["'](A single, focused responsibility|To catch regressions when code changes|3)["']/,
    );
  }
  // The scripts are the student app, not the teacher or admin pages.
  expect(bodies.some((b) => /pages\/Teacher|teacherDemo/.test(b.url))).toBe(
    false,
  );
});

test("stu02fe AC8 teacher pages still show their demo answers (loaded on demand)", async ({
  page,
}) => {
  await mockPracticeApi(page);
  await page.goto("/teacher/practice");
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  await expect(
    page.getByText(FIXTURE_KEY.q2.explanation).first(),
  ).toBeVisible();
  await page.goto("/teacher/review");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.getByRole("tab", { name: "Practice questions & answers" }).click();
  await expect
    .poll(async () =>
      page
        .locator("textarea, input")
        .evaluateAll((els) =>
          els.map((el) => (el as HTMLInputElement).value).join("\n"),
        ),
    )
    .toContain(EXPLANATIONS[0]);
  await page.goto("/admin/overview");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("stu02fe AC9 study companion reflects submitted or not submitted on the Practice page", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page);
  await openPractice(page);
  await page.getByRole("button", { name: "Open study companion" }).click();
  const chat = page.getByRole("dialog", { name: "Your study companion" });
  await expect(chat).toBeVisible();
  await expect(chat).toContainText("Hints only before whole-set submission");
  await expect(chat).not.toContainText("Practice submitted");
  await page.getByRole("button", { name: "Minimise study companion" }).click();
  await pick(page, ALL_CORRECT);
  await submitButton(page).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  expect(mock.count("results")).toBe(1);
  await page.getByRole("button", { name: "Open study companion" }).click();
  await expect(chat).toContainText("Practice submitted");
});

test("stu02fe AC10 answers survive navigating away and back", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page);
  await openPractice(page);
  await pick(page, { q1: "b", q2: "b" });
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page).toHaveURL(/\/student\/overview$/);
  await page.getByRole("link", { name: "Practice", exact: true }).click();
  await expect(radio(page, "q1", "b")).toBeChecked();
  await expect(radio(page, "q2", "b")).toBeChecked();
  await expect(page.getByText("2 of 3 answered")).toBeVisible();
  expect(mock.mutating).toEqual([]);
});

test("stu02fe AC10 results survive navigating away and back", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page);
  await submitCompleteSet(page, mock, TWO_OF_THREE);
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page).toHaveURL(/\/student\/overview$/);
  await page.getByRole("link", { name: "Practice", exact: true }).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  await expect(page.getByText(scoreText(2)).first()).toBeVisible();
  await expect(radio(page, "q3", "a")).toBeChecked();
  await expect(radio(page, "q3", "a")).toBeDisabled();
  expect(mock.count("submit")).toBe(1);
});

test("stu02fe AC11 every practice request sends one constant X-Student-Id and no storage is used", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page);
  await submitCompleteSet(page, mock, TWO_OF_THREE);
  const ids = mock
    .of("start")
    .concat(mock.of("save"), mock.of("submit"), mock.of("results"))
    .map((r) => r.headers["x-student-id"]);
  expect(ids).toHaveLength(4);
  for (const id of ids) expect(id?.trim()).toBeTruthy();
  expect(new Set(ids).size).toBe(1);
  const storage = await page.evaluate(() => ({
    local: localStorage.length,
    session: sessionStorage.length,
  }));
  expect(storage).toEqual({ local: 0, session: 0 });
  // No credentials or tokens were added to any request.
  for (const r of mock.requests) {
    expect(r.headers["authorization"]).toBeUndefined();
    expect(r.headers["cookie"]).toBeUndefined();
  }
});

test("stu02fe security server text is rendered as text, never as HTML", async ({
  page,
}) => {
  const payload = '<img src="x" onerror="window.__xss = 1">';
  const set = {
    ...FIXTURE_SET,
    title: `Title ${payload}`,
    questions: FIXTURE_SET.questions.map((q, i) =>
      i === 0
        ? {
            ...q,
            text: `Question ${payload}`,
            choices: [
              { id: "a", text: `<b>bold-choice</b>` },
              ...q.choices.slice(1),
            ],
          }
        : q,
    ),
  };
  const key = {
    ...FIXTURE_KEY,
    q1: { correct: "a", explanation: `Explain ${payload}` },
  };
  await mockPracticeApi(page, { set, key });
  await page.goto("/student/practice");
  await expect(page.getByText("<b>bold-choice</b>")).toBeVisible();
  await page.getByRole("radio", { name: "<b>bold-choice</b>" }).check();
  await radio(page, "q2", "b").check();
  await radio(page, "q3", "c").check();
  await submitButton(page).click();
  await expect(page.getByText(`Explain ${payload}`)).toBeVisible();
  await expect(page.locator('img[src="x"]')).toHaveCount(0);
  await expect(page.locator("b", { hasText: "bold-choice" })).toHaveCount(0);
  expect(
    await page.evaluate(
      () => (window as unknown as Record<string, unknown>).__xss,
    ),
  ).toBeUndefined();
});

test("stu02fe security a double click on Submit sends one flow", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { submit: [{ delayMs: 600, passThrough: true }] },
  });
  await openPractice(page);
  await pick(page, ALL_CORRECT);
  await submitButton(page).dblclick();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  expect(mock.count("start")).toBe(1);
  expect(mock.count("save")).toBe(1);
  expect(mock.count("submit")).toBe(1);
  expect(mock.count("results")).toBe(1);
});

test("stu02fe security the submit button is disabled while a submit is running", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: { submit: [{ hang: true }] },
  });
  await openPractice(page);
  await pick(page, ALL_CORRECT);
  await submitButton(page).click();
  await expect.poll(() => mock.count("submit")).toBe(1);
  await expect(submitButton(page)).toBeDisabled();
  expect(mock.count("results")).toBe(0);
  mock.release();
});

test("stu02fe security results are requested only after a successful submit", async ({
  page,
}) => {
  const mock = await mockPracticeApi(page, {
    replies: {
      submit: [apiError(422, "incomplete", { missing: ["q1"] })],
    },
  });
  await openPractice(page);
  await pick(page, ALL_CORRECT);
  await submitButton(page).click();
  await expect(page.getByRole("alert")).toBeVisible();
  expect(mock.count("results")).toBe(0);
});

test("stu02fe security identifiers from the server are URL-encoded in paths", async ({
  page,
}) => {
  const odd = "att/../e?mpt#1 x";
  const mock = await mockPracticeApi(page, {
    replies: {
      start: [
        {
          status: 201,
          json: {
            attempt_id: odd,
            set_id: SET_ID,
            status: "in_progress",
            answers: {},
          },
        },
      ],
    },
  });
  mock.script("save", {
    status: 200,
    json: { attempt_id: odd, status: "in_progress", answers: ALL_CORRECT },
  });
  mock.script("submit", {
    status: 200,
    json: {
      attempt_id: odd,
      status: "submitted",
      score: { correct: 3, total: 3 },
    },
  });
  mock.script("results", { json: buildResults(odd, ALL_CORRECT) });
  await openPractice(page);
  await pick(page, ALL_CORRECT);
  await submitButton(page).click();
  await expect(page.getByText(EXPLANATIONS[0]).first()).toBeVisible();
  const expected = `/api/attempts/${encodeURIComponent(odd)}`;
  expect(mock.of("save")[0].path).toBe(`${expected}/answers`);
  expect(mock.of("submit")[0].path).toBe(`${expected}/submit`);
  expect(mock.of("results")[0].path).toBe(`${expected}/results`);
});

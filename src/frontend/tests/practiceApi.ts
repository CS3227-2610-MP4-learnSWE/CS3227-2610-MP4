import type { Page, Route } from "@playwright/test";

/**
 * Mock of the STU-02 practice API (contract: workflow/specs/STU-02/plan.md).
 * Acts as a small stateful fake server so a normal flow works without any
 * overrides, records every request, and lets a test script failures per step.
 */

export const SET_ID = "intro-se-1";

export interface FixtureQuestion {
  id: string;
  text: string;
  code: string | null;
  choices: { id: string; text: string }[];
}
export interface FixtureSet {
  id: string;
  title: string;
  questions: FixtureQuestion[];
}
export interface KeyEntry {
  correct: string;
  explanation: string;
}

export const FIXTURE_SET: FixtureSet = {
  id: SET_ID,
  title: "Software engineering basics",
  questions: [
    {
      id: "q1",
      text: "What should a well-designed function have?",
      code: null,
      choices: [
        { id: "a", text: "A single, focused responsibility" },
        { id: "b", text: "As many responsibilities as possible" },
        { id: "c", text: "No descriptive name" },
      ],
    },
    {
      id: "q2",
      text: "Why do we keep automated tests alongside our code?",
      code: null,
      choices: [
        { id: "a", text: "To make the repository larger" },
        { id: "b", text: "To catch regressions when code changes" },
        { id: "c", text: "To avoid ever reviewing code" },
      ],
    },
    {
      id: "q3",
      text: "What does this Python code print?",
      code: "values = [1, 2, 3]\nprint(len(values))",
      choices: [
        { id: "a", text: "2" },
        { id: "b", text: "4" },
        { id: "c", text: "3" },
      ],
    },
  ],
};

export const FIXTURE_KEY: Record<string, KeyEntry> = {
  q1: {
    correct: "a",
    explanation:
      "One focused responsibility makes a function easier to understand, test and change.",
  },
  q2: {
    correct: "b",
    explanation:
      "Tests protect expected behaviour and can catch regressions introduced by later changes.",
  },
  q3: {
    correct: "c",
    explanation:
      "len returns the number of items. The list contains three items.",
  },
};

/** Choice ids that give a full score. */
export const ALL_CORRECT: Record<string, string> = {
  q1: "a",
  q2: "b",
  q3: "c",
};
/** Choice ids that give 2 of 3 (q3 wrong). */
export const TWO_OF_THREE: Record<string, string> = {
  q1: "a",
  q2: "b",
  q3: "a",
};

export type Step =
  "getSet" | "start" | "getAttempt" | "save" | "submit" | "results";

/** One scripted reply. Without `json`/`body` the default fake server answers. */
export interface Reply {
  status?: number;
  json?: unknown;
  /** Raw body (for non-JSON replies). */
  body?: string;
  /** Simulate an unreachable backend. */
  abort?: boolean;
  /** Never answer until `mock.release()` (for timeout tests). */
  hang?: boolean;
  /** Answer after this many real milliseconds. */
  delayMs?: number;
  /** Let the default fake server answer, but after delayMs. */
  passThrough?: boolean;
}

export interface MockOptions {
  set?: FixtureSet | unknown;
  key?: Record<string, KeyEntry>;
  /** Replies consumed in order, one per request of that step. */
  replies?: Partial<Record<Step, Reply[]>>;
}

export interface RecordedRequest {
  step: Step;
  method: string;
  path: string;
  headers: Record<string, string>;
  body: unknown;
  attemptId: string | null;
}

export function apiError(
  status: number,
  code: string,
  extra: Record<string, unknown> = {},
): Reply {
  return {
    status,
    json: {
      detail: { code, message: `Server says ${code}`, ...extra },
    },
  };
}

export function buildResults(
  attemptId: string,
  answers: Record<string, string>,
  set: FixtureSet = FIXTURE_SET,
  key: Record<string, KeyEntry> = FIXTURE_KEY,
) {
  const questions = set.questions.map((q) => ({
    id: q.id,
    selected: answers[q.id] ?? null,
    correct_choice: key[q.id].correct,
    correct: answers[q.id] === key[q.id].correct,
    explanation: key[q.id].explanation,
  }));
  return {
    attempt_id: attemptId,
    set_id: set.id,
    key_version: "v1",
    score: {
      correct: questions.filter((q) => q.correct).length,
      total: questions.length,
    },
    answers,
    questions,
  };
}

interface FakeAttempt {
  student: string;
  answers: Record<string, string>;
  status: "in_progress" | "submitted";
}

export class PracticeApiMock {
  readonly requests: RecordedRequest[] = [];
  readonly replies: Partial<Record<Step, Reply[]>>;
  private readonly attempts = new Map<string, FakeAttempt>();
  private readonly waiting: (() => void)[] = [];
  private counter = 0;

  constructor(
    readonly set: FixtureSet | unknown,
    readonly key: Record<string, KeyEntry>,
    replies: Partial<Record<Step, Reply[]>>,
  ) {
    this.replies = replies;
  }

  /** Queue scripted replies for a step (consumed in order). */
  script(step: Step, ...replies: Reply[]) {
    this.replies[step] = [...(this.replies[step] ?? []), ...replies];
  }

  of(step: Step) {
    return this.requests.filter((r) => r.step === step);
  }
  count(step: Step) {
    return this.of(step).length;
  }
  /** Requests that change server state (anything but GET). */
  get mutating() {
    return this.requests.filter((r) => r.method !== "GET");
  }
  /** Step names in the order the page made the requests. */
  get order() {
    return this.requests.map((r) => r.step);
  }
  release() {
    this.waiting.splice(0).forEach((resolve) => resolve());
  }

  async handle(route: Route) {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const path = url.pathname;
    const classified = this.classify(method, path);
    if (!classified) {
      await route.fulfill({
        status: 404,
        json: { detail: { code: "not_found", message: "no such route" } },
      });
      return;
    }
    const { step, attemptId } = classified;
    let body: unknown = null;
    try {
      body = request.postDataJSON();
    } catch {
      body = request.postData();
    }
    this.requests.push({
      step,
      method,
      path,
      headers: request.headers(),
      body,
      attemptId,
    });

    const scripted = this.replies[step]?.shift();
    if (scripted) {
      if (scripted.abort) {
        await route.abort("connectionrefused");
        return;
      }
      if (scripted.hang) {
        await new Promise<void>((resolve) => this.waiting.push(resolve));
        await route.abort("timedout").catch(() => undefined);
        return;
      }
      if (scripted.delayMs) {
        await new Promise((resolve) => setTimeout(resolve, scripted.delayMs));
      }
      if (!scripted.passThrough) {
        await route.fulfill({
          status: scripted.status ?? 200,
          ...(scripted.body !== undefined
            ? { body: scripted.body, contentType: "application/json" }
            : { json: scripted.json }),
        });
        return;
      }
    }
    const reply = this.defaultReply(
      step,
      attemptId,
      request.headers()["x-student-id"]?.trim() ?? "",
      body,
    );
    await route.fulfill({ status: reply.status, json: reply.json });
  }

  private classify(
    method: string,
    path: string,
  ): { step: Step; attemptId: string | null } | null {
    const set = path.match(/^\/api\/practice-sets\/([^/]+)$/);
    if (set && method === "GET") return { step: "getSet", attemptId: null };
    const start = path.match(/^\/api\/practice-sets\/([^/]+)\/attempts$/);
    if (start && method === "POST") return { step: "start", attemptId: null };
    const attempt = path.match(/^\/api\/attempts\/([^/]+)(?:\/(\w+))?$/);
    if (attempt) {
      const id = decodeURIComponent(attempt[1]);
      const tail = attempt[2];
      if (!tail && method === "GET")
        return { step: "getAttempt", attemptId: id };
      if (tail === "answers" && method === "PUT")
        return { step: "save", attemptId: id };
      if (tail === "submit" && method === "POST")
        return { step: "submit", attemptId: id };
      if (tail === "results" && method === "GET")
        return { step: "results", attemptId: id };
    }
    return null;
  }

  private defaultReply(
    step: Step,
    attemptId: string | null,
    student: string,
    body: unknown,
  ): { status: number; json: unknown } {
    const err = (status: number, code: string, extra = {}) => ({
      status,
      json: { detail: { code, message: code, ...extra } },
    });
    if (step === "getSet") return { status: 200, json: this.set };
    if (!student) return err(401, "missing_student");
    if (step === "start") {
      const id = `attempt-${String(++this.counter).padStart(4, "0")}`;
      this.attempts.set(id, {
        student,
        answers: {},
        status: "in_progress",
      });
      return {
        status: 201,
        json: {
          attempt_id: id,
          set_id: SET_ID,
          status: "in_progress",
          answers: {},
        },
      };
    }
    const attempt = attemptId ? this.attempts.get(attemptId) : undefined;
    if (!attemptId || !attempt || attempt.student !== student)
      return err(404, "attempt_not_found");
    const set = this.set as FixtureSet;
    if (step === "getAttempt")
      return {
        status: 200,
        json: {
          attempt_id: attemptId,
          set_id: SET_ID,
          status: attempt.status,
          answers: attempt.answers,
        },
      };
    if (step === "save") {
      if (attempt.status === "submitted") return err(409, "already_submitted");
      const sent = (body as { answers?: Record<string, string> } | null)
        ?.answers;
      if (!sent || typeof sent !== "object")
        return { status: 422, json: { detail: [{ msg: "bad body" }] } };
      for (const [q, c] of Object.entries(sent)) {
        const question = set.questions.find((x) => x.id === q);
        if (!question) return err(422, "unknown_question");
        if (!question.choices.some((x) => x.id === c))
          return err(422, "invalid_choice");
      }
      Object.assign(attempt.answers, sent);
      return {
        status: 200,
        json: {
          attempt_id: attemptId,
          status: "in_progress",
          answers: attempt.answers,
        },
      };
    }
    if (step === "submit") {
      if (attempt.status === "submitted") return err(409, "already_submitted");
      const missing = set.questions
        .filter((q) => !attempt.answers[q.id])
        .map((q) => q.id);
      if (missing.length) return err(422, "incomplete", { missing });
      attempt.status = "submitted";
      const results = buildResults(attemptId, attempt.answers, set, this.key);
      return {
        status: 200,
        json: {
          attempt_id: attemptId,
          status: "submitted",
          score: results.score,
        },
      };
    }
    // results
    if (attempt.status !== "submitted") return err(403, "not_submitted");
    return {
      status: 200,
      json: buildResults(attemptId, attempt.answers, set, this.key),
    };
  }
}

/**
 * Register the practice API mock on a page. Call it after any broader route
 * (later routes win in Playwright), and before `page.goto`.
 */
export async function mockPracticeApi(
  page: Page,
  options: MockOptions = {},
): Promise<PracticeApiMock> {
  const mock = new PracticeApiMock(
    options.set ?? FIXTURE_SET,
    options.key ?? FIXTURE_KEY,
    Object.fromEntries(
      Object.entries(options.replies ?? {}).map(([k, v]) => [k, [...v]]),
    ),
  );
  await page.route(
    (url) =>
      url.pathname.startsWith("/api/practice-sets") ||
      url.pathname.startsWith("/api/attempts"),
    (route) => mock.handle(route),
  );
  return mock;
}

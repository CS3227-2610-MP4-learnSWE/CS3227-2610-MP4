import type { Page, Route } from "@playwright/test";
import { mockAuthApi, STUDENT, type AuthApiMock, type User } from "./authApi";
import {
  COURSE_ALGO,
  COURSE_SE,
  L_TESTING,
  mockLessonsApi,
  type LessonsApiMock,
  type LessonsOptions,
} from "./lessonsApi";

/**
 * Mock of GET /api/progress (contract: workflow/specs/STU-04/plan.md).
 * A small fake server: it serves one body (fixed, computed per request, or derived from a
 * LessonsApiMock so completions made through the lesson page show up), records every request and
 * lets a test script a reply per request. No backend is used.
 */

export interface ProgressBody {
  lessons: {
    totals: { lesson_count: number; completed_count: number };
    courses: {
      id: string;
      title: string;
      lesson_count: number;
      completed_count: number;
    }[];
    recent: {
      lesson_id: string;
      course_id: string;
      title: string;
      completed_at: string;
    }[];
  };
  practice: {
    sets: {
      set_id: string;
      title: string;
      attempts_submitted: number;
      best: { correct: number; total: number };
      latest: { correct: number; total: number; submitted_at: string };
    }[];
    average_latest_percent: number | null;
  };
  topics: {
    rule: { min_answers: number; weak_below_percent: number };
    items: {
      topic: { id: string | null; name: string };
      answered: number;
      correct: number;
      accuracy_percent: number;
      status: "needs_practice" | "on_track" | "insufficient";
    }[];
  };
}

export const RULE = { min_answers: 3, weak_below_percent: 60 };

/** The exact rule paragraph of the spec for the default rule. */
export const RULE_TEXT =
  "A topic needs practice when you have answered at least 3 questions on it and fewer than 60% were correct. Only your latest submitted attempt on each practice set counts.";

/** Exact messages from the spec's "UI states and copy" (single place for the specs). */
export const MSG = {
  offline: "Could not reach the server. Check your connection and try again.",
  unavailable: "Progress is unavailable right now. Please try again.",
  badShape: "Progress could not be read. Please try again.",
  forbidden: "You do not have access to progress.",
  signIn: "Sign in to see your lessons and practice progress.",
  loading: "Loading your progress…",
  noCourses:
    "You are not enrolled in any course yet. Ask your teacher or an administrator to add you, and your lesson progress will appear here.",
  noPractice: "Submit a practice set to see your scores here.",
  noTopics: "Topics appear here after you submit a practice set.",
  allInsufficient:
    "Topics are suggested once you have answered at least 3 questions on them. Keep practising and check back.",
  noneNeedPractice: "No topics need extra practice right now.",
  noLessonsDone: "No lessons completed yet.",
  noLessonsPublished: "No lessons published yet.",
  statOffline: "Could not reach the server.",
  statUnavailable: "Progress is unavailable right now.",
  statForbidden: "You do not have access to progress.",
  statSignIn: "Sign in to see your progress",
} as const;

export const SET_ID = "intro-se-1";
export const SET_TITLE = "Software engineering basics";
export const TOPIC_BASICS = "66666666-6666-4666-8666-666666666661";
export const TOPIC_TESTING = "33333333-3333-4333-8333-333333333333";
export const TOPIC_DESIGN = "77777777-7777-4777-8777-777777777777";

export function emptyProgress(): ProgressBody {
  return {
    lessons: {
      totals: { lesson_count: 0, completed_count: 0 },
      courses: [],
      recent: [],
    },
    practice: { sets: [], average_latest_percent: null },
    topics: { rule: { ...RULE }, items: [] },
  };
}

/** A full body: 2 courses (1 of 3 lessons), one practice set, three topics (one of each status). */
export function sampleProgress(): ProgressBody {
  return {
    lessons: {
      totals: { lesson_count: 3, completed_count: 1 },
      courses: [
        {
          id: COURSE_ALGO,
          title: "Algorithms",
          lesson_count: 1,
          completed_count: 0,
        },
        {
          id: COURSE_SE,
          title: "Software Engineering",
          lesson_count: 2,
          completed_count: 1,
        },
      ],
      recent: [
        {
          lesson_id: L_TESTING,
          course_id: COURSE_SE,
          title: "Unit testing basics",
          completed_at: "2026-02-01T10:00:00Z",
        },
      ],
    },
    practice: {
      sets: [
        {
          set_id: SET_ID,
          title: SET_TITLE,
          attempts_submitted: 3,
          best: { correct: 2, total: 3 },
          latest: {
            correct: 1,
            total: 3,
            submitted_at: "2026-02-02T10:00:00Z",
          },
        },
      ],
      average_latest_percent: 33,
    },
    topics: {
      rule: { ...RULE },
      items: [
        {
          topic: { id: TOPIC_BASICS, name: SET_TITLE },
          answered: 3,
          correct: 1,
          accuracy_percent: 33,
          status: "needs_practice",
        },
        {
          topic: { id: TOPIC_TESTING, name: "Testing" },
          answered: 5,
          correct: 3,
          accuracy_percent: 60,
          status: "on_track",
        },
        {
          topic: { id: TOPIC_DESIGN, name: "Design" },
          answered: 2,
          correct: 1,
          accuracy_percent: 50,
          status: "insufficient",
        },
      ],
    },
  };
}

export interface Reply {
  status?: number;
  json?: unknown;
  body?: string;
  abort?: boolean;
  /** Do not answer until `mock.release()`. */
  hang?: boolean;
  /** Let the default server answer, but only after this many real milliseconds. */
  delayMs?: number;
}

export interface RecordedProgressRequest {
  method: string;
  path: string;
  search: string;
  headers: Record<string, string>;
}

export function progressError(
  status: number,
  code: string,
  message = `Server says ${code}`,
): Reply {
  return { status, json: { detail: { code, message } } };
}

export interface ProgressOptions {
  /** Fixed body, or a function evaluated per request. */
  body?: ProgressBody | (() => ProgressBody);
  replies?: Reply[];
  auth?: AuthApiMock;
}

export class ProgressApiMock {
  readonly requests: RecordedProgressRequest[] = [];
  body: ProgressBody | (() => ProgressBody);
  private readonly replies: Reply[];
  private readonly waiting: (() => void)[] = [];
  private readonly auth?: AuthApiMock;

  constructor(options: ProgressOptions = {}) {
    this.body = options.body ?? emptyProgress();
    this.replies = [...(options.replies ?? [])];
    this.auth = options.auth;
  }

  /** Queue replies, one per upcoming request. */
  script(...replies: Reply[]) {
    this.replies.push(...replies);
  }
  get count() {
    return this.requests.length;
  }
  release() {
    this.waiting.splice(0).forEach((resolve) => resolve());
  }

  async handle(route: Route) {
    const request = route.request();
    const url = new URL(request.url());
    this.requests.push({
      method: request.method(),
      path: url.pathname,
      search: url.search,
      headers: request.headers(),
    });
    const scripted = this.replies.shift();
    if (scripted?.abort) {
      await route.abort("connectionrefused");
      return;
    }
    if (scripted?.hang) {
      await new Promise<void>((resolve) => this.waiting.push(resolve));
      await route.abort("timedout").catch(() => undefined);
      return;
    }
    if (scripted?.delayMs)
      await new Promise((resolve) => setTimeout(resolve, scripted.delayMs));
    let reply: Reply;
    if (
      scripted &&
      (scripted.json !== undefined ||
        scripted.body !== undefined ||
        scripted.status)
    )
      reply = scripted;
    else if (this.auth && !this.auth.user)
      reply = progressError(401, "unauthenticated", "Sign in to continue.");
    else if (this.auth && this.auth.user!.role !== "student")
      reply = progressError(
        403,
        "forbidden",
        "You do not have access to this.",
      );
    else
      reply = {
        json: typeof this.body === "function" ? this.body() : this.body,
      };
    await route
      .fulfill({
        status: reply.status ?? 200,
        headers: { "cache-control": "no-store" },
        ...(reply.body !== undefined
          ? { body: reply.body, contentType: "application/json" }
          : { json: reply.json }),
      })
      .catch(() => undefined);
  }
}

/** Register the progress mock on a page. Call before `page.goto`. */
export async function mockProgressApi(
  page: Page,
  options: ProgressOptions = {},
): Promise<ProgressApiMock> {
  const mock = new ProgressApiMock(options);
  await page.route(
    (url) => url.pathname === "/api/progress",
    (route) => mock.handle(route),
  );
  return mock;
}

/** A signed-in student (or another user, or null for demo mode) behind one session. */
export async function signedInProgress(
  page: Page,
  options: Omit<ProgressOptions, "auth"> & { user?: User | null } = {},
) {
  const { user = STUDENT, ...rest } = options;
  const auth = await mockAuthApi(page, { user });
  const api = await mockProgressApi(page, { ...rest, auth });
  return { auth, api };
}

/**
 * Progress derived from the study mock, so a completion made on the lesson page changes the next
 * progress response (same session, same counts as STU-01).
 */
export function progressFromLessons(
  lessons: LessonsApiMock,
): () => ProgressBody {
  return () => {
    const body = emptyProgress();
    const visible = (courseId: string) =>
      lessons.lessons.filter(
        (l) => l.course_id === courseId && !lessons.withdrawn.has(l.id),
      );
    const courses = [...lessons.courses]
      .sort((a, b) =>
        a.title.toLowerCase().localeCompare(b.title.toLowerCase()),
      )
      .map((c) => ({
        id: c.id,
        title: c.title,
        lesson_count: visible(c.id).length,
        completed_count: visible(c.id).filter((l) => lessons.done.has(l.id))
          .length,
      }));
    body.lessons.courses = courses;
    body.lessons.totals = {
      lesson_count: courses.reduce((n, c) => n + c.lesson_count, 0),
      completed_count: courses.reduce((n, c) => n + c.completed_count, 0),
    };
    body.lessons.recent = [...lessons.done.entries()]
      .sort((a, b) => b[1].localeCompare(a[1]))
      .slice(0, 5)
      .flatMap(([id, at]) => {
        const l = lessons.lessons.find((x) => x.id === id);
        return l
          ? [
              {
                lesson_id: id,
                course_id: l.course_id,
                title: l.title,
                completed_at: at,
              },
            ]
          : [];
      });
    return body;
  };
}

/**
 * Student session with both the study mock (lessons) and the progress mock derived from it.
 * Used where a test completes a lesson and then looks at progress.
 */
export async function signedInStudyAndProgress(
  page: Page,
  options: Omit<LessonsOptions, "auth"> & {
    user?: User | null;
    progressReplies?: Reply[];
  } = {},
) {
  const { user = STUDENT, progressReplies, ...rest } = options;
  const auth = await mockAuthApi(page, { user });
  const lessons = await mockLessonsApi(page, { ...rest, auth });
  const progress = await mockProgressApi(page, {
    body: progressFromLessons(lessons),
    replies: progressReplies,
    auth,
  });
  return { auth, lessons, progress };
}

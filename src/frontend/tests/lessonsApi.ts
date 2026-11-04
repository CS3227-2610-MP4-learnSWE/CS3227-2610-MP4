import type { Page, Route } from "@playwright/test";
import { mockAuthApi, STUDENT, type AuthApiMock, type User } from "./authApi";

/**
 * Mock of the STU-01 study API (contract: workflow/specs/STU-01/plan.md).
 * A small stateful fake server: it serves the four /api/study paths from fixture data, keeps the
 * completion state, records every request and lets a test script a failure per step.
 */

export const COURSE_SE = "11111111-1111-4111-8111-111111111111";
export const COURSE_ALGO = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
export const TOPIC_TESTING = "33333333-3333-4333-8333-333333333333";
export const TOPIC_DESIGN = "77777777-7777-4777-8777-777777777777";

export const L_TESTING = "55555555-5555-4555-8555-555555555551";
export const L_GENERAL = "55555555-5555-4555-8555-555555555552";
export const L_DESIGN = "66666666-6666-4666-8666-666666666661";
export const L_BSEARCH = "88888888-8888-4888-8888-888888888881";

export interface FixtureCourse {
  id: string;
  title: string;
}
export interface FixtureLesson {
  id: string;
  course_id: string;
  topic: { id: string | null; name: string };
  title: string;
  content: string;
  published_at: string;
}

export const COURSES: FixtureCourse[] = [
  { id: COURSE_SE, title: "Software Engineering" },
  { id: COURSE_ALGO, title: "Algorithms" },
];

export const LESSONS: FixtureLesson[] = [
  {
    id: L_TESTING,
    course_id: COURSE_SE,
    topic: { id: TOPIC_TESTING, name: "Testing" },
    title: "Unit testing basics",
    content: "Write small tests first.\nRun them often.",
    published_at: "2026-01-01T09:00:00Z",
  },
  {
    id: L_DESIGN,
    course_id: COURSE_SE,
    topic: { id: TOPIC_DESIGN, name: "Design" },
    title: "Design for change",
    content: "Keep modules small and focused.",
    published_at: "2026-01-02T09:00:00Z",
  },
  {
    id: L_GENERAL,
    course_id: COURSE_SE,
    topic: { id: null, name: "General" },
    title: "Clean code habits",
    content: "Name things well.\n\nKeep functions short.",
    published_at: "2026-01-03T09:00:00Z",
  },
  {
    id: L_BSEARCH,
    course_id: COURSE_ALGO,
    topic: { id: null, name: "General" },
    title: "Binary search basics",
    content: "Halve the search space each step.",
    published_at: "2026-01-04T09:00:00Z",
  },
];

/** Exact messages from the spec's "UI states and copy" (single place for the specs). */
export const MSG = {
  offline: "Could not reach the server. Check your connection and try again.",
  unavailable: "Study materials are unavailable right now. Please try again.",
  badShape: "Study materials could not be read. Please try again.",
  forbidden: "You do not have access to study materials.",
  courseGone: "This course is not available to you.",
  saveOffline: "Could not reach the server. Your progress was not saved.",
  saveFailed: "Could not save your progress. Nothing was changed.",
  signIn: "Sign in to read study materials and track your progress.",
  loadingList: "Loading study materials…",
  loadingLesson: "Loading lesson…",
  noCourses:
    "You are not enrolled in any course yet. Ask your teacher or an administrator to add you.",
  noLessons:
    "Your teacher has not published lessons in this course yet. Check back soon.",
  noMatch: "Try another topic or a different search.",
} as const;

export type Step = "courses" | "lessons" | "lesson" | "put";

export interface Reply {
  status?: number;
  json?: unknown;
  /** Raw body, for non-JSON replies. */
  body?: string;
  /** Simulate an unreachable backend. */
  abort?: boolean;
  /** Do not answer until `mock.release()`. */
  hang?: boolean;
  /** Let the default server answer, but only after this many real milliseconds. */
  delayMs?: number;
}

export interface RecordedStudyRequest {
  step: Step;
  method: string;
  path: string;
  headers: Record<string, string>;
  body: unknown;
  courseId: string | null;
  lessonId: string | null;
}

export function studyError(
  status: number,
  code: string,
  message = `Server says ${code}`,
  extra: Record<string, unknown> = {},
): Reply {
  return { status, json: { detail: { code, message, ...extra } } };
}

export interface LessonsOptions {
  courses?: FixtureCourse[];
  lessons?: FixtureLesson[];
  /** Lesson ids already completed on the server. */
  done?: string[];
  replies?: Partial<Record<Step, Reply[]>>;
  /** Behave like the real server for sessions: 401 signed out, 403 other roles, CSRF on PUT. */
  auth?: AuthApiMock;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export class LessonsApiMock {
  readonly requests: RecordedStudyRequest[] = [];
  courses: FixtureCourse[];
  lessons: FixtureLesson[];
  /** lesson id -> completed_at (ISO) for completed lessons. */
  readonly done = new Map<string, string>();
  readonly withdrawn = new Set<string>();
  private readonly replies: Partial<Record<Step, Reply[]>>;
  private readonly waiting: (() => void)[] = [];
  private readonly auth?: AuthApiMock;

  constructor(options: LessonsOptions = {}) {
    this.courses = options.courses ?? COURSES;
    this.lessons = options.lessons ?? LESSONS;
    for (const id of options.done ?? [])
      this.done.set(id, "2026-02-01T10:00:00.000Z");
    this.replies = { ...(options.replies ?? {}) };
    this.auth = options.auth;
  }

  script(step: Step, ...replies: Reply[]) {
    this.replies[step] = [...(this.replies[step] ?? []), ...replies];
  }
  of(step: Step) {
    return this.requests.filter((r) => r.step === step);
  }
  count(step: Step) {
    return this.of(step).length;
  }
  get last() {
    return this.requests[this.requests.length - 1];
  }
  release() {
    this.waiting.splice(0).forEach((resolve) => resolve());
  }
  isDone(id: string) {
    return this.done.has(id);
  }

  private visible(courseId: string) {
    return this.lessons.filter(
      (l) => l.course_id === courseId && !this.withdrawn.has(l.id),
    );
  }
  private counts(courseId: string) {
    const lessons = this.visible(courseId);
    return {
      lesson_count: lessons.length,
      completed_count: lessons.filter((l) => this.done.has(l.id)).length,
    };
  }

  async handle(route: Route) {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname;
    const classified = this.classify(method, path);
    if (!classified) {
      await route.fulfill(studyReply(studyError(404, "not_found")));
      return;
    }
    let body: unknown = null;
    try {
      body = request.postDataJSON();
    } catch {
      body = request.postData();
    }
    this.requests.push({
      step: classified.step,
      method,
      path,
      headers: request.headers(),
      body,
      courseId: classified.courseId,
      lessonId: classified.lessonId,
    });
    const scripted = this.replies[classified.step]?.shift();
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
    if (
      scripted &&
      (scripted.json !== undefined ||
        scripted.body !== undefined ||
        scripted.status)
    ) {
      await route.fulfill(studyReply(scripted)).catch(() => undefined);
      return;
    }
    const denied = this.sessionError(method, request.headers());
    const reply = denied ?? this.defaultReply(classified, body);
    await route.fulfill(studyReply(reply)).catch(() => undefined);
  }

  private classify(method: string, path: string) {
    let m: RegExpMatchArray | null;
    if (path === "/api/study/courses" && method === "GET")
      return { step: "courses" as Step, courseId: null, lessonId: null };
    if (
      (m = path.match(/^\/api\/study\/courses\/([^/]+)\/lessons$/)) &&
      method === "GET"
    )
      return {
        step: "lessons" as Step,
        courseId: decodeURIComponent(m[1]),
        lessonId: null,
      };
    if (
      (m = path.match(/^\/api\/study\/lessons\/([^/]+)$/)) &&
      method === "GET"
    )
      return {
        step: "lesson" as Step,
        courseId: null,
        lessonId: decodeURIComponent(m[1]),
      };
    if (
      (m = path.match(/^\/api\/study\/lessons\/([^/]+)\/completion$/)) &&
      method === "PUT"
    )
      return {
        step: "put" as Step,
        courseId: null,
        lessonId: decodeURIComponent(m[1]),
      };
    return null;
  }

  private sessionError(
    method: string,
    headers: Record<string, string>,
  ): Reply | null {
    if (!this.auth) return null;
    if (!this.auth.user) return studyError(401, "unauthenticated");
    if (method !== "GET" && headers["x-csrf-token"] !== this.auth.csrf)
      return studyError(403, "csrf_failed");
    if (this.auth.user.role !== "student") return studyError(403, "forbidden");
    return null;
  }

  private lessonNotFound = () =>
    studyError(404, "not_found", "Lesson not found.");

  private defaultReply(
    c: { step: Step; courseId: string | null; lessonId: string | null },
    body: unknown,
  ): Reply {
    if (c.step === "courses") {
      const courses = [...this.courses]
        .sort((a, b) =>
          a.title.toLowerCase().localeCompare(b.title.toLowerCase()),
        )
        .map((course) => ({
          id: course.id,
          title: course.title,
          ...this.counts(course.id),
        }));
      return {
        json: {
          courses,
          totals: {
            lesson_count: courses.reduce((n, x) => n + x.lesson_count, 0),
            completed_count: courses.reduce((n, x) => n + x.completed_count, 0),
          },
        },
      };
    }
    if (c.step === "lessons") {
      if (!UUID.test(c.courseId ?? ""))
        return studyError(422, "validation_error");
      const course = this.courses.find((x) => x.id === c.courseId);
      if (!course) return studyError(404, "not_found", "Course not found.");
      const groups = new Map<
        string | null,
        { id: string | null; name: string; lessons: unknown[] }
      >();
      const ordered = [...this.visible(course.id)].sort((a, b) =>
        a.published_at.localeCompare(b.published_at),
      );
      for (const l of ordered) {
        const key = l.topic.id;
        if (!groups.has(key))
          groups.set(key, { id: key, name: l.topic.name, lessons: [] });
        groups.get(key)!.lessons.push({
          id: l.id,
          title: l.title,
          excerpt: l.content.replace(/\s+/g, " ").trim().slice(0, 160),
          completed: this.done.has(l.id),
        });
      }
      const topics = [...groups.values()].sort((a, b) => {
        if (a.id === null) return 1;
        if (b.id === null) return -1;
        return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
      });
      return {
        json: { course: { id: course.id, title: course.title }, topics },
      };
    }
    if (!UUID.test(c.lessonId ?? ""))
      return studyError(422, "validation_error");
    const lesson = this.lessons.find(
      (l) => l.id === c.lessonId && !this.withdrawn.has(l.id),
    );
    if (!lesson) return this.lessonNotFound();
    const course = this.courses.find((x) => x.id === lesson.course_id)!;
    if (c.step === "lesson") {
      return {
        json: {
          id: lesson.id,
          course: { id: course.id, title: course.title },
          topic: lesson.topic,
          title: lesson.title,
          content: lesson.content,
          published_at: lesson.published_at,
          completed: this.done.has(lesson.id),
          completed_at: this.done.get(lesson.id) ?? null,
        },
      };
    }
    const b = body as { completed?: unknown } | null;
    if (
      !b ||
      typeof b !== "object" ||
      typeof b.completed !== "boolean" ||
      Object.keys(b).length !== 1
    )
      return studyError(422, "validation_error", "Provide a valid request.", {
        fields: ["completed"],
      });
    if (b.completed) {
      if (!this.done.has(lesson.id))
        this.done.set(lesson.id, new Date().toISOString());
    } else this.done.delete(lesson.id);
    return {
      json: {
        lesson_id: lesson.id,
        completed: b.completed,
        completed_at: this.done.get(lesson.id) ?? null,
        course: { id: course.id, ...this.counts(course.id) },
      },
    };
  }
}

function studyReply(reply: Reply) {
  return {
    status: reply.status ?? 200,
    headers: { "cache-control": "no-store" },
    ...(reply.body !== undefined
      ? { body: reply.body, contentType: "application/json" }
      : { json: reply.json }),
  };
}

/** Register the study mock on a page. Call before `page.goto`. */
export async function mockLessonsApi(
  page: Page,
  options: LessonsOptions = {},
): Promise<LessonsApiMock> {
  const mock = new LessonsApiMock(options);
  await page.route(
    (url) => url.pathname.startsWith("/api/study/"),
    (route) => mock.handle(route),
  );
  return mock;
}

/** A signed-in student (or another user) with the study mock behind the same session. */
export async function signedInStudy(
  page: Page,
  options: Omit<LessonsOptions, "auth"> & { user?: User | null } = {},
) {
  const { user = STUDENT, ...rest } = options;
  const auth = await mockAuthApi(page, { user });
  const api = await mockLessonsApi(page, { ...rest, auth });
  return { auth, api };
}

/** A small valid lesson of a given shape, for XSS and edge-case tests. */
export function customLesson(
  overrides: Partial<FixtureLesson> & { id: string },
): FixtureLesson {
  return {
    course_id: COURSE_SE,
    topic: { id: null, name: "General" },
    title: "Custom lesson",
    content: "Custom content",
    published_at: "2026-01-10T09:00:00Z",
    ...overrides,
  };
}

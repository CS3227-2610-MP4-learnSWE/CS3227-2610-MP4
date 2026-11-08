import type { Page, Route } from "@playwright/test";
import { TEACHER, mockAuthApi, type AuthApiMock, type User } from "./authApi";

/**
 * Mock of GET /api/teacher/overview (contract: workflow/specs/TEA-05/plan.md).
 * Records every request, scripts replies per request, and never touches a backend.
 */

export const PATH = "/teacher/overview";
export const API = "/api/teacher/overview";

export const MSG = {
  expired: "Your session has expired. Sign in again.",
  forbidden: "You do not have access to the learning overview.",
  invalid: "Choose Last 7 days, Last 30 days or All time.",
  limited: "Too many overview requests. Try again shortly.",
  unavailable: "The learning overview is temporarily unavailable. Try again.",
  network: "Could not reach the server. Check your connection and retry.",
  timeout: "The learning overview request timed out. Try again.",
  malformed: "The server returned an invalid learning overview. Try again.",
  anonymous: "Sign in to view your learning overview.",
  noCourses:
    "You do not manage any courses yet. Ask an administrator to assign you to a course.",
  noLessons: "No lessons are published in this course yet.",
  noCompletions: "No lessons were completed in this period.",
  noSets: "No practice sets are published in this course yet.",
  noAttempts: "No practice attempts were submitted in this period.",
  noMissedNoAttempts:
    "No missed questions to show because no practice attempts were submitted in this period.",
  noMissed: "No questions were missed in this period.",
  noStudents: "No students are enrolled in this course yet.",
  intro:
    "Lesson completion, practice results and commonly missed questions for the courses you manage. Totals only: no student names or individual scores.",
};

export const NOTE_BULLETS = [
  "Students are the people enrolled in the course with a student account. Disabled students still count; a student removed from the course no longer appears in any figure.",
  "A lesson counts as completed when the student has it marked complete and the completion time falls inside the period. Lessons marked complete and later unmarked do not count. Only published lessons are included.",
  "Completion rate for a lesson = students who completed it ÷ students enrolled. Lesson completion rate for a course = completions in the period ÷ (students enrolled × published lessons). Percentages are rounded down; Not available means there is nothing to divide by.",
  "Practice results include submitted attempts on the course's published practice sets that were submitted inside the period. Average score uses each student's latest submitted attempt: all correct answers ÷ all answers.",
  "A question is missed when a student's latest attempt answered it incorrectly. Miss rate = missed ÷ answered, rounded down. The five questions with the highest miss rate are listed, ties broken by more misses, then set title, then question number.",
  "Periods use UTC calendar days and include today. All time has no start date. Figures show current enrolment and current records only. Totals are shown, never individual students.",
];

export interface LessonRow {
  lesson_id: string;
  title: string;
  topic: string;
  completed_students: number;
  rate_percent: number | null;
}
export interface SetRow {
  set_id: string;
  title: string;
  topic: string;
  students_attempted: number;
  submitted_attempts: number;
  average_score_percent: number | null;
}
export interface MissedRow {
  set_id: string;
  set_title: string;
  position: number;
  question: string;
  missed: number;
  answered: number;
  miss_rate_percent: number;
}
export interface CourseRow {
  course_id: string;
  title: string;
  student_count: number;
  lesson_count: number;
  completion_rate_percent: number | null;
  lessons: LessonRow[];
  practice: { sets: SetRow[]; missed_questions: MissedRow[] };
}
export interface OverviewBody {
  period: {
    preset: string;
    start: string | null;
    end: string;
    start_date: string | null;
    end_date: string;
    timezone: string;
  };
  as_of: string;
  courses: CourseRow[];
}

export const AS_OF = "2026-11-09T12:00:00Z";
export const COURSE_A = "c0000000-0000-4000-8000-00000000000a";
export const COURSE_B = "c0000000-0000-4000-8000-00000000000b";

export function periodFor(preset: string): OverviewBody["period"] {
  const start =
    preset === "7d" ? "2026-11-03" : preset === "30d" ? "2026-10-11" : null;
  return {
    preset,
    start: start ? `${start}T00:00:00Z` : null,
    end: "2026-11-10T00:00:00Z",
    start_date: start,
    end_date: "2026-11-09",
    timezone: "UTC",
  };
}

export function periodLine(preset: string): string {
  const range =
    preset === "7d"
      ? "Last 7 days, 2026-11-03 to 2026-11-09"
      : preset === "30d"
        ? "Last 30 days, 2026-10-11 to 2026-11-09"
        : "All time, up to 2026-11-09";
  return `Period: ${range} (UTC)`;
}

export function dataCourse(): CourseRow {
  return {
    course_id: COURSE_A,
    title: "Intro to SE",
    student_count: 5,
    lesson_count: 2,
    completion_rate_percent: 40,
    lessons: [
      {
        lesson_id: "d0000000-0000-4000-8000-000000000001",
        title: "Clean code",
        topic: "General",
        completed_students: 3,
        rate_percent: 60,
      },
      {
        lesson_id: "d0000000-0000-4000-8000-000000000002",
        title: "Version control",
        topic: "Git",
        completed_students: 1,
        rate_percent: 20,
      },
    ],
    practice: {
      sets: [
        {
          set_id: "e0000000-0000-4000-8000-000000000001",
          title: "Testing basics",
          topic: "Testing",
          students_attempted: 4,
          submitted_attempts: 6,
          average_score_percent: 58,
        },
      ],
      missed_questions: [
        {
          set_id: "e0000000-0000-4000-8000-000000000001",
          set_title: "Testing basics",
          position: 2,
          question: "What does a unit test check?",
          missed: 3,
          answered: 4,
          miss_rate_percent: 75,
        },
        {
          set_id: "e0000000-0000-4000-8000-000000000001",
          set_title: "Testing basics",
          position: 3,
          question: "Which status means not found?",
          missed: 1,
          answered: 4,
          miss_rate_percent: 25,
        },
      ],
    },
  };
}

export function quietCourse(title = "Second course"): CourseRow {
  return {
    course_id: COURSE_B,
    title,
    student_count: 3,
    lesson_count: 1,
    completion_rate_percent: 0,
    lessons: [
      {
        lesson_id: "d0000000-0000-4000-8000-000000000003",
        title: "Quiet lesson",
        topic: "General",
        completed_students: 0,
        rate_percent: 0,
      },
    ],
    practice: {
      sets: [
        {
          set_id: "e0000000-0000-4000-8000-000000000002",
          title: "Quiet set",
          topic: "General",
          students_attempted: 0,
          submitted_attempts: 0,
          average_score_percent: null,
        },
      ],
      missed_questions: [],
    },
  };
}

export function emptyCourse(title = "Empty course"): CourseRow {
  return {
    course_id: COURSE_B,
    title,
    student_count: 0,
    lesson_count: 0,
    completion_rate_percent: null,
    lessons: [],
    practice: { sets: [], missed_questions: [] },
  };
}

export function overviewBody(
  preset: string,
  courses: CourseRow[] = [dataCourse()],
): OverviewBody {
  return {
    period: periodFor(preset),
    as_of: AS_OF,
    courses: structuredClone(courses),
  };
}

export type Step = {
  status?: number;
  code?: string;
  abort?: boolean;
  hold?: boolean;
  malformed?: boolean;
  json?: unknown;
  courses?: CourseRow[];
  /** Marks the pending response for this request, used by stale-response tests. */
  mark?: (body: OverviewBody) => void;
};

export interface Tea05Context {
  auth: AuthApiMock;
  requests: URL[];
  completed: URL[];
  steps: Step[];
  release: () => void;
  /** Number of requests that are held and not yet released. */
  held: () => number;
}

/**
 * Sign in a user (teacher by default) with the auth mock and register the overview route. The
 * route is registered after mockAuthApi, so it wins over the neutral empty route there.
 */
export async function setup(
  page: Page,
  first?: Step,
  user: User | null = TEACHER,
  defaultCourses: CourseRow[] = [dataCourse()],
): Promise<Tea05Context> {
  const auth = await mockAuthApi(page, { user });
  const requests: URL[] = [];
  const completed: URL[] = [];
  const steps: Step[] = first ? [first] : [];
  const releases: (() => void)[] = [];
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.route(
    (url) => url.pathname === API,
    async (route: Route) => {
      const url = new URL(route.request().url());
      requests.push(url);
      const step = steps.shift() ?? {};
      if (step.hold)
        await new Promise<void>((resolve) => releases.push(resolve));
      if (step.abort) {
        await route.abort("connectionrefused").catch(() => undefined);
        return;
      }
      if (step.malformed) {
        await route
          .fulfill({ contentType: "application/json", body: "not-json" })
          .catch(() => undefined);
        return;
      }
      const preset = url.searchParams.get("period") ?? "30d";
      const body = overviewBody(preset, step.courses ?? defaultCourses);
      step.mark?.(body);
      await route
        .fulfill({
          status: step.status ?? 200,
          json:
            step.json ??
            (step.status
              ? {
                  detail: {
                    code: step.code,
                    message: "ignored private server error",
                  },
                }
              : body),
          headers: { "cache-control": "private, no-store", vary: "Cookie" },
        })
        .catch(() => undefined);
      completed.push(url);
    },
  );
  return {
    auth,
    requests,
    completed,
    steps,
    release: () => releases.splice(0).forEach((resolve) => resolve()),
    held: () => releases.length,
  };
}

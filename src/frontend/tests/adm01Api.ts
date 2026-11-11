import { type Page, type Route } from "@playwright/test";
import { ADMIN, mockAuthApi, type AuthApiMock, type User } from "./authApi";

/**
 * Stateful mock of the ADM-01 analytics API (contract: workflow/specs/ADM-01/plan.md "API endpoints").
 * No backend is used. Every analytics request is recorded; replies are scriptable per endpoint kind.
 * Follows the structure of adm03Api.ts / adm06-usage.spec.ts (auth mock first, catch-all admin route,
 * then the feature routes).
 */

// ADM-07 P2-5: the ADM-01 page moved unchanged to this path (no nav link); the hub owns /admin/analytics.
export const PATH = "/admin/feature-analytics-legacy";
export const API = "/api/admin/analytics";

export type Kind = "usage" | "generation" | "quality" | "start" | "run";
export type Workflow = "student_exercise" | "teacher_lesson_planning";

export interface Step {
  status?: number;
  code?: string;
  /** Server message; the page must ignore it except for 422 on the grading start. */
  message?: string;
  abort?: boolean;
  hold?: boolean;
  malformed?: boolean;
  json?: unknown;
}

export interface Recorded {
  kind: Kind;
  url: URL;
  method: string;
  body: unknown;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Json = any;

const DAY = 86_400_000;

export function isoDay(offsetDays = 0): string {
  return new Date(Date.now() - offsetDays * DAY).toISOString().slice(0, 10);
}

/** The page's default period: the last 30 days ending today (UTC). */
export function defaultPeriod() {
  return { from: isoDay(29), to: isoDay(0) };
}

export const DIM_NAMES = [
  "relevance",
  "factual_accuracy",
  "clarity",
  "safety",
] as const;

const unavailable = (reason: string) => ({ state: "unavailable", reason });

export function usageBody(url: URL): Json {
  return {
    period_start: url.searchParams.get("period_start"),
    period_end: url.searchParams.get("period_end"),
    recording_started_on: "2020-01-01",
    chatbot: {
      student: {
        state: "available",
        reason: null,
        successful: 12,
        unsuccessful: 3,
        rows: [
          {
            user_id: "u-3f9a1c2b",
            name: "Alice Tan",
            successful: 5,
            unsuccessful: 1,
          },
          {
            user_id: "u-77aa01de",
            name: "Bob Lim",
            successful: 7,
            unsuccessful: 2,
          },
        ],
        rows_truncated: false,
      },
      teacher: {
        ...unavailable("no_source"),
        successful: null,
        unsuccessful: null,
        rows: [],
        rows_truncated: false,
      },
      total: {
        ...unavailable("no_source"),
        successful: null,
        unsuccessful: null,
      },
    },
    practice_completion: {
      state: "available",
      reason: null,
      started: 3,
      submitted: 2,
      percentage: 66.7,
    },
  };
}

export function generationBody(url: URL): Json {
  return {
    period_start: url.searchParams.get("period_start"),
    period_end: url.searchParams.get("period_end"),
    recording_started_on: "2020-01-01",
    workflows: [
      {
        workflow: "study_notes",
        label: "Study notes",
        state: "available",
        reason: null,
        attempts: 9,
        successful: 6,
        unsuccessful: 3,
        rate_percent: 66.7,
      },
      {
        workflow: "mcq_batch",
        label: "MCQ batches",
        state: "not_applicable",
        reason: "no_generation_attempts",
        attempts: 0,
        successful: 0,
        unsuccessful: 0,
        rate_percent: null,
      },
    ],
  };
}

const GRADES = (n: number) =>
  DIM_NAMES.map((dimension, i) => ({
    dimension,
    state:
      dimension === "factual_accuracy" && n % 2 === 0
        ? "unassessable"
        : "graded",
    score:
      dimension === "factual_accuracy" && n % 2 === 0
        ? null
        : 3 + ((n + i) % 3),
    reason:
      dimension === "factual_accuracy" && n % 2 === 0
        ? "No authorised context was available."
        : `Reason ${dimension} ${n}.`,
  }));

export function itemRows(offset: number, limit: number, total: number): Json[] {
  const rows: Json[] = [];
  for (let i = offset; i < Math.min(offset + limit, total); i++) {
    const graded = i === 0;
    rows.push({
      item_id: 1000 + i,
      received_at: "2026-11-08T09:12:44Z",
      status: graded ? "graded" : "pending",
      response_time_ms: 2312,
      failure_code: null,
      graded_at: graded ? "2026-11-09T05:01:10Z" : null,
      grades: graded ? GRADES(1) : [],
    });
  }
  return rows;
}

export function qualityBody(url: URL, total = 2): Json {
  const workflow = (url.searchParams.get("workflow") ??
    "student_exercise") as Workflow;
  const limit = Number(url.searchParams.get("limit") ?? 25);
  const offset = Number(url.searchParams.get("offset") ?? 0);
  const teacher = workflow === "teacher_lesson_planning";
  return {
    workflow,
    period_start: url.searchParams.get("period_start"),
    period_end: url.searchParams.get("period_end"),
    recording_started_on: "2020-01-01",
    grades: {
      state: "available",
      reason: null,
      assessed_count: 12,
      pending_count: 5,
      grading_failed_count: 1,
      content_expired_count: 0,
      privacy_blocked_count: 0,
      privacy_mode: "local_dlp",
      dimensions: [
        {
          dimension: "relevance",
          average: 4.25,
          graded_count: 12,
          unassessable_count: 0,
        },
        {
          dimension: "factual_accuracy",
          average: 3.5,
          graded_count: 6,
          unassessable_count: 6,
        },
        {
          dimension: "clarity",
          average: 4.0,
          graded_count: 12,
          unassessable_count: 0,
        },
        {
          dimension: "safety",
          average: 5.0,
          graded_count: 12,
          unassessable_count: 0,
        },
      ],
    },
    response_time: {
      state: "available",
      reason: null,
      successful_count: 40,
      mean_ms: 2400,
      median_ms: 2100,
      failed_or_incomplete_count: 3,
    },
    sessions: teacher
      ? {
          ...unavailable("no_source"),
          session_count: null,
          average_messages_per_session: null,
          user_messages: null,
          ai_messages: null,
        }
      : {
          state: "available",
          reason: null,
          session_count: 9,
          average_messages_per_session: 6.5,
          user_messages: 30,
          ai_messages: 28,
        },
    activity_time: teacher
      ? {
          ...unavailable("no_source"),
          linked_session_count: null,
          distinct_activity_count: null,
          excluded_session_count: null,
          average_messages_per_session: null,
          average_activity_seconds: null,
          start_event: null,
          end_event: null,
        }
      : {
          state: "available",
          reason: null,
          linked_session_count: 7,
          distinct_activity_count: 6,
          excluded_session_count: 2,
          average_messages_per_session: 7.14,
          average_activity_seconds: 912.5,
          start_event: "Practice attempt started",
          end_event: "Practice attempt submitted",
        },
    items: { total, limit, offset, rows: itemRows(offset, limit, total) },
    active_run: null,
  };
}

export interface Run {
  run_id: number;
  workflow: Workflow;
  period_start: string;
  period_end: string;
  status: "queued" | "running" | "completed" | "failed";
  items_total: number;
  items_graded: number;
  items_failed: number;
  failure_code: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export function run(over: Partial<Run> = {}): Run {
  return {
    run_id: 12,
    workflow: "student_exercise",
    period_start: "2026-10-11",
    period_end: "2026-11-09",
    status: "queued",
    items_total: 3,
    items_graded: 0,
    items_failed: 0,
    failure_code: null,
    created_at: "2026-11-09T05:00:00Z",
    started_at: null,
    finished_at: null,
    ...over,
  };
}

export class AnalyticsMock {
  readonly requests: Recorded[] = [];
  readonly completed: Recorded[] = [];
  readonly steps: Record<Kind, Step[]> = {
    usage: [],
    generation: [],
    quality: [],
    start: [],
    run: [],
  };
  /** Persistent edits applied to every default reply of a kind. */
  tweak: {
    usage?: (body: Json, url: URL) => void;
    generation?: (body: Json, url: URL) => void;
    quality?: (body: Json, url: URL) => void;
  } = {};
  /** Total number of assessed-response rows the default quality reply claims. */
  total = 2;
  /** Successive GET /grading-runs/{id} bodies; the last one repeats. */
  runStates: Partial<Run>[] = [];
  /** The default 202 body of POST /grading-runs. */
  startRun: Partial<Run> = {};
  private readonly waiting: (() => void)[] = [];

  constructor(readonly auth: AuthApiMock) {}

  of(kind: Kind) {
    return this.requests.filter((r) => r.kind === kind);
  }
  count(kind?: Kind) {
    return kind ? this.of(kind).length : this.requests.length;
  }
  /** Queue a scripted reply for the next request of `kind`. */
  next(kind: Kind, ...steps: Step[]) {
    this.steps[kind].push(...steps);
  }
  release() {
    this.waiting.splice(0).forEach((resolve) => resolve());
  }
  clear() {
    this.requests.length = 0;
    this.completed.length = 0;
  }

  private classify(method: string, path: string): Kind | null {
    if (method === "GET" && path === `${API}/usage`) return "usage";
    if (method === "GET" && path === `${API}/generation`) return "generation";
    if (method === "GET" && path === `${API}/quality`) return "quality";
    if (method === "POST" && path === `${API}/grading-runs`) return "start";
    if (method === "GET" && path.startsWith(`${API}/grading-runs/`))
      return "run";
    return null;
  }

  private defaultBody(kind: Kind, url: URL): Json {
    if (kind === "usage") {
      const body = usageBody(url);
      this.tweak.usage?.(body, url);
      return body;
    }
    if (kind === "generation") {
      const body = generationBody(url);
      this.tweak.generation?.(body, url);
      return body;
    }
    if (kind === "quality") {
      const body = qualityBody(url, this.total);
      this.tweak.quality?.(body, url);
      return body;
    }
    if (kind === "start") return run(this.startRun);
    const state =
      this.runStates.length > 1
        ? this.runStates.shift()!
        : (this.runStates[0] ?? {});
    return run({
      status: "running",
      items_graded: 1,
      started_at: "2026-11-09T05:00:01Z",
      ...state,
    });
  }

  async handle(route: Route) {
    const request = route.request();
    const url = new URL(request.url());
    const kind = this.classify(request.method(), url.pathname);
    if (!kind) {
      await route.fulfill({
        status: 404,
        json: { detail: { code: "not_found", message: "no route" } },
      });
      return;
    }
    let body: unknown = null;
    try {
      body = request.postDataJSON();
    } catch {
      body = request.postData();
    }
    const recorded: Recorded = { kind, url, method: request.method(), body };
    this.requests.push(recorded);
    const step = this.steps[kind].shift() ?? {};
    if (step.hold)
      await new Promise<void>((resolve) => this.waiting.push(resolve));
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
    const failing = step.status && step.status >= 400;
    await route
      .fulfill({
        status: step.status ?? (kind === "start" ? 202 : 200),
        json:
          step.json ??
          (failing
            ? {
                detail: {
                  code: step.code ?? "error",
                  message: step.message ?? "ignored private server error",
                },
              }
            : this.defaultBody(kind, url)),
        headers: { "cache-control": "no-store" },
      })
      .catch(() => undefined);
    this.completed.push(recorded);
  }
}

/** Register auth, a neutral catch-all for other admin calls, and the analytics routes. Call before page.goto. */
export async function setup(
  page: Page,
  options: { user?: User | null } = {},
): Promise<AnalyticsMock> {
  const auth = await mockAuthApi(page, {
    user: options.user === undefined ? ADMIN : options.user,
  });
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  // All unrelated admin calls stay isolated from any developer backend.
  await page.route("**/api/admin/**", (route) =>
    route.fulfill({ json: { accounts: [], courses: [] } }),
  );
  const mock = new AnalyticsMock(auth);
  await page.route(
    (url) => url.pathname.startsWith(API),
    (route) => mock.handle(route),
  );
  return mock;
}

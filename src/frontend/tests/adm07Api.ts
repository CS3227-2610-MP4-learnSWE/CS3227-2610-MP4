import { type Page, type Route } from "@playwright/test";
import { ADMIN, mockAuthApi, type AuthApiMock, type User } from "./authApi";
import { generationBody, qualityBody, run, type Run } from "./adm01Api";

/**
 * Stateful mock of the ADM-07 hub API (contract: workflow/specs/ADM-07/plan.md, phase 2).
 * No backend is used. Every request is recorded; replies are scriptable per kind. Metrics without a
 * source in phase 2 (rate-limited, logins, drafts started, published, categories) are the specified
 * unavailable state, never zero.
 */

export const HUB = "/admin/analytics";
export const API = "/api/admin/analytics";
export const AI_USAGE = "/api/admin/ai-usage";

export type Kind =
  | "health"
  | "hourly"
  | "daily"
  | "users"
  | "generation"
  | "quality"
  | "aiusage"
  | "start"
  | "run";

export interface Step {
  status?: number;
  abort?: boolean;
  hold?: boolean;
  malformed?: boolean;
  json?: unknown;
}

export interface Recorded {
  kind: Kind;
  url: URL;
  method: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Json = any;

const DAY = 86_400_000;

export function isoDay(offsetDays = 0): string {
  return new Date(Date.now() - offsetDays * DAY).toISOString().slice(0, 10);
}

/** Dates from period_start to period_end inclusive (UTC). */
function datesOf(url: URL): string[] {
  const start = Date.parse(`${url.searchParams.get("period_start")}T00:00:00Z`);
  const end = Date.parse(`${url.searchParams.get("period_end")}T00:00:00Z`);
  const out: string[] = [];
  for (let t = start; t <= end; t += DAY)
    out.push(new Date(t).toISOString().slice(0, 10));
  return out;
}

const unavailable = (reason: string) => ({ state: "unavailable", reason });
const CATS = {
  timeout: 0,
  rate_limited: 0,
  invalid_output: 0,
  upstream: 0,
  unclassified: 0,
};

export function healthBody(url: URL): Json {
  return {
    period_start: url.searchParams.get("period_start"),
    period_end: url.searchParams.get("period_end"),
    recording_started_on: "2020-01-01",
    data_starts_on: null,
    as_of: "2026-11-11T09:30:00Z",
    low_sample_threshold: 20,
    chatbot_failure: {
      state: "available",
      reason: null,
      total: 120,
      failed: 9,
      in_progress: 0,
      rate_percent: 7.5,
      severity: "critical",
    },
    generation_failure: {
      state: "available",
      reason: null,
      total: 30,
      failed: 1,
      in_progress: 0,
      includes_rate_limited: false,
      rate_percent: 3.3,
      severity: "warning",
    },
    rate_limited: {
      ...unavailable("not_collected"),
      since: null,
      count: null,
      total_requests: null,
    },
    chatbot_response_time: {
      state: "available",
      reason: null,
      all: { count: 120, median_ms: 2100, p95_ms: 5400 },
      successful: { count: 111, median_ms: 2000, p95_ms: 4100 },
      failed: { count: 9, median_ms: 120000, p95_ms: 120000 },
    },
    generation_response_time: {
      state: "available",
      reason: null,
      all: { count: 30, median_ms: 14200, p95_ms: 31800 },
      successful: { count: 29, median_ms: 14000, p95_ms: 30000 },
      failed: { count: 1, median_ms: 31800, p95_ms: 31800 },
    },
    practice_completion: {
      state: "available",
      reason: null,
      started: 10,
      submitted: 7,
      percentage: 70.0,
    },
  };
}

/** One bucket per UTC hour; the first day has 4 requests at 16:00Z (1 failed) and 2 at 17:00Z. */
export function hourlyBody(url: URL): Json {
  const days = datesOf(url);
  const buckets: Json[] = [];
  days.forEach((d, di) => {
    for (let h = 0; h < 24; h++) {
      const special = di === 0 && (h === 16 || h === 17);
      const successful = special ? (h === 16 ? 3 : 2) : 0;
      const failed = special && h === 16 ? 1 : 0;
      const total = successful + failed;
      buckets.push({
        hour_start: `${d}T${String(h).padStart(2, "0")}:00:00Z`,
        successful,
        failed,
        total,
        failure_rate_percent: total
          ? Math.round((failed * 1000) / total) / 10
          : null,
        failed_by_category: { ...CATS, unclassified: failed },
      });
    }
  });
  const sum = (k: string) => buckets.reduce((a, b) => a + b[k], 0);
  return {
    period_start: url.searchParams.get("period_start"),
    period_end: url.searchParams.get("period_end"),
    recording_started_on: "2020-01-01",
    data_starts_on: null,
    as_of: "2026-11-11T09:30:00Z",
    in_progress: 0,
    state: "available",
    reason: null,
    retention_days: 30,
    category_breakdown: unavailable("not_collected"),
    totals: {
      successful: sum("successful"),
      failed: sum("failed"),
      total: sum("total"),
    },
    buckets,
  };
}

export function dailyBody(url: URL): Json {
  const days = datesOf(url);
  return {
    period_start: url.searchParams.get("period_start"),
    period_end: url.searchParams.get("period_end"),
    recording_started_on: "2020-01-01",
    logins: {
      ...unavailable("not_collected"),
      since: null,
      per_day: [],
      total_logins: null,
      data_starts_on: null,
    },
    practice_drafts_started: {
      ...unavailable("not_collected"),
      since: null,
      per_day: [],
      total: null,
      data_starts_on: null,
    },
    practice_published: {
      ...unavailable("not_collected"),
      since: null,
      per_day: [],
      total: null,
      data_starts_on: null,
    },
    attempts_funnel: {
      state: "available",
      reason: null,
      data_starts_on: null,
      started_total: 10,
      submitted_by_period_end: 7,
      per_day: days.map((date, i) => ({
        date,
        started: i === 0 ? 3 : 0,
        submitted: i === 0 ? 2 : 0,
      })),
    },
    attempts_per_student: {
      state: "available",
      reason: null,
      data_starts_on: null,
      per_day: days.map((date, i) => ({
        date,
        active_students: i === 0 ? 2 : 0,
        median_attempts: i === 0 ? 1.5 : null,
        distribution:
          i === 0
            ? { "1": 1, "2": 1, "3": 0, "4": 0, "5_plus": 0 }
            : { "1": 0, "2": 0, "3": 0, "4": 0, "5_plus": 0 },
      })),
    },
  };
}

export function usersBody(url: URL, total = 23): Json {
  const role = url.searchParams.get("role") ?? "student";
  const limit = Number(url.searchParams.get("limit") ?? 10);
  const offset = Number(url.searchParams.get("offset") ?? 0);
  const base = {
    period_start: url.searchParams.get("period_start"),
    period_end: url.searchParams.get("period_end"),
    recording_started_on: "2020-01-01",
    data_starts_on: null,
    as_of: "2026-11-11T09:30:00Z",
    in_progress: 0,
    role,
    sort: url.searchParams.get("sort") ?? "unsuccessful",
    order: url.searchParams.get("order") ?? "desc",
    limit,
    offset,
    all_users_total: {
      ...unavailable("no_source"),
      successful: null,
      unsuccessful: null,
    },
  };
  if (role === "teacher")
    return {
      ...base,
      ...unavailable("no_source"),
      totals: { successful: null, unsuccessful: null },
      total_users: null,
      rows: [],
    };
  const rows: Json[] = [];
  for (let i = offset; i < Math.min(offset + limit, total); i++)
    rows.push({
      user_id: `u-${String(i).padStart(8, "0")}`,
      name: i === 0 ? "Alice Tan" : i === 1 ? "Bob Lim" : `Student ${i}`,
      successful: 5,
      unsuccessful: 4,
      failure_rate_percent: 44.4,
    });
  return {
    ...base,
    state: "available",
    reason: null,
    totals: { successful: 120, unsuccessful: 9 },
    total_users: total,
    rows,
  };
}

export function aiUsageBody(url: URL): Json {
  const feature = url.searchParams.get("feature") ?? "all";
  const m = (value: number | null, reason: string | null = null) => ({
    value,
    reason,
  });
  const row = (f: string) => ({
    feature: f,
    coverage_start: "2020-01-01T00:00:00Z",
    requests: m(731),
    failures: m(3),
    rate_limit_failures: m(1),
    other_failures: m(2),
    input_tokens: m(12),
    output_tokens: m(7),
    total_tokens: m(99),
  });
  const all = ["STU-03", "TEA-02", "ADM-03", "ADM-01"];
  return {
    feature,
    start_date: url.searchParams.get("start_date"),
    end_date: url.searchParams.get("end_date"),
    timezone: "UTC",
    as_of: new Date().toISOString(),
    rows: (feature === "all" ? all : [feature]).map(row),
  };
}

export class HubMock {
  readonly requests: Recorded[] = [];
  readonly steps: Record<Kind, Step[]> = {
    health: [],
    hourly: [],
    daily: [],
    users: [],
    generation: [],
    quality: [],
    aiusage: [],
    start: [],
    run: [],
  };
  tweak: Partial<Record<Kind, (body: Json, url: URL) => void>> = {};
  runStates: Partial<Run>[] = [];
  usersTotal = 23;
  private readonly waiting: (() => void)[] = [];

  constructor(readonly auth: AuthApiMock) {}

  of(kind: Kind) {
    return this.requests.filter((r) => r.kind === kind);
  }
  count(kind?: Kind) {
    return kind ? this.of(kind).length : this.requests.length;
  }
  /** Analytics GET requests only (excludes grading start/poll). */
  loads() {
    return this.requests.filter((r) => r.kind !== "start" && r.kind !== "run")
      .length;
  }
  next(kind: Kind, ...steps: Step[]) {
    this.steps[kind].push(...steps);
  }
  release() {
    this.waiting.splice(0).forEach((resolve) => resolve());
  }
  clear() {
    this.requests.length = 0;
  }

  private classify(method: string, path: string): Kind | null {
    if (path === AI_USAGE && method === "GET") return "aiusage";
    const map: Record<string, Kind> = {
      [`${API}/health`]: "health",
      [`${API}/hourly`]: "hourly",
      [`${API}/daily`]: "daily",
      [`${API}/chatbot-users`]: "users",
      [`${API}/generation`]: "generation",
      [`${API}/quality`]: "quality",
    };
    if (method === "GET" && map[path]) return map[path];
    if (method === "POST" && path === `${API}/grading-runs`) return "start";
    if (method === "GET" && path.startsWith(`${API}/grading-runs/`))
      return "run";
    return null;
  }

  private defaultBody(kind: Kind, url: URL): Json {
    let body: Json;
    switch (kind) {
      case "health":
        body = healthBody(url);
        break;
      case "hourly":
        body = hourlyBody(url);
        break;
      case "daily":
        body = dailyBody(url);
        break;
      case "users":
        body = usersBody(url, this.usersTotal);
        break;
      case "generation":
        body = generationBody(url);
        for (const w of body.workflows) {
          w.requests = w.attempts;
          w.rate_limited = null;
          w.rate_limited_state = unavailable("not_collected");
        }
        body.data_starts_on = null;
        break;
      case "quality":
        body = qualityBody(url);
        body.data_starts_on = null;
        break;
      case "aiusage":
        body = aiUsageBody(url);
        break;
      case "start":
        return run({});
      default: {
        const state =
          this.runStates.length > 1
            ? this.runStates.shift()!
            : (this.runStates[0] ?? {});
        return run({ status: "running", items_graded: 1, ...state });
      }
    }
    this.tweak[kind]?.(body, url);
    return body;
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
    this.requests.push({ kind, url, method: request.method() });
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
                  code: "error",
                  message: "ignored private server error",
                },
              }
            : this.defaultBody(kind, url)),
        headers: { "cache-control": "no-store" },
      })
      .catch(() => undefined);
  }
}

/** Register auth, a neutral catch-all for other admin calls, and the hub routes. Call before page.goto. */
export async function setup(
  page: Page,
  options: { user?: User | null } = {},
): Promise<HubMock> {
  const auth = await mockAuthApi(page, {
    user: options.user === undefined ? ADMIN : options.user,
  });
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.route("**/api/admin/**", (route) =>
    route.fulfill({ json: { accounts: [], courses: [] } }),
  );
  const mock = new HubMock(auth);
  await page.route(
    (url) => url.pathname.startsWith(API) || url.pathname === AI_USAGE,
    (route) => mock.handle(route),
  );
  return mock;
}

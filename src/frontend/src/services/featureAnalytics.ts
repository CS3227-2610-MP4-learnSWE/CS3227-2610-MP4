import { ApiError, request } from "./client";

export const TIMEOUT_MS = 15_000;
export const PAGE_SIZE = 25;

export type Workflow = "student_exercise" | "teacher_lesson_planning";
export const WORKFLOWS: { id: Workflow; label: string }[] = [
  { id: "student_exercise", label: "Student exercises" },
  { id: "teacher_lesson_planning", label: "Teacher lesson planning" },
];

export type State = "available" | "not_applicable" | "unavailable";
export type Reason =
  | "period_before_recording"
  | "no_source"
  | "read_failed"
  | "no_practice_attempts"
  | "no_generation_attempts"
  | "no_eligible_records"
  | "none_graded"
  | "not_collected"
  | "beyond_retention"
  | "no_chat_requests";
type Base = {
  state: State;
  reason: Reason | null;
  data_starts_on?: string | null;
};

export type UserRow = {
  user_id: string;
  name: string | null;
  successful: number;
  unsuccessful: number;
};
export type ChatGroup = Base & {
  successful: number | null;
  unsuccessful: number | null;
  rows: UserRow[];
  rows_truncated: boolean;
};
export type Usage = {
  period_start: string;
  period_end: string;
  recording_started_on: string;
  chatbot: {
    student: ChatGroup;
    teacher: ChatGroup;
    total: Base & { successful: number | null; unsuccessful: number | null };
  };
  practice_completion: Base & {
    started: number | null;
    submitted: number | null;
    percentage: number | null;
  };
};

export type GenerationRow = Base & {
  workflow: string;
  label: string;
  attempts: number | null;
  requests: number | null;
  rate_limited: number | null;
  rate_limited_state: { state: State; reason: Reason | null };
  successful: number | null;
  unsuccessful: number | null;
  rate_percent: number | null;
};
export type Generation = {
  recording_started_on: string;
  data_starts_on?: string | null;
  workflows: GenerationRow[];
};

export type Dimension = "relevance" | "factual_accuracy" | "clarity" | "safety";
export const DIMENSIONS: { id: Dimension; label: string }[] = [
  { id: "relevance", label: "Relevance" },
  { id: "factual_accuracy", label: "Factual accuracy" },
  { id: "clarity", label: "Clarity" },
  { id: "safety", label: "Safety" },
];
export type GradeEntry = {
  dimension: Dimension;
  state: "graded" | "unassessable";
  score: number | null;
  reason: string;
};
export type ItemStatus =
  | "pending"
  | "graded"
  | "grading_failed"
  | "content_expired"
  | "privacy_blocked";
export type QualityItem = {
  item_id: number;
  received_at: string;
  status: ItemStatus;
  response_time_ms: number | null;
  failure_code: string | null;
  graded_at: string | null;
  grades: GradeEntry[];
};
export type RunStatus = "queued" | "running" | "completed" | "failed";
export type Run = {
  run_id: number;
  workflow: string;
  period_start: string;
  period_end: string;
  status: RunStatus;
  items_total: number;
  items_graded: number;
  items_failed: number;
  failure_code: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};
export type Items = {
  total: number;
  limit: number;
  offset: number;
  rows: QualityItem[];
};
export type Quality = {
  workflow: Workflow;
  recording_started_on: string;
  data_starts_on?: string | null;
  grades: Base & {
    assessed_count: number | null;
    pending_count: number | null;
    grading_failed_count: number | null;
    content_expired_count: number | null;
    privacy_blocked_count: number | null;
    privacy_mode: "strict" | "local_dlp";
    dimensions: {
      dimension: Dimension;
      average: number | null;
      graded_count: number;
      unassessable_count: number;
    }[];
  };
  response_time: Base & {
    successful_count: number | null;
    mean_ms: number | null;
    median_ms: number | null;
    failed_or_incomplete_count: number | null;
  };
  sessions: Base & {
    session_count: number | null;
    average_messages_per_session: number | null;
    user_messages: number | null;
    ai_messages: number | null;
  };
  activity_time: Base & {
    linked_session_count: number | null;
    distinct_activity_count: number | null;
    excluded_session_count: number | null;
    average_messages_per_session: number | null;
    average_activity_seconds: number | null;
  };
  items: Items;
  active_run: Run | null;
};

export type Period = { from: string; to: string };

const DATE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;
export const DATE_MESSAGE = "Enter dates as YYYY-MM-DD.";
export const ORDER_MESSAGE =
  "The start date must be on or before the end date.";
export const LENGTH_MESSAGE = "The period can be at most 366 days.";

export function validDate(value: string): boolean {
  if (!DATE.test(value)) return false;
  const time = Date.parse(`${value}T00:00:00Z`);
  return (
    Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value
  );
}

export function isoDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export type PeriodErrors = { from?: string; to?: string };

/** The same three messages as the server, checked in the same order. */
export function checkPeriod(period: Period): PeriodErrors {
  const from = period.from.trim();
  const to = period.to.trim();
  const errors: PeriodErrors = {};
  if (!validDate(from)) errors.from = DATE_MESSAGE;
  if (!validDate(to)) errors.to = DATE_MESSAGE;
  if (errors.from || errors.to) return errors;
  if (from > to) return { from: ORDER_MESSAGE };
  const days =
    (Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) /
      86_400_000 +
    1;
  if (days > 366) return { to: LENGTH_MESSAGE };
  return {};
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function checked<T>(data: unknown, keys: string[]): T {
  if (!isObject(data) || !keys.every((key) => key in data))
    throw new ApiError(0, "bad_response");
  return data as T;
}

const read = (path: string, signal?: AbortSignal) =>
  request("GET", path, undefined, {
    timeoutMs: TIMEOUT_MS,
    distinguishTimeout: true,
    cache: "no-store",
    signal,
    anyUnauthorized: true,
  });

const query = (period: Period) =>
  `period_start=${encodeURIComponent(period.from)}&period_end=${encodeURIComponent(period.to)}`;

export async function readUsage(
  period: Period,
  signal?: AbortSignal,
): Promise<Usage> {
  return checked<Usage>(
    await read(`/api/admin/analytics/usage?${query(period)}`, signal),
    ["chatbot", "practice_completion"],
  );
}

export async function readGeneration(
  period: Period,
  signal?: AbortSignal,
): Promise<Generation> {
  const data = checked<Generation>(
    await read(`/api/admin/analytics/generation?${query(period)}`, signal),
    ["workflows"],
  );
  if (!Array.isArray(data.workflows)) throw new ApiError(0, "bad_response");
  return data;
}

export async function readQuality(
  period: Period,
  workflow: Workflow,
  offset = 0,
  signal?: AbortSignal,
): Promise<Quality> {
  const data = checked<Quality>(
    await read(
      `/api/admin/analytics/quality?workflow=${workflow}&${query(period)}&limit=${PAGE_SIZE}&offset=${offset}`,
      signal,
    ),
    ["grades", "response_time", "sessions", "activity_time", "items"],
  );
  if (!isObject(data.items) || !Array.isArray(data.items.rows))
    throw new ApiError(0, "bad_response");
  return data;
}

export async function startGradingRun(
  period: Period,
  workflow: Workflow,
  signal?: AbortSignal,
): Promise<Run> {
  const data = await request(
    "POST",
    "/api/admin/analytics/grading-runs",
    { workflow, period_start: period.from, period_end: period.to },
    {
      timeoutMs: TIMEOUT_MS,
      distinguishTimeout: true,
      signal,
      anyUnauthorized: true,
    },
  );
  return checked<Run>(data, ["run_id", "status"]);
}

export async function readRun(
  runId: number,
  signal?: AbortSignal,
): Promise<Run> {
  return checked<Run>(
    await read(`/api/admin/analytics/grading-runs/${runId}`, signal),
    ["run_id", "status"],
  );
}

export const isActive = (run: Run | null) =>
  run !== null && (run.status === "queued" || run.status === "running");

export const UNAVAILABLE_REASONS: Record<string, (recorded: string) => string> =
  {
    period_before_recording: (recorded) =>
      `recording began on ${recorded}, after this period started`,
    no_source: () => "this activity is not recorded",
    read_failed: () => "the value could not be read reliably",
  };

export const RUN_FAILURES: Record<string, string> = {
  ai_rate_limited: "the AI service is rate-limited, try again in a few minutes",
  ai_timeout: "the AI service took too long to respond",
  ai_unavailable: "the AI service is unavailable, try again later",
  context_load_failed: "the stored response data could not be loaded",
  save_failed: "the grades could not be saved",
  run_expired: "the run exceeded its 15-minute limit",
};

export const NETWORK_MESSAGE =
  "Could not reach the server. Check your connection and try again.";
export const TIMEOUT_MESSAGE =
  "The request timed out after 15 seconds. Try again.";
export const FORBIDDEN_MESSAGE = "You do not have access to analytics.";

export const isAborted = (error: unknown) =>
  error instanceof ApiError && error.code === "aborted";

/** Copy for a failed panel or page read; `subject` is the panel's name. */
export function loadFailure(subject: string, error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "network") return NETWORK_MESSAGE;
    if (error.code === "timeout") return TIMEOUT_MESSAGE;
    if (error.status === 403) return FORBIDDEN_MESSAGE;
    if (error.status > 0)
      return `${subject} could not be loaded: the server returned an error (${error.status}). Try again.`;
  }
  return `${subject} could not be loaded: the server returned an unreadable reply. Try again.`;
}

export const PRIVACY_UNAVAILABLE =
  "AI grading is unavailable because the local privacy scanner is not ready. Try again later.";

/** Copy for a failed grading start. */
export function startFailure(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "privacy_grading_disabled")
      return "AI grading is disabled because free-text privacy protection has not been approved.";
    if (error.code === "privacy_scanner_unavailable")
      return PRIVACY_UNAVAILABLE;
    if (error.code === "network")
      return "Could not reach the server. Reload to check whether grading started.";
    if (error.code === "timeout")
      return "The request timed out after 15 seconds. Reload to check whether grading started.";
    if (error.status === 403) return FORBIDDEN_MESSAGE;
    if (error.status === 409) return "A grading run is already in progress.";
    if (error.status === 429)
      return "Grading run limit reached. Try again later.";
    if (error.status === 422 && typeof error.detail.message === "string")
      return error.detail.message;
    if (error.status > 0)
      return `Grading could not be started: the server returned an error (${error.status}).`;
  }
  return "Grading could not be started: the server returned an unreadable reply.";
}

/** Copy for a failed progress check. */
export function pollFailure(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "network")
      return "Could not reach the server. Grading may still be running.";
    if (error.code === "timeout")
      return "The request timed out after 15 seconds. Grading may still be running.";
    if (error.status === 403) return FORBIDDEN_MESSAGE;
    if (error.status > 0)
      return `Grading progress could not be checked: the server returned an error (${error.status}).`;
  }
  return "Grading progress could not be checked: the server returned an unreadable reply.";
}

// ---- ADM-07 hub reads ----

export type Severity = "low_sample" | "ok" | "warning" | "critical";
export type FailureTile = Base & {
  total: number | null;
  failed: number | null;
  in_progress: number | null;
  rate_percent: number | null;
  severity: Severity | null;
  includes_rate_limited?: boolean;
};
export type TimeSet = {
  count: number | null;
  median_ms: number | null;
  p95_ms: number | null;
};
export type ResponseTimeTile = Base & {
  all: TimeSet;
  successful: TimeSet;
  failed: TimeSet;
};
export type Health = {
  period_start: string;
  period_end: string;
  recording_started_on: string;
  data_starts_on: string | null;
  as_of: string;
  low_sample_threshold: number;
  chatbot_failure: FailureTile;
  generation_failure: FailureTile;
  rate_limited: Base & {
    since: string | null;
    count: number | null;
    total_requests: number | null;
  };
  chatbot_response_time: ResponseTimeTile;
  generation_response_time: ResponseTimeTile;
  practice_completion: Usage["practice_completion"];
};

export const CATEGORIES = [
  "timeout",
  "rate_limited",
  "invalid_output",
  "upstream",
  "unclassified",
] as const;
export type Category = (typeof CATEGORIES)[number];
export type HourlyBucket = {
  hour_start: string;
  successful: number;
  failed: number;
  total: number;
  failure_rate_percent: number | null;
  failed_by_category: Record<Category, number>;
};
export type Hourly = Base & {
  recording_started_on: string;
  as_of: string;
  in_progress: number | null;
  retention_days: number;
  category_breakdown: { state: State; reason: Reason | null };
  totals: { successful: number; failed: number; total: number } | null;
  buckets: HourlyBucket[];
};

export type DailySeries = Base & {
  since: string | null;
  per_day: Record<string, string | number>[];
  total_logins?: number | null;
  total?: number | null;
};
export type Funnel = Base & {
  started_total: number | null;
  submitted_by_period_end: number | null;
  per_day: { date: string; started: number; submitted: number }[];
};
export type PerStudentDay = {
  date: string;
  active_students: number;
  median_attempts: number | null;
  distribution: Record<"1" | "2" | "3" | "4" | "5_plus", number>;
};
export type Daily = {
  period_start: string;
  period_end: string;
  recording_started_on: string;
  logins: DailySeries;
  practice_drafts_started: DailySeries;
  practice_published: DailySeries;
  attempts_funnel: Funnel;
  attempts_per_student: Base & { per_day: PerStudentDay[] };
};

export type UsersRole = "student" | "teacher";
export type UsersSort = "unsuccessful" | "successful" | "name" | "failure_rate";
export type UsersOrder = "asc" | "desc";
export type UsersQuery = {
  role: UsersRole;
  sort: UsersSort;
  order: UsersOrder;
  offset: number;
};
export const USERS_PAGE_SIZE = 10;
export type ChatbotUsers = Base & {
  recording_started_on: string;
  as_of: string;
  in_progress: number | null;
  role: UsersRole;
  sort: UsersSort;
  order: UsersOrder;
  totals: { successful: number | null; unsuccessful: number | null };
  all_users_total: Base & {
    successful: number | null;
    unsuccessful: number | null;
  };
  limit: number;
  offset: number;
  total_users: number | null;
  rows: (UserRow & { failure_rate_percent: number | null })[];
};

export const getHealth = async (
  period: Period,
  signal?: AbortSignal,
): Promise<Health> =>
  checked<Health>(
    await read(`/api/admin/analytics/health?${query(period)}`, signal),
    ["chatbot_failure", "generation_failure", "chatbot_response_time"],
  );

export async function getHourly(
  period: Period,
  signal?: AbortSignal,
): Promise<Hourly> {
  const data = checked<Hourly>(
    await read(`/api/admin/analytics/hourly?${query(period)}`, signal),
    ["state", "buckets", "category_breakdown"],
  );
  if (!Array.isArray(data.buckets)) throw new ApiError(0, "bad_response");
  return data;
}

export const getDaily = async (
  period: Period,
  signal?: AbortSignal,
): Promise<Daily> =>
  checked<Daily>(
    await read(`/api/admin/analytics/daily?${query(period)}`, signal),
    ["logins", "attempts_funnel", "attempts_per_student"],
  );

export async function getChatbotUsers(
  period: Period,
  users: UsersQuery,
  signal?: AbortSignal,
): Promise<ChatbotUsers> {
  const data = checked<ChatbotUsers>(
    await read(
      `/api/admin/analytics/chatbot-users?role=${users.role}&sort=${users.sort}&order=${users.order}&limit=${USERS_PAGE_SIZE}&offset=${users.offset}&${query(period)}`,
      signal,
    ),
    ["state", "totals", "rows"],
  );
  if (!Array.isArray(data.rows)) throw new ApiError(0, "bad_response");
  return data;
}

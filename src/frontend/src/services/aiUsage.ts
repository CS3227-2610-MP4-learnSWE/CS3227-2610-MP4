import { ApiError, request } from "./client";

export const FEATURE_LABELS = {
  "STU-03": "Student assistant (STU-03)",
  "TEA-02": "Teacher generation (TEA-02)",
  "ADM-03": "Feedback analysis (ADM-03)",
  "ADM-01": "Feature analytics (ADM-01)",
} as const;
export type Feature = keyof typeof FEATURE_LABELS;
export type Filters = {
  feature: "all" | Feature;
  start_date: string;
  end_date: string;
};
export const REASONS = {
  incomplete_coverage: "Coverage does not include the whole period.",
  not_enabled: "Collection is not enabled for this feature.",
  pending_attempts: "Some service calls have not finished recording.",
  missing_measurement:
    "The provider did not supply this measurement for every call.",
  no_measurements: "No recorded token measurements in this period.",
} as const;
export type Metric = {
  value: number | null;
  reason: keyof typeof REASONS | null;
};
export const METRIC_LABELS = {
  requests: "Requests",
  failures: "Failures",
  rate_limit_failures: "Rate-limit failures",
  other_failures: "Other failures",
  input_tokens: "Input tokens",
  output_tokens: "Output tokens",
  total_tokens: "Total tokens",
} as const;
export type MetricKey = keyof typeof METRIC_LABELS;
export type UsageRow = {
  feature: Feature;
  coverage_start: string | null;
} & Record<MetricKey, Metric>;
export type UsageReport = Filters & {
  timezone: "UTC";
  as_of: string;
  rows: UsageRow[];
};

export const INVALID_FILTERS =
  "Choose a valid feature and a UTC date range of at most 31 days ending today or earlier.";

export function defaultFilters(): Filters {
  const today = new Date();
  const start = new Date(today);
  start.setUTCDate(start.getUTCDate() - 6);
  return {
    feature: "all",
    start_date: start.toISOString().slice(0, 10),
    end_date: today.toISOString().slice(0, 10),
  };
}

function validDate(value: string) {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value)) return false;
  const time = Date.parse(`${value}T00:00:00Z`);
  return (
    Number.isFinite(time) &&
    new Date(time).toISOString().slice(0, 10) === value &&
    value >= "0001-01-01"
  );
}

export function validFilters(filters: Filters): boolean {
  const { feature, start_date: start, end_date: end } = filters;
  return (
    (feature === "all" || Object.hasOwn(FEATURE_LABELS, feature)) &&
    validDate(start) &&
    validDate(end) &&
    start <= end &&
    end <= new Date().toISOString().slice(0, 10) &&
    (Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) /
      86_400_000 <
      31
  );
}

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function keys(value: Record<string, unknown>, wanted: string[]) {
  return (
    Object.keys(value).length === wanted.length &&
    wanted.every((key) => Object.hasOwn(value, key))
  );
}
function timestamp(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^\d{4}-\d{2}-\d{2}T.*(?:Z|\+00:00)$/.test(value) &&
    Number.isFinite(Date.parse(value))
  );
}
function metric(value: unknown): value is Metric {
  if (!object(value) || !keys(value, ["value", "reason"])) return false;
  return value.value === null
    ? typeof value.reason === "string" && Object.hasOwn(REASONS, value.reason)
    : typeof value.value === "number" &&
        Number.isSafeInteger(value.value) &&
        value.value >= 0 &&
        value.reason === null;
}

export async function readUsage(
  filters: Filters,
  signal?: AbortSignal,
): Promise<UsageReport> {
  const data = await request(
    "GET",
    `/api/admin/ai-usage?${new URLSearchParams(filters)}`,
    undefined,
    { timeoutMs: 15_000, distinguishTimeout: true, cache: "no-store", signal },
  );
  const features =
    filters.feature === "all" ? Object.keys(FEATURE_LABELS) : [filters.feature];
  if (
    !object(data) ||
    !keys(data, [
      "feature",
      "start_date",
      "end_date",
      "timezone",
      "as_of",
      "rows",
    ]) ||
    data.feature !== filters.feature ||
    data.start_date !== filters.start_date ||
    data.end_date !== filters.end_date ||
    data.timezone !== "UTC" ||
    !timestamp(data.as_of) ||
    !Array.isArray(data.rows) ||
    data.rows.length !== features.length ||
    !data.rows.every(
      (row: unknown, index: number) =>
        object(row) &&
        keys(row, [
          "feature",
          "coverage_start",
          ...Object.keys(METRIC_LABELS),
        ]) &&
        row.feature === features[index] &&
        (row.coverage_start === null || timestamp(row.coverage_start)) &&
        Object.keys(METRIC_LABELS).every((key) => metric(row[key])),
    )
  ) {
    throw new ApiError(0, "bad_response");
  }
  return data as UsageReport;
}

export function usageError(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<number, string> = {
      401: "Your session has expired. Sign in again.",
      403: "You do not have access to AI usage.",
      422: INVALID_FILTERS,
      429: "Too many report requests. Try again shortly.",
      503: "AI usage data is temporarily unavailable. Try again.",
    };
    if (messages[error.status]) return messages[error.status];
    if (error.code === "network")
      return "Could not reach the server. Check your connection and retry.";
    if (error.code === "timeout")
      return "AI usage request timed out. Try again.";
  }
  return "The server returned an invalid AI usage report. Try again.";
}

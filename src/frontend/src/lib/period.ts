import {
  checkPeriod,
  isoDay,
  type Period,
  type PeriodErrors,
} from "../services/featureAnalytics";

export type Range = "today" | "7d" | "30d";
export const RANGES: { id: Range; label: string; days: number }[] = [
  { id: "today", label: "Today (UTC)", days: 1 },
  { id: "7d", label: "Last 7 days", days: 7 },
  { id: "30d", label: "Last 30 days", days: 30 },
];
export const DEFAULT_RANGE: Range = "7d";
export const FUTURE_MESSAGE = "The end date cannot be in the future (UTC).";

export const todayUtc = () => isoDay(new Date());

/** Range of the hourly charts: the page period, or the last 24 hours, 3 days or 7 days ending now. */
export type HourlyRange = "period" | "24h" | "3d" | "7d";
export const HOURLY_RANGES: { id: HourlyRange; label: string; hours: number }[] =
  [
    { id: "period", label: "Selected period", hours: 0 },
    { id: "24h", label: "Last 24 hours", hours: 24 },
    { id: "3d", label: "Last 3 days", hours: 72 },
    { id: "7d", label: "Last 7 days", hours: 168 },
  ];
const HOUR_MS = 3_600_000;
const currentHour = (now: Date) => Math.floor(now.getTime() / HOUR_MS) * HOUR_MS;

/** What to request for the hourly charts: the whole UTC days that cover the range (the server works in days). */
export function hourlyRequestPeriod(
  range: HourlyRange,
  period: Period,
  now: Date,
): Period {
  const hours = HOURLY_RANGES.find((r) => r.id === range)?.hours ?? 0;
  if (!hours) return period;
  return {
    from: isoDay(new Date(currentHour(now) - (hours - 1) * HOUR_MS)),
    to: isoDay(now),
  };
}

/** Whether an hour bucket falls inside a rolling range: the last N hours ending with the current hour. */
export function inHourlyRange(
  hourStartIso: string,
  range: HourlyRange,
  now: Date,
): boolean {
  const hours = HOURLY_RANGES.find((r) => r.id === range)?.hours ?? 0;
  if (!hours) return true;
  const at = new Date(hourStartIso).getTime();
  const end = currentHour(now);
  return at <= end && at > end - hours * HOUR_MS;
}

/** Presets are UTC calendar dates ending today (UTC). */
export function resolvePeriod(range: Range, today: string): Period {
  const days = RANGES.find((r) => r.id === range)?.days ?? 7;
  const start = new Date(`${today}T00:00:00Z`);
  start.setUTCDate(start.getUTCDate() - (days - 1));
  return { from: isoDay(start), to: today };
}

/** The server's three period rules in the server's order, then the client-only future rule. */
export function customPeriodErrors(
  from: string,
  to: string,
  today: string,
): PeriodErrors {
  const errors = checkPeriod({ from, to });
  if (Object.keys(errors).length > 0) return errors;
  return to.trim() > today ? { to: FUTURE_MESSAGE } : {};
}

export function validateCustomPeriod(
  from: string,
  to: string,
  today: string,
): string | null {
  const errors = customPeriodErrors(from, to, today);
  return errors.from ?? errors.to ?? null;
}

/** What the page shows: a preset or a custom pair. */
export type PeriodChoice =
  | { kind: "range"; range: Range }
  | { kind: "custom"; from: string; to: string };

/** `range` wins only if valid, else a valid `from`/`to` pair, else the default. */
export function choiceFromParams(
  params: URLSearchParams,
  today: string,
): PeriodChoice {
  const range = params.get("range");
  const preset = RANGES.find((r) => r.id === range);
  if (preset) return { kind: "range", range: preset.id };
  const from = params.get("from") ?? "";
  const to = params.get("to") ?? "";
  if (validateCustomPeriod(from, to, today) === null)
    return { kind: "custom", from, to };
  return { kind: "range", range: DEFAULT_RANGE };
}

export const periodOfChoice = (choice: PeriodChoice, today: string): Period =>
  choice.kind === "custom"
    ? { from: choice.from, to: choice.to }
    : resolvePeriod(choice.range, today);

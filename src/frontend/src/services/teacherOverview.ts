import { ApiError, request } from "./client";

export const OVERVIEW_PERIODS = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "all", label: "All time" },
] as const;
export type Period = (typeof OVERVIEW_PERIODS)[number]["value"];
export const DEFAULT_PERIOD: Period = "30d";

export type OverviewLesson = {
  lesson_id: string;
  title: string;
  topic: string;
  completed_students: number;
  rate_percent: number | null;
};
export type OverviewSet = {
  set_id: string;
  title: string;
  topic: string;
  students_attempted: number;
  submitted_attempts: number;
  average_score_percent: number | null;
};
export type MissedQuestion = {
  set_id: string;
  set_title: string;
  position: number;
  question: string;
  missed: number;
  answered: number;
  miss_rate_percent: number;
};
export type OverviewCourse = {
  course_id: string;
  title: string;
  student_count: number;
  lesson_count: number;
  completion_rate_percent: number | null;
  lessons: OverviewLesson[];
  practice: { sets: OverviewSet[]; missed_questions: MissedQuestion[] };
};
export type OverviewPeriod = {
  preset: Period;
  start: string | null;
  end: string;
  start_date: string | null;
  end_date: string;
  timezone: "UTC";
};
export type Overview = {
  period: OverviewPeriod;
  as_of: string;
  courses: OverviewCourse[];
};

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function keys(
  value: unknown,
  wanted: string[],
): value is Record<string, unknown> {
  return (
    object(value) &&
    Object.keys(value).length === wanted.length &&
    wanted.every((key) => Object.hasOwn(value, key))
  );
}
const text = (value: unknown) => typeof value === "string";
const count = (value: unknown) =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const percent = (value: unknown) =>
  value === null || (count(value) && (value as number) <= 100);
const timestamp = (value: unknown) =>
  typeof value === "string" &&
  /^\d{4}-\d{2}-\d{2}T.*Z$/.test(value) &&
  Number.isFinite(Date.parse(value));
const date = (value: unknown) =>
  text(value) && /^\d{4}-\d{2}-\d{2}$/.test(value as string);
const dateOrNull = (value: unknown) => value === null || date(value);
const all = (value: unknown, check: (item: unknown) => boolean) =>
  Array.isArray(value) && value.every(check);

const validLesson = (l: unknown) =>
  keys(l, [
    "lesson_id",
    "title",
    "topic",
    "completed_students",
    "rate_percent",
  ]) &&
  text(l.lesson_id) &&
  text(l.title) &&
  text(l.topic) &&
  count(l.completed_students) &&
  percent(l.rate_percent);
const validSet = (s: unknown) =>
  keys(s, [
    "set_id",
    "title",
    "topic",
    "students_attempted",
    "submitted_attempts",
    "average_score_percent",
  ]) &&
  text(s.set_id) &&
  text(s.title) &&
  text(s.topic) &&
  count(s.students_attempted) &&
  count(s.submitted_attempts) &&
  percent(s.average_score_percent);
const validMissed = (m: unknown) =>
  keys(m, [
    "set_id",
    "set_title",
    "position",
    "question",
    "missed",
    "answered",
    "miss_rate_percent",
  ]) &&
  text(m.set_id) &&
  text(m.set_title) &&
  text(m.question) &&
  count(m.position) &&
  count(m.missed) &&
  count(m.answered) &&
  m.miss_rate_percent !== null &&
  percent(m.miss_rate_percent);
const validCourse = (c: unknown) =>
  keys(c, [
    "course_id",
    "title",
    "student_count",
    "lesson_count",
    "completion_rate_percent",
    "lessons",
    "practice",
  ]) &&
  text(c.course_id) &&
  text(c.title) &&
  count(c.student_count) &&
  count(c.lesson_count) &&
  percent(c.completion_rate_percent) &&
  all(c.lessons, validLesson) &&
  keys(c.practice, ["sets", "missed_questions"]) &&
  all(c.practice.sets, validSet) &&
  all(c.practice.missed_questions, validMissed);

export async function readOverview(period: Period): Promise<Overview> {
  const data = await request(
    "GET",
    `/api/teacher/overview?period=${period}`,
    undefined,
    { timeoutMs: 15_000, distinguishTimeout: true, cache: "no-store" },
  );
  if (
    !keys(data, ["period", "as_of", "courses"]) ||
    !keys(data.period, [
      "preset",
      "start",
      "end",
      "start_date",
      "end_date",
      "timezone",
    ]) ||
    data.period.preset !== period ||
    data.period.timezone !== "UTC" ||
    !(data.period.start === null || timestamp(data.period.start)) ||
    !timestamp(data.period.end) ||
    !dateOrNull(data.period.start_date) ||
    !date(data.period.end_date) ||
    !timestamp(data.as_of) ||
    !all(data.courses, validCourse)
  ) {
    throw new ApiError(0, "bad_response");
  }
  return data as Overview;
}

export function overviewError(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<number, string> = {
      401: "Your session has expired. Sign in again.",
      403: "You do not have access to the learning overview.",
      422: "Choose Last 7 days, Last 30 days or All time.",
      429: "Too many overview requests. Try again shortly.",
      503: "The learning overview is temporarily unavailable. Try again.",
    };
    if (messages[error.status]) return messages[error.status];
    if (error.code === "network")
      return "Could not reach the server. Check your connection and retry.";
    if (error.code === "timeout")
      return "The learning overview request timed out. Try again.";
  }
  return "The server returned an invalid learning overview. Try again.";
}

export function periodLine(period: OverviewPeriod): string {
  const label = OVERVIEW_PERIODS.find((p) => p.value === period.preset)?.label;
  return period.start_date === null
    ? `Period: ${label}, up to ${period.end_date} (UTC)`
    : `Period: ${label}, ${period.start_date} to ${period.end_date} (UTC)`;
}

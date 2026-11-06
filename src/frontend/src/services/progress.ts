import { ApiError } from "./client";
import { readOnce } from "./readOnce";

export type ProgressCourse = {
  id: string;
  title: string;
  lesson_count: number;
  completed_count: number;
};
export type ProgressRecentLesson = {
  lesson_id: string;
  course_id: string;
  title: string;
  completed_at: string;
};
export type ProgressSet = {
  set_id: string;
  title: string;
  attempts_submitted: number;
  best: { correct: number; total: number };
  latest: { correct: number; total: number; submitted_at: string };
};
export type TopicStatus = "needs_practice" | "on_track" | "insufficient";
export type ProgressTopic = {
  topic: { id: string | null; name: string };
  answered: number;
  correct: number;
  accuracy_percent: number;
  status: TopicStatus;
};
export type Progress = {
  lessons: {
    totals: { lesson_count: number; completed_count: number };
    courses: ProgressCourse[];
    recent: ProgressRecentLesson[];
  };
  practice: { sets: ProgressSet[]; average_latest_percent: number | null };
  topics: {
    rule: { min_answers: number; weak_below_percent: number };
    items: ProgressTopic[];
  };
};

const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const isString = (v: unknown): v is string => typeof v === "string";
const isCount = (v: unknown): v is number =>
  Number.isInteger(v) && (v as number) >= 0;
const isScore = (v: unknown, withTime: boolean) =>
  isObject(v) &&
  isCount(v.correct) &&
  isCount(v.total) &&
  (!withTime || isString(v.submitted_at));
const isCourse = (v: unknown) =>
  isObject(v) &&
  isString(v.id) &&
  isString(v.title) &&
  isCount(v.lesson_count) &&
  isCount(v.completed_count);
const isRecent = (v: unknown) =>
  isObject(v) &&
  isString(v.lesson_id) &&
  isString(v.course_id) &&
  isString(v.title) &&
  isString(v.completed_at);
const isSet = (v: unknown) =>
  isObject(v) &&
  isString(v.set_id) &&
  isString(v.title) &&
  isCount(v.attempts_submitted) &&
  isScore(v.best, false) &&
  isScore(v.latest, true);
const STATUSES = ["needs_practice", "on_track", "insufficient"];
const isTopic = (v: unknown) =>
  isObject(v) &&
  isObject(v.topic) &&
  (v.topic.id === null || isString(v.topic.id)) &&
  isString(v.topic.name) &&
  isCount(v.answered) &&
  isCount(v.correct) &&
  isCount(v.accuracy_percent) &&
  isString(v.status) &&
  STATUSES.includes(v.status);

function isProgress(data: unknown): data is Progress {
  if (!isObject(data)) return false;
  const { lessons, practice, topics } = data;
  return (
    isObject(lessons) &&
    isObject(lessons.totals) &&
    isCount(lessons.totals.lesson_count) &&
    isCount(lessons.totals.completed_count) &&
    Array.isArray(lessons.courses) &&
    lessons.courses.every(isCourse) &&
    Array.isArray(lessons.recent) &&
    lessons.recent.every(isRecent) &&
    isObject(practice) &&
    Array.isArray(practice.sets) &&
    practice.sets.every(isSet) &&
    (practice.average_latest_percent === null ||
      isCount(practice.average_latest_percent)) &&
    isObject(topics) &&
    isObject(topics.rule) &&
    isCount(topics.rule.min_answers) &&
    isCount(topics.rule.weak_below_percent) &&
    Array.isArray(topics.items) &&
    topics.items.every(isTopic)
  );
}

export async function getProgress(): Promise<Progress> {
  const data = await readOnce("/api/progress");
  if (!isProgress(data)) throw new ApiError(0, "bad_response");
  return data;
}

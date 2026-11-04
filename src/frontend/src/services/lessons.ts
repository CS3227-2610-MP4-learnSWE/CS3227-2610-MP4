import { ApiError, getSessionGeneration, request } from "./client";

export type CourseSummary = {
  id: string;
  title: string;
  lesson_count: number;
  completed_count: number;
};
export type LessonSummary = {
  id: string;
  title: string;
  excerpt: string;
  completed: boolean;
};
export type TopicGroup = {
  id: string | null;
  name: string;
  lessons: LessonSummary[];
};
export type LessonDetail = {
  id: string;
  course: { id: string; title: string };
  topic: { id: string | null; name: string };
  title: string;
  content: string;
  published_at: string;
  completed: boolean;
  completed_at: string | null;
};
export type CompletionResult = {
  lesson_id: string;
  completed: boolean;
  completed_at: string | null;
  course: { id: string; lesson_count: number; completed_count: number };
};

const bad = () => new ApiError(0, "bad_response");
const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const isString = (v: unknown): v is string => typeof v === "string";
const isCount = (v: unknown): v is number =>
  Number.isInteger(v) && (v as number) >= 0;
const isNullableString = (v: unknown) => v === null || isString(v);
const isCourseRef = (v: unknown) =>
  isObject(v) && isString(v.id) && isString(v.title);
const seg = (id: string) => encodeURIComponent(id);

// Identical GETs already in flight share one request (React StrictMode runs
// effects twice in development); a finished request is never reused, and a
// request started before a sign-in/out or a completion change is never shared
// with a page opened after it.
const inFlight = new Map<string, Promise<unknown>>();
let writes = 0;
function readOnce(path: string): Promise<unknown> {
  const key = `${getSessionGeneration()}:${writes}:${path}`;
  const pending = inFlight.get(key);
  if (pending) return pending;
  const started = request("GET", path).finally(() => inFlight.delete(key));
  inFlight.set(key, started);
  return started;
}

export async function listCourses(): Promise<{
  courses: CourseSummary[];
  totals: { lesson_count: number; completed_count: number };
}> {
  const data = await readOnce("/api/study/courses");
  if (
    !isObject(data) ||
    !Array.isArray(data.courses) ||
    !isObject(data.totals) ||
    !isCount(data.totals.lesson_count) ||
    !isCount(data.totals.completed_count) ||
    !data.courses.every(
      (c) =>
        isCourseRef(c) &&
        isCount((c as CourseSummary).lesson_count) &&
        isCount((c as CourseSummary).completed_count),
    )
  )
    throw bad();
  return data as {
    courses: CourseSummary[];
    totals: { lesson_count: number; completed_count: number };
  };
}

export async function listCourseLessons(courseId: string): Promise<{
  course: { id: string; title: string };
  topics: TopicGroup[];
}> {
  const data = await readOnce(`/api/study/courses/${seg(courseId)}/lessons`);
  if (
    !isObject(data) ||
    !isCourseRef(data.course) ||
    !Array.isArray(data.topics) ||
    !data.topics.every(
      (t) =>
        isObject(t) &&
        isNullableString(t.id) &&
        isString(t.name) &&
        Array.isArray(t.lessons) &&
        t.lessons.every(
          (l) =>
            isObject(l) &&
            isString(l.id) &&
            isString(l.title) &&
            isString(l.excerpt) &&
            typeof l.completed === "boolean",
        ),
    )
  )
    throw bad();
  return data as {
    course: { id: string; title: string };
    topics: TopicGroup[];
  };
}

export async function getLesson(lessonId: string): Promise<LessonDetail> {
  const data = await readOnce(`/api/study/lessons/${seg(lessonId)}`);
  if (
    !isObject(data) ||
    !isString(data.id) ||
    !isCourseRef(data.course) ||
    !isObject(data.topic) ||
    !isNullableString(data.topic.id) ||
    !isString(data.topic.name) ||
    !isString(data.title) ||
    !isString(data.content) ||
    !isString(data.published_at) ||
    typeof data.completed !== "boolean" ||
    !isNullableString(data.completed_at)
  )
    throw bad();
  return data as LessonDetail;
}

export async function setCompletion(
  lessonId: string,
  completed: boolean,
): Promise<CompletionResult> {
  writes += 1;
  let data: unknown;
  try {
    data = await request(
      "PUT",
      `/api/study/lessons/${seg(lessonId)}/completion`,
      { completed },
    );
  } finally {
    writes += 1;
  }
  if (
    !isObject(data) ||
    !isString(data.lesson_id) ||
    typeof data.completed !== "boolean" ||
    !isNullableString(data.completed_at) ||
    !isObject(data.course) ||
    !isString(data.course.id) ||
    !isCount(data.course.lesson_count) ||
    !isCount(data.course.completed_count)
  )
    throw bad();
  return data as CompletionResult;
}

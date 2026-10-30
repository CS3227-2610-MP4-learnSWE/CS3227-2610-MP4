import { ApiError, request } from "./client";

export type Choice = { id: string; text: string };
export type Question = {
  id: string;
  text: string;
  code: string | null;
  choices: Choice[];
};
export type PracticeSet = { id: string; title: string; questions: Question[] };
export type QuestionResult = {
  id: string;
  selected: string;
  correct_choice: string;
  correct: boolean;
  explanation: string;
};
export type Results = {
  score: { correct: number; total: number };
  questions: QuestionResult[];
};

const bad = () => new ApiError(0, "bad_response");
const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const isString = (v: unknown): v is string => typeof v === "string";
const isInt = (v: unknown): v is number => Number.isInteger(v);
const seg = (id: string) => encodeURIComponent(id);

function parseSet(data: unknown): PracticeSet {
  if (
    !isObject(data) ||
    !isString(data.id) ||
    !isString(data.title) ||
    !Array.isArray(data.questions) ||
    data.questions.length === 0
  )
    throw bad();
  for (const q of data.questions) {
    if (
      !isObject(q) ||
      !isString(q.id) ||
      !isString(q.text) ||
      !(q.code === null || isString(q.code)) ||
      !Array.isArray(q.choices) ||
      q.choices.length === 0 ||
      !q.choices.every((c) => isObject(c) && isString(c.id) && isString(c.text))
    )
      throw bad();
  }
  return data as PracticeSet;
}

function parseResults(data: unknown): Results {
  if (
    !isObject(data) ||
    !isObject(data.score) ||
    !isInt(data.score.correct) ||
    !isInt(data.score.total) ||
    !Array.isArray(data.questions) ||
    !data.questions.every(
      (q) =>
        isObject(q) &&
        isString(q.id) &&
        isString(q.selected) &&
        isString(q.correct_choice) &&
        typeof q.correct === "boolean" &&
        isString(q.explanation),
    )
  )
    throw bad();
  return data as Results;
}

export async function getSet(setId: string): Promise<PracticeSet> {
  return parseSet(await request("GET", `/api/practice-sets/${seg(setId)}`));
}

export async function startAttempt(setId: string): Promise<string> {
  const data = await request(
    "POST",
    `/api/practice-sets/${seg(setId)}/attempts`,
  );
  if (!isObject(data) || !isString(data.attempt_id) || !data.attempt_id)
    throw bad();
  return data.attempt_id;
}

export async function saveAnswers(
  attemptId: string,
  answers: Record<string, string>,
): Promise<void> {
  const data = await request("PUT", `/api/attempts/${seg(attemptId)}/answers`, {
    answers,
  });
  if (!isObject(data) || !isObject(data.answers)) throw bad();
}

export async function submitAttempt(attemptId: string): Promise<void> {
  const data = await request("POST", `/api/attempts/${seg(attemptId)}/submit`);
  if (!isObject(data) || data.status !== "submitted") throw bad();
}

export async function getResults(attemptId: string): Promise<Results> {
  return parseResults(
    await request("GET", `/api/attempts/${seg(attemptId)}/results`),
  );
}

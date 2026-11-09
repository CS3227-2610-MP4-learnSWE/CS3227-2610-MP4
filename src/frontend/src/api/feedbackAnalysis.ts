import { ApiError, request } from "../services/client";

const BASE = "/api/admin/feedback";
const options = {
  timeoutMs: 15000,
  distinguishTimeout: true,
  cache: "no-store" as const,
};

export type OptionStat = {
  option_id: string;
  label: string;
  count: number;
  percent: number;
};
export type Aggregate = {
  question_id: string;
  prompt: string;
  kind: "text" | "single" | "multi" | "scale";
  answered: number;
  skipped: number;
  options?: OptionStat[];
  min?: number;
  max?: number;
  mean?: number | null;
  median?: number | null;
  distribution?: { label: string; count: number; percent: number }[];
};
export type Step = { kind: string; index: number | null; total: number | null };
export type Failure = {
  code: string;
  message: string;
  step: Step;
  details: Record<string, unknown>;
};
export type Result = {
  summary: string;
  themes: { title: string; description: string; evidence: string[] }[];
  suggestions: { text: string; basis: "feedback" | "ai"; evidence: string[] }[];
};
export type Analysis = {
  id: string;
  form_id: string;
  form_title: string;
  created_at: string;
  response_count: number;
  mode: "explicit" | "select_all";
  expected_count: number | null;
  labels: { label: string; submitted_at: string }[];
  aggregates: Aggregate[];
  free_text: { total: number; used: number };
  ai: {
    status: "running" | "complete" | "failed";
    progress: { done: number; total: number; step: Step | null };
    result: Result | null;
    error: Failure | null;
    completed_at: string | null;
  };
};
export type HistoryItem = {
  id: string;
  form_id: string;
  form_title: string;
  created_at: string;
  response_count: number;
  ai_status: "running" | "complete" | "failed";
};
export type Page<T> = { items: T[]; next_offset: number | null };
export type FormItem = { id: string; title: string };
export type ResponseItem = {
  id: string;
  respondent: { id: string; display_name: string };
  submitted_at: string;
};
export type Evidence = {
  label: string;
  response: {
    respondent: { display_name: string };
    submitted_at: string;
    form_snapshot: {
      questions: {
        id: string;
        prompt: string;
        type: string;
        options: { id: string; label: string }[];
      }[];
    };
    answers: { question_id: string; value: unknown }[];
  };
};

const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null;

/** A reply that does not have the expected shape is unreadable and is never rendered. */
function checked<T>(
  data: unknown,
  ok: (v: Record<string, unknown>) => boolean,
): T {
  if (!isObject(data) || !ok(data)) throw new ApiError(0, "bad_response");
  return data as T;
}
const isPage = (v: Record<string, unknown>) => Array.isArray(v.items);
const isAnalysis = (v: Record<string, unknown>) =>
  typeof v.id === "string" &&
  Array.isArray(v.aggregates) &&
  Array.isArray(v.labels) &&
  isObject(v.ai);

const get = (path: string) =>
  request("GET", `${BASE}${path}`, undefined, options);
const id = encodeURIComponent;

export const listForms = async () =>
  checked<Page<FormItem>>(await get("/forms?limit=100&offset=0"), isPage);
export const listResponses = async (formId: string, offset: number) =>
  checked<Page<ResponseItem>>(
    await get(`/forms/${id(formId)}/responses?limit=100&offset=${offset}`),
    isPage,
  );
export const responseCount = async (formId: string) =>
  checked<{ count: number }>(
    await get(`/forms/${id(formId)}/response-count`),
    (v) => typeof v.count === "number",
  );
export const listAnalyses = async (offset: number) =>
  checked<Page<HistoryItem>>(
    await get(`/analyses?limit=20&offset=${offset}`),
    isPage,
  );
export const getAnalysis = async (analysisId: string) =>
  checked<Analysis>(await get(`/analyses/${id(analysisId)}`), isAnalysis);
export const getEvidence = async (analysisId: string, label: string) =>
  checked<Evidence>(
    await get(`/analyses/${id(analysisId)}/responses/${id(label)}`),
    (v) => isObject(v.response),
  );
export const createAnalysis = async (body: object) =>
  checked<Analysis>(
    await request("POST", `${BASE}/analyses`, body, options),
    isAnalysis,
  );
export async function deleteAnalysis(analysisId: string): Promise<void> {
  await request(
    "DELETE",
    `${BASE}/analyses/${id(analysisId)}`,
    undefined,
    options,
  );
}

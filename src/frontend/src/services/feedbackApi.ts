import { ApiError, getSessionGeneration, request } from "./client";

export type Association = null | { kind: "feature" | "lesson"; id: string };
export type QuestionType =
  | "short_answer"
  | "paragraph"
  | "multiple_choice"
  | "dropdown"
  | "checkbox"
  | "linear_scale";
export type Question = {
  id: string;
  type: QuestionType;
  prompt: string;
  required: boolean;
  options: { id: string; label: string }[];
  scale: null | {
    min: number;
    max: number;
    min_label: string;
    max_label: string;
  };
};
export type Answer = {
  question_id: string;
  value: null | string | string[] | number;
};
export function isBlankAnswer(value: Answer["value"] | undefined) {
  return (
    value === null ||
    value === undefined ||
    (typeof value === "string" && !value.trim()) ||
    (Array.isArray(value) && !value.length)
  );
}
export type Draft = {
  version: number;
  answers: Answer[];
  updated_at: string | null;
};
export type Definition = {
  title: string;
  description: string;
  association: Association;
  questions: Question[];
};
export type Form = Definition & {
  id: string;
  state: "draft" | "open" | "closed";
  version: number;
  audience_role: "student" | "teacher" | null;
  recipient_count: number;
  response_count: number;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  closed_at: string | null;
};
export type RecipientForm = Definition & {
  id: string;
  state: "open" | "closed";
  submitted: boolean;
  draft: Draft | null;
};
export type FormSummary = Omit<Form, "description" | "questions">;
export type Page<T> = { items: T[]; next_offset: number | null };
export type Audience = {
  id: string;
  display_name: string;
  role: "student" | "teacher";
};
export type Associations = {
  features: { id: string; label: string }[];
  lessons: { id: string; title: string }[];
  truncated: boolean;
};
export type InboxItem = {
  id: string;
  form_id: string;
  title: string;
  created_at: string;
  read_at: string | null;
  state: "open" | "closed";
  submitted: boolean;
  response_status: "not_started" | "draft" | "completed" | "closed";
};
export type ResponseSummary = {
  id: string;
  form_id: string;
  respondent: { id: string; display_name: string };
  submitted_at: string;
};
export type ResponseDetail = ResponseSummary & {
  form_snapshot: Definition;
  answers: Answer[];
};
export type Receipt = { id: string; form_id: string; submitted_at: string };

const messages: Record<string, string> = {
  unauthenticated: "Your session has expired. Sign in again.",
  forbidden: "You do not have permission to access this feedback page.",
  csrf_failed: "You do not have permission to access this feedback page.",
  feedback_not_found: "This feedback form or response is not available.",
  network: "Cannot connect to the server. Check your connection and try again.",
  timeout: "The request timed out. Check the current form before trying again.",
  feedback_rate_limited:
    "Too many feedback requests. Wait before trying again.",
  feedback_unavailable:
    "The feedback service is temporarily unavailable. Try again later.",
  invalid_feedback_input: "Check the feedback form fields and try again.",
  invalid_feedback_title: "Enter a title of 1 to 160 characters.",
  invalid_feedback_questions:
    "Add 1 to 30 valid questions with unique identifiers.",
  invalid_feedback_options:
    "Enter 2 to 20 distinct options for each choice question.",
  invalid_feedback_scale:
    "Set a scale with whole-number endpoints from 0 to 10, with the minimum below the maximum.",
  invalid_feedback_association:
    "Select an available feature or published lesson.",
  invalid_feedback_text: "One or more feedback fields exceed their text limit.",
  feedback_too_large:
    "This feedback request is too large. Reduce its content and try again.",
  invalid_feedback_audience:
    "Select 1 to 500 different recipients from one audience role.",
  invalid_feedback_answers:
    "Answer every required question and check that all answers match their question type.",
  invalid_feedback_draft_answers:
    "Check your draft answers and their size limits. Unanswered required questions can be saved.",
  feedback_version_conflict:
    "This form changed in another session. Reload the saved form before continuing.",
  feedback_state_conflict:
    "This action is not available in the form's current state.",
  feedback_audience_changed:
    "Some selected recipients are no longer eligible. Review the audience again.",
  feedback_closed: "This form is closed.",
  feedback_already_submitted: "You have already submitted feedback.",
  feedback_draft_version_conflict:
    "Your draft changed in another session. Reload the saved draft before continuing.",
};
export function feedbackError(error: unknown): string {
  if (error instanceof ApiError) {
    if (messages[error.code]) return messages[error.code];
    if (error.status === 401) return messages.unauthenticated;
    if (error.status === 403) return messages.forbidden;
    if (error.status === 503) return messages.feedback_unavailable;
  }
  return "The feedback service encountered an error. Try again later.";
}
export function feedbackCode(error: unknown) {
  return error instanceof ApiError ? error.code : "";
}
export function uncertain(error: unknown) {
  return error instanceof ApiError && error.status === 0;
}

function object(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}
function string(value: unknown): value is string {
  return typeof value === "string";
}
function number(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) >= 0;
}
function association(value: unknown): boolean {
  return (
    value === null ||
    (object(value) &&
      ["feature", "lesson"].includes(String(value.kind)) &&
      string(value.id))
  );
}
function question(value: unknown): boolean {
  return (
    object(value) &&
    string(value.id) &&
    string(value.prompt) &&
    typeof value.required === "boolean" &&
    [
      "short_answer",
      "paragraph",
      "multiple_choice",
      "dropdown",
      "checkbox",
      "linear_scale",
    ].includes(String(value.type)) &&
    Array.isArray(value.options) &&
    value.options.every((o) => object(o) && string(o.id) && string(o.label)) &&
    (value.scale === null ||
      (object(value.scale) &&
        number(value.scale.min) &&
        number(value.scale.max) &&
        string(value.scale.min_label) &&
        string(value.scale.max_label)))
  );
}
function definition(value: unknown): boolean {
  return (
    object(value) &&
    string(value.title) &&
    string(value.description) &&
    association(value.association) &&
    Array.isArray(value.questions) &&
    value.questions.every(question)
  );
}
function answer(value: unknown): boolean {
  return (
    object(value) &&
    string(value.question_id) &&
    (value.value === null ||
      string(value.value) ||
      number(value.value) ||
      (Array.isArray(value.value) && value.value.every(string)))
  );
}
function draft(value: unknown): boolean {
  return (
    object(value) &&
    number(value.version) &&
    Array.isArray(value.answers) &&
    value.answers.every(answer) &&
    (value.updated_at === null || string(value.updated_at))
  );
}
function summary(value: unknown): boolean {
  return (
    object(value) &&
    string(value.id) &&
    string(value.title) &&
    association(value.association) &&
    ["draft", "open", "closed"].includes(String(value.state)) &&
    number(value.version) &&
    number(value.recipient_count) &&
    number(value.response_count)
  );
}
function responseSummary(value: unknown): boolean {
  return (
    object(value) &&
    string(value.id) &&
    string(value.form_id) &&
    string(value.submitted_at) &&
    object(value.respondent) &&
    string(value.respondent.id) &&
    string(value.respondent.display_name)
  );
}
const checks = {
  form: (v: unknown) => definition(v) && summary(v),
  forms: (v: unknown) => page(v, summary),
  associations: (v: unknown) =>
    object(v) &&
    typeof v.truncated === "boolean" &&
    Array.isArray(v.features) &&
    v.features.every((i) => object(i) && string(i.id) && string(i.label)) &&
    Array.isArray(v.lessons) &&
    v.lessons.every((i) => object(i) && string(i.id) && string(i.title)),
  audience: (v: unknown) =>
    page(
      v,
      (i) =>
        object(i) &&
        string(i.id) &&
        string(i.display_name) &&
        ["student", "teacher"].includes(String(i.role)),
    ),
  inbox: (v: unknown) =>
    object(v) &&
    number(v.unread_count) &&
    page(
      v,
      (i) =>
        object(i) &&
        string(i.id) &&
        string(i.form_id) &&
        string(i.title) &&
        (i.read_at === null || string(i.read_at)) &&
        ["not_started", "draft", "completed", "closed"].includes(
          String(i.response_status),
        ),
    ),
  recipient: (v: unknown) =>
    definition(v) &&
    object(v) &&
    string(v.id) &&
    ["open", "closed"].includes(String(v.state)) &&
    typeof v.submitted === "boolean" &&
    (v.draft === null || draft(v.draft)),
  draft,
  receipt: (v: unknown) =>
    object(v) && string(v.id) && string(v.form_id) && string(v.submitted_at),
  responses: (v: unknown) => page(v, responseSummary),
  response: (v: unknown) =>
    responseSummary(v) &&
    object(v) &&
    definition(v.form_snapshot) &&
    Array.isArray(v.answers) &&
    v.answers.every(answer),
};
function page(value: unknown, check: (item: unknown) => boolean): boolean {
  return (
    object(value) &&
    Array.isArray(value.items) &&
    value.items.every(check) &&
    (value.next_offset === null || number(value.next_offset))
  );
}
type Kind = keyof typeof checks;
export type Results = {
  form: Form;
  forms: Page<FormSummary>;
  associations: Associations;
  audience: Page<Audience>;
  inbox: Page<InboxItem> & { unread_count: number };
  recipient: RecipientForm;
  draft: Draft;
  receipt: Receipt;
  responses: Page<ResponseSummary>;
  response: ResponseDetail;
};

let epoch = 0;
const pending = new Map<
  string,
  {
    promise: Promise<unknown>;
    controller: AbortController;
    users: number;
    timer?: ReturnType<typeof setTimeout>;
  }
>();
async function send<K extends Kind>(
  method: string,
  path: string,
  kind: K,
  body?: unknown,
  signal?: AbortSignal,
): Promise<Results[K]> {
  const generation = getSessionGeneration();
  const data = await request(method, path, body, {
    timeoutMs: 15000,
    distinguishTimeout: true,
    cache: "no-store",
    signal,
  });
  if (generation !== getSessionGeneration() || signal?.aborted)
    throw new ApiError(0, "stale_session");
  if (!checks[kind](data)) throw new ApiError(0, "bad_response");
  return data as Results[K];
}
export function feedbackRead<K extends Kind>(path: string, kind: K) {
  const key = `${getSessionGeneration()}:${epoch}:${path}:${kind}`;
  let entry = pending.get(key);
  if (!entry) {
    const controller = new AbortController();
    entry = {
      controller,
      users: 0,
      promise: send("GET", path, kind, undefined, controller.signal).finally(
        () => pending.delete(key),
      ),
    };
    pending.set(key, entry);
  }
  entry.users++;
  clearTimeout(entry.timer);
  const owned = entry;
  return {
    promise: owned.promise as Promise<Results[K]>,
    release: () => {
      owned.users--;
      if (!owned.users)
        owned.timer = setTimeout(() => {
          if (!owned.users) owned.controller.abort();
        }, 0);
    },
  };
}
export async function feedbackWrite<K extends Kind>(
  method: string,
  path: string,
  kind: K,
  body: unknown,
  signal?: AbortSignal,
) {
  epoch++;
  try {
    return await send(method, path, kind, body, signal);
  } finally {
    epoch++;
  }
}
export const adminBase = "/api/admin/feedback/forms";
export const recipientBase = "/api/feedback/forms";

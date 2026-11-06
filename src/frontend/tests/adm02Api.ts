import { expect, type Page, type Route } from "@playwright/test";
import { STUDENT, TEACHER, mockAuthApi, type User } from "./authApi";

export const FORM_ID = "a2000000-0000-4000-8000-000000000001";
export const RESPONSE_ID = "a2000000-0000-4000-8000-000000000002";
export const TIME = "2026-11-07T00:00:00Z";
export const TITLE = "Your learning feedback";
export const ROOT = "/api/admin/feedback";
export const PUBLIC = "/api/feedback";
export const MSG = {
  saved: "Draft saved. You can return to finish later.",
  initial: "Your answers will be saved as a draft as you fill in this form.",
  saving: "Saving your draft...",
  unsaved: "Your latest changes are not saved. Keep this page open and retry.",
  network: "Cannot connect to the server. Check your connection and try again.",
  timeout: "The request timed out. Check the current form before trying again.",
  unavailable:
    "The feedback service is temporarily unavailable. Try again later.",
  forbidden: "You do not have permission to access this feedback page.",
  missing: "This feedback form or response is not available.",
  limited: "Too many feedback requests. Wait before trying again.",
  conflict:
    "Your draft changed in another session. Reload the saved draft before continuing.",
  closed: "This form is closed.",
  completed: "You have already submitted feedback.",
  unexpected: "The feedback service encountered an error. Try again later.",
};

export type Answer = {
  question_id: string;
  value: null | string | string[] | number;
};
export type Question = {
  id: string;
  type: string;
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
const id = (n: number) =>
  `b2000000-0000-4000-8000-${n.toString().padStart(12, "0")}`;
export function questions(): Question[] {
  return [
    "short_answer",
    "paragraph",
    "multiple_choice",
    "dropdown",
    "checkbox",
    "linear_scale",
  ].map((type, i) => ({
    id: id(i + 1),
    type,
    prompt: [
      "One sentence",
      "Your experience",
      "Choose one",
      "Pick a topic",
      "Useful tools",
      "Rate usefulness",
    ][i],
    required: i === 0,
    options: ["multiple_choice", "dropdown", "checkbox"].includes(type)
      ? [
          { id: id(20 + i * 2), label: "First option" },
          { id: id(21 + i * 2), label: "Second option" },
        ]
      : [],
    scale:
      type === "linear_scale"
        ? { min: 0, max: 5, min_label: "Low", max_label: "High" }
        : null,
  }));
}

export function form(state = "open") {
  return {
    id: FORM_ID,
    title: TITLE,
    description: "Tell us what works.",
    association: null,
    questions: questions(),
    state,
    version: state === "draft" ? 1 : 2,
    audience_role: state === "draft" ? null : "student",
    recipient_count: state === "draft" ? 0 : 1,
    response_count: 0,
    created_at: TIME,
    updated_at: TIME,
    published_at: state === "draft" ? null : TIME,
    closed_at: state === "closed" ? TIME : null,
  };
}
export type Draft = {
  version: number;
  answers: Answer[];
  updated_at: string | null;
};
export type Step = {
  method?: string;
  path?: string;
  status?: number;
  code?: string;
  json?: unknown;
  hold?: boolean;
  abort?: boolean;
};
type Body = ReturnType<typeof form> & {
  answers: Answer[];
  draft_version: number;
  recipient_ids: string[];
};
export type Recorded = {
  method: string;
  path: string;
  body: Body;
  headers: Record<string, string>;
};

export async function setup(page: Page, user: User = STUDENT) {
  // Every API request is isolated from a developer server, including unrelated shell reads.
  await page.route("**/api/**", (route) =>
    route.fulfill({
      status: 503,
      json: {
        detail: {
          code: "test_unrelated",
          message: "Unavailable in isolated fixture",
        },
      },
    }),
  );
  const auth = await mockAuthApi(page, { user });
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  const ctx = {
    auth,
    form: form(),
    draft: { version: 0, answers: [], updated_at: null } as Draft,
    submitted: false,
    unread: true,
    requests: [] as Recorded[],
    steps: [] as Step[],
    waiting: [] as (() => void)[],
    responseAnswers: [] as Answer[],
    of(method: string, suffix = "") {
      return this.requests.filter(
        (r) => r.method === method && (!suffix || r.path.endsWith(suffix)),
      );
    },
    release() {
      this.waiting.splice(0).forEach((resolve) => resolve());
    },
  };
  const handler = async (route: Route) => {
    const req = route.request(),
      url = new URL(req.url()),
      path = url.pathname,
      method = req.method();
    let body = {} as Body;
    try {
      body = req.postDataJSON();
    } catch {
      /* GET */
    }
    ctx.requests.push({ method, path, body, headers: req.headers() });
    const at = ctx.steps.findIndex(
      (step) =>
        (!step.method || step.method === method) &&
        (!step.path || path.endsWith(step.path)),
    );
    const step = at < 0 ? undefined : ctx.steps.splice(at, 1)[0];
    if (step?.hold)
      await new Promise<void>((resolve) => ctx.waiting.push(resolve));
    if (step?.abort) {
      await route.abort("connectionrefused").catch(() => undefined);
      return;
    }
    const reply = async (json: unknown, status = 200) =>
      route
        .fulfill({ status, json, headers: { "cache-control": "no-store" } })
        .catch(() => undefined);
    if (step?.status) {
      await reply(
        {
          detail: {
            code: step.code,
            message: "Do not render arbitrary private backend details",
          },
        },
        step.status,
      );
      return;
    }
    if (step?.json !== undefined) {
      await reply(step.json);
      return;
    }
    if (path === ROOT + "/associations") {
      await reply({
        features: [{ id: "ADM-02", label: "Targeted feedback forms" }],
        lessons: [],
        truncated: false,
      });
      return;
    }
    if (path.endsWith("/audience")) {
      await reply({
        items: [
          {
            id:
              url.searchParams.get("role") === "teacher"
                ? TEACHER.id
                : STUDENT.id,
            display_name:
              url.searchParams.get("role") === "teacher"
                ? TEACHER.display_name
                : STUDENT.display_name,
            role: url.searchParams.get("role") ?? "student",
          },
        ],
        next_offset: null,
      });
      return;
    }
    if (path === ROOT + "/forms" && method === "GET") {
      await reply({
        items: [{ ...ctx.form, questions: undefined, description: undefined }],
        next_offset: null,
      });
      return;
    }
    if (path === ROOT + "/forms" && method === "POST") {
      ctx.form = {
        ...ctx.form,
        ...body,
        state: "draft",
        version: 1,
        audience_role: null,
        recipient_count: 0,
      };
      await reply(ctx.form, 201);
      return;
    }
    if (path.endsWith("/publish")) {
      ctx.form = {
        ...ctx.form,
        state: "open",
        version: ctx.form.version + 1,
        recipient_count: body.recipient_ids.length,
        audience_role: body.audience_role,
        published_at: TIME,
      };
      await reply(ctx.form);
      return;
    }
    if (path.endsWith("/close")) {
      ctx.form = {
        ...ctx.form,
        state: "closed",
        version: ctx.form.version + 1,
        closed_at: TIME,
      };
      await reply(ctx.form);
      return;
    }
    if (path === `${ROOT}/forms/${FORM_ID}`) {
      if (method === "PUT")
        ctx.form = { ...ctx.form, ...body, version: ctx.form.version + 1 };
      await reply(ctx.form);
      return;
    }
    if (path === `${ROOT}/forms/${FORM_ID}/responses`) {
      await reply({
        items: ctx.submitted
          ? [
              {
                id: RESPONSE_ID,
                form_id: FORM_ID,
                respondent: { id: user.id, display_name: user.display_name },
                submitted_at: TIME,
              },
            ]
          : [],
        next_offset: null,
      });
      return;
    }
    if (path === `${ROOT}/forms/${FORM_ID}/responses/${RESPONSE_ID}`) {
      await reply({
        id: RESPONSE_ID,
        form_id: FORM_ID,
        respondent: { id: STUDENT.id, display_name: STUDENT.display_name },
        submitted_at: TIME,
        form_snapshot: {
          title: TITLE,
          description: ctx.form.description,
          association: null,
          questions: ctx.form.questions,
        },
        answers: ctx.responseAnswers,
      });
      return;
    }
    if (path === PUBLIC + "/inbox") {
      await reply({
        items: [
          {
            id: id(99),
            form_id: FORM_ID,
            title: TITLE,
            created_at: TIME,
            read_at: ctx.unread ? null : TIME,
            state: ctx.form.state,
            submitted: ctx.submitted,
            response_status: ctx.submitted
              ? "completed"
              : ctx.form.state === "closed"
                ? "closed"
                : ctx.draft.version
                  ? "draft"
                  : "not_started",
          },
        ],
        next_offset: null,
        unread_count: ctx.unread ? 1 : 0,
      });
      return;
    }
    if (path === `${PUBLIC}/forms/${FORM_ID}`) {
      ctx.unread = false;
      await reply({
        id: FORM_ID,
        title: ctx.form.title,
        description: ctx.form.description,
        association: null,
        state: ctx.form.state,
        submitted: ctx.submitted,
        questions:
          ctx.submitted || ctx.form.state === "closed"
            ? []
            : ctx.form.questions,
        draft: ctx.submitted || ctx.form.state === "closed" ? null : ctx.draft,
      });
      return;
    }
    if (path.endsWith("/draft")) {
      ctx.draft = {
        version: body.version + 1,
        answers: body.answers,
        updated_at: TIME,
      };
      await reply(ctx.draft);
      return;
    }
    if (path === `${PUBLIC}/forms/${FORM_ID}/responses`) {
      ctx.submitted = true;
      ctx.responseAnswers = body.answers;
      ctx.draft = { version: 0, answers: [], updated_at: null };
      await reply(
        { id: RESPONSE_ID, form_id: FORM_ID, submitted_at: TIME },
        201,
      );
      return;
    }
    await reply(
      { detail: { code: "feedback_not_found", message: MSG.missing } },
      404,
    );
  };
  await page.route(
    (url) =>
      url.pathname.startsWith(ROOT + "/") ||
      url.pathname.startsWith(PUBLIC + "/"),
    handler,
  );
  return ctx;
}

export async function choose(page: Page, label: string, option: string) {
  const control = page.getByRole("combobox", { name: label, exact: true });
  if ((await control.evaluate((el) => el.tagName)) === "SELECT")
    await control.selectOption({ label: option });
  else {
    await control.click();
    await page.getByRole("option", { name: option, exact: true }).click();
  }
}
export function firstAnswer(page: Page) {
  return page.getByRole("textbox", { name: "1. One sentence", exact: true });
}
export async function recipientReady(
  page: Page,
  role: "student" | "teacher" = "student",
) {
  const ctx = await setup(page, role === "teacher" ? TEACHER : STUDENT);
  await page.goto(`/${role}/feedback/${FORM_ID}`);
  await expect(firstAnswer(page)).toBeVisible();
  return ctx;
}
export const status = (page: Page, message: string) =>
  page.getByRole("status").filter({ hasText: message });
export const alert = (page: Page, message: string) =>
  page.getByRole("alert").filter({ hasText: message });

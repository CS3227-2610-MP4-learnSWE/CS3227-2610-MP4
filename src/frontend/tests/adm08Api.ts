import { expect, type Page, type Route } from "@playwright/test";
import { ADMIN, STUDENT, TEACHER, mockAuthApi, type User } from "./authApi";
import { FORM_ID, RESPONSE_ID, TITLE, TIME, form, questions } from "./adm02Api";
import { analysis, uuid as analysisUuid, type Analysis } from "./adm03Api";
import { samplePreview, type Preview } from "./adm04Api";

/**
 * ADM-08 stateful mock of the feedback hub's whole API surface (ADM-02, ADM-03, ADM-04 admin endpoints and the new
 * follow-up count endpoint). Reuses the existing builders (form, analysis, samplePreview). Contract:
 * workflow/specs/ADM-08/plan.md. Every request is recorded; replies are scriptable once or persistently.
 */
export { ADMIN, STUDENT, TEACHER, FORM_ID, RESPONSE_ID, TITLE, TIME };
export const HUB = "/admin/feedback-hub";
export const FEEDBACK = "/api/admin/feedback";
export const MESSAGING = "/api/admin/messaging";
export const COUNT_FORMS = `${FEEDBACK}/forms`;
export const COUNT_ANALYSES = `${FEEDBACK}/analyses`;
export const COUNT_FOLLOWUP = `${MESSAGING}/followup-counts`;
export const SECOND_FORM_ID = "a2000000-0000-4000-8000-0000000000f2";
export const THIRD_FORM_ID = "a2000000-0000-4000-8000-0000000000f3";
export const DRAFT_FORM_ID = "a2000000-0000-4000-8000-0000000000f4";
export const REVIEW_ID = "a4000000-0000-4000-8000-000000000001";

export const MSG = {
  expired: "Your session has expired. Sign in again.",
  forbidden: "You do not have permission to access this feedback page.",
  limited: "Too many feedback requests. Wait before trying again.",
  unexpected: "The feedback service encountered an error. Try again later.",
  unavailable: "The feedback service is temporarily unavailable. Try again later.",
  network: "Cannot connect to the server. Check your connection and try again.",
  timeout: "The request timed out. Check the current form before trying again.",
  missing: "This feedback form or response is not available.",
  notFound: "This Feedback hub page does not exist.",
  notAvailableForAnalysis:
    "The linked form is not available for analysis. Choose a form below.",
  chooserEmpty:
    "No published feedback forms yet. Publish a form on the Forms tab to collect responses.",
  chooserTruncated:
    "Showing the first 100 forms. Open an older form from the Forms tab, then choose Review responses.",
  followUpNote:
    "To reply to one person, open their response on the Responses tab and choose Respond to feedback.",
  muted:
    "Create forms, review responses, analyse feedback and follow up with respondents, all in one place.",
  discard: "Discard unsaved changes?",
};

export type Step = {
  method?: string;
  /** path suffix */
  suffix?: string;
  /** substring that the query string must contain */
  query?: string;
  status?: number;
  code?: string;
  json?: unknown;
  hold?: boolean;
  abort?: boolean;
  /** keep the step for every later matching request */
  persist?: boolean;
};
export type Recorded = {
  method: string;
  path: string;
  search: string;
  query: URLSearchParams;
  body: Record<string, unknown>;
};
export type FormRow = ReturnType<typeof form>;

export const formId = (n: number) =>
  `a2000000-0000-4000-8000-${(n + 5000).toString().padStart(12, "0")}`;

/** A form with a given state, response count and title (default the ADM-02 sample). */
export function makeForm(
  id: string,
  title: string,
  state: "draft" | "open" | "closed",
  responses = 0,
): FormRow {
  return { ...form(state), id, title, response_count: responses };
}
export const analysisFor = (
  n: number,
  state: "running" | "complete" | "failed" = "complete",
  over: Record<string, unknown> = {},
): Analysis => analysis(n, state, { form_id: FORM_ID, form_title: TITLE, ...over });

export interface Options {
  user?: User | null;
  forms?: FormRow[];
  analyses?: Analysis[];
  followUp?: number;
  /** unanswered follow-up decrements per sent feedback_response reply */
  responseIds?: string[];
}

export async function setup(page: Page, opts: Options = {}) {
  const user = opts.user === undefined ? ADMIN : opts.user;
  await page.route("**/api/**", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: { code: "test_unrelated", message: "Unrelated fixture" } },
    }),
  );
  const auth = await mockAuthApi(page, { user });
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  const ctx = {
    auth,
    requests: [] as Recorded[],
    steps: [] as Step[],
    waiting: [] as (() => void)[],
    forms: opts.forms ?? [makeForm(FORM_ID, TITLE, "open", 2)],
    analyses: [...(opts.analyses ?? [])] as Analysis[],
    followUp: opts.followUp ?? 0,
    responses: opts.responseIds ?? [RESPONSE_ID],
    previews: new Map<string, Preview>(),
    receipts: new Map<string, Record<string, unknown>>(),
    created: 0,
    createdAnalyses: 0,
    release() {
      this.waiting.splice(0).forEach((resolve) => resolve());
    },
    /** requests to the feedback and messaging admin APIs only */
    api() {
      return this.requests.filter(
        (r) => r.path.startsWith(FEEDBACK) || r.path.startsWith(MESSAGING),
      );
    },
    of(method: string, suffix = "", query = "") {
      return this.requests.filter(
        (r) =>
          r.method === method &&
          (!suffix || r.path.endsWith(suffix)) &&
          (!query || r.search.includes(query)),
      );
    },
    /** the three count requests, identified by their exact query strings */
    formsCountGets() {
      return this.requests.filter(
        (r) =>
          r.method === "GET" &&
          r.path === COUNT_FORMS &&
          r.search === "?limit=100&offset=0",
      );
    },
    analysesCountGets() {
      return this.requests.filter(
        (r) =>
          r.method === "GET" &&
          r.path === COUNT_ANALYSES &&
          r.search === "?limit=50&offset=0",
      );
    },
    followUpGets() {
      return this.requests.filter(
        (r) => r.method === "GET" && r.path === COUNT_FOLLOWUP,
      );
    },
    mark() {
      return this.requests.length;
    },
    since(mark: number) {
      return this.requests.slice(mark);
    },
  };
  const detailOf = (id: string) => ctx.forms.find((f) => f.id === id);
  const summary = (f: FormRow) => ({
    ...f,
    questions: undefined,
    description: undefined,
  });
  const notFound = (code: string, message: string) => ({
    status: 404,
    json: { detail: { code, message } },
  });
  const handler = async (route: Route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    const method = req.method();
    let body: Record<string, unknown> = {};
    try {
      body = req.postDataJSON() ?? {};
    } catch {
      /* no body */
    }
    ctx.requests.push({
      method,
      path,
      search: url.search,
      query: url.searchParams,
      body,
    });
    const at = ctx.steps.findIndex(
      (s) =>
        (!s.method || s.method === method) &&
        (!s.suffix || path.endsWith(s.suffix)) &&
        (!s.query || url.search.includes(s.query)),
    );
    const step =
      at < 0
        ? undefined
        : ctx.steps[at].persist
          ? ctx.steps[at]
          : ctx.steps.splice(at, 1)[0];
    if (step?.hold) await new Promise<void>((r) => ctx.waiting.push(r));
    if (step?.abort) {
      await route.abort("connectionrefused").catch(() => undefined);
      return;
    }
    const send = (status: number, json?: unknown) =>
      route
        .fulfill(
          status === 204
            ? { status }
            : { status, json, headers: { "cache-control": "no-store" } },
        )
        .catch(() => undefined);
    if (step?.status) {
      await send(
        step.status,
        step.json ?? {
          detail: {
            code: step.code,
            message: "Do not render arbitrary private backend details",
            retry_after_seconds: 1,
          },
        },
      );
      return;
    }
    if (step?.json !== undefined) {
      await send(200, step.json);
      return;
    }
    const limit = Number(url.searchParams.get("limit") ?? 20);
    const offset = Number(url.searchParams.get("offset") ?? 0);
    const page_ = <T,>(rows: T[]) => ({
      items: rows.slice(offset, offset + limit),
      next_offset: offset + limit < rows.length ? offset + limit : null,
    });
    const rest = path.startsWith(FEEDBACK) ? path.slice(FEEDBACK.length) : "";
    if (path === COUNT_FOLLOWUP) {
      await send(200, { unanswered_responses: ctx.followUp });
      return;
    }
    if (rest === "/associations") {
      await send(200, {
        features: [{ id: "ADM-02", label: "Targeted feedback forms" }],
        lessons: [],
        truncated: false,
      });
      return;
    }
    if (rest === "/forms" && method === "GET") {
      await send(200, page_(ctx.forms.map(summary)));
      return;
    }
    if (rest === "/forms" && method === "POST") {
      const made = {
        ...form("draft"),
        ...body,
        id: formId(++ctx.created),
        state: "draft",
        version: 1,
        response_count: 0,
      } as FormRow;
      ctx.forms.unshift(made);
      await send(201, made);
      return;
    }
    const formMatch = /^\/forms\/([^/]+)(\/.*)?$/.exec(rest);
    if (formMatch) {
      const f = detailOf(formMatch[1]);
      const sub = formMatch[2] ?? "";
      if (!f) {
        const nf = notFound("feedback_not_found", MSG.missing);
        await send(nf.status, nf.json);
        return;
      }
      if (sub === "" && method === "GET") return void (await send(200, f));
      if (sub === "" && method === "PUT") {
        Object.assign(f, body, { version: f.version + 1 });
        return void (await send(200, f));
      }
      if (sub === "/audience") {
        return void (await send(200, {
          items: [
            {
              id: STUDENT.id,
              display_name: STUDENT.display_name,
              role: "student",
            },
          ],
          next_offset: null,
        }));
      }
      if (sub === "/publish") {
        Object.assign(f, {
          state: "open",
          version: f.version + 1,
          recipient_count: (body.recipient_ids as string[] | undefined)?.length ?? 1,
          audience_role: body.audience_role ?? "student",
          published_at: TIME,
        });
        return void (await send(200, f));
      }
      if (sub === "/close") {
        Object.assign(f, { state: "closed", version: f.version + 1, closed_at: TIME });
        return void (await send(200, f));
      }
      if (sub === "/response-count") {
        return void (await send(200, { form_id: f.id, count: f.response_count }));
      }
      if (sub === "/responses" && method === "GET") {
        const rows = ctx.responses.slice(0, f.response_count).map((rid) => ({
          id: rid,
          form_id: f.id,
          respondent: { id: STUDENT.id, display_name: STUDENT.display_name },
          submitted_at: TIME,
        }));
        return void (await send(200, page_(rows)));
      }
      const resp = /^\/responses\/([^/]+)$/.exec(sub);
      if (resp) {
        const known = ctx.responses.includes(resp[1]) && f.response_count > 0;
        if (method === "DELETE") {
          if (!known) {
            const nf = notFound(
              "feedback_response_not_found",
              "This response was not found. It may already have been deleted, or it does not belong to this form.",
            );
            return void (await send(nf.status, nf.json));
          }
          f.response_count -= 1;
          ctx.followUp = Math.max(0, ctx.followUp - 1);
          return void (await send(204));
        }
        if (!known) {
          const nf = notFound("feedback_not_found", MSG.missing);
          return void (await send(nf.status, nf.json));
        }
        return void (await send(200, {
          id: resp[1],
          form_id: f.id,
          respondent: { id: STUDENT.id, display_name: STUDENT.display_name },
          submitted_at: TIME,
          form_snapshot: {
            title: f.title,
            description: f.description,
            association: null,
            questions: questions(),
          },
          answers: [],
        }));
      }
    }
    if (rest === "/analyses" && method === "GET") {
      await send(
        200,
        page_(
          ctx.analyses.map((a) => ({
            id: a.id,
            form_id: a.form_id,
            form_title: a.form_title,
            created_at: a.created_at,
            response_count: a.response_count,
            ai_status: a.ai.status,
          })),
        ),
      );
      return;
    }
    if (rest === "/analyses" && method === "POST") {
      const made = analysisFor(900 + ++ctx.createdAnalyses, "running", {
        response_count: body.select_all
          ? (detailOf(String(body.form_id))?.response_count ?? 1)
          : ((body.response_ids as string[] | undefined)?.length ?? 1),
      });
      ctx.analyses.unshift(made);
      await send(201, made);
      return;
    }
    const an = /^\/analyses\/([^/]+)(?:\/responses\/(R\d+))?$/.exec(rest);
    if (an) {
      const found = ctx.analyses.find((a) => a.id === an[1]);
      if (!found) {
        const nf = notFound(
          "analysis_not_found",
          "That analysis is not available. It does not exist or is not in your history.",
        );
        return void (await send(nf.status, nf.json));
      }
      if (method === "DELETE") {
        ctx.analyses.splice(ctx.analyses.indexOf(found), 1);
        return void (await send(204));
      }
      if (an[2]) {
        return void (await send(200, {
          label: an[2],
          response: {
            id: RESPONSE_ID,
            form_id: FORM_ID,
            respondent: { id: STUDENT.id, display_name: STUDENT.display_name },
            submitted_at: TIME,
            form_snapshot: {
              title: TITLE,
              description: "",
              association: null,
              questions: [],
            },
            answers: [],
          },
        }));
      }
      return void (await send(200, found));
    }
    if (path === `${MESSAGING}/recipients`) {
      await send(200, {
        items: [
          { id: STUDENT.id, display_name: STUDENT.display_name, role: "student" },
        ],
        page: 1,
        page_size: 50,
        total: 1,
      });
      return;
    }
    if (/\/feedback-responses\/[^/]+\/recipient$/.test(path)) {
      await send(200, {
        response_id: RESPONSE_ID,
        recipient: {
          id: STUDENT.id,
          display_name: STUDENT.display_name,
          role: "student",
        },
      });
      return;
    }
    if (path === `${MESSAGING}/previews` && method === "POST") {
      const value: Preview = {
        ...samplePreview(`a4000000-0000-4000-8000-${(ctx.previews.size + 1).toString().padStart(12, "0")}`),
        kind: String(body.kind),
        response_id: body.kind === "feedback_response" ? RESPONSE_ID : null,
        audience_mode:
          body.kind === "feedback_response" ? null : String(body.audience_mode),
        subject: String(body.subject).trim(),
        body: String(body.body).trim(),
      };
      ctx.previews.set(value.id, value);
      await send(201, value);
      return;
    }
    if (/\/previews\/[^/]+\/send$/.test(path)) {
      const value = ctx.previews.get(path.split("/").at(-2)!);
      if (!value) {
        await send(404, { detail: { code: "PREVIEW_NOT_FOUND", message: "x" } });
        return;
      }
      if (!ctx.receipts.has(value.id)) {
        ctx.receipts.set(value.id, {
          message_id: `a4000000-0000-4000-8000-${(200 + ctx.receipts.size).toString().padStart(12, "0")}`,
          preview_id: value.id,
          kind: value.kind,
          recipient_count: value.recipient_count,
          sent_at: TIME,
        });
        if (value.kind === "feedback_response")
          ctx.followUp = Math.max(0, ctx.followUp - 1);
      }
      await send(200, ctx.receipts.get(value.id));
      return;
    }
    if (/\/previews\/[^/]+$/.test(path)) {
      const id = path.split("/").at(-1)!;
      await send(200, {
        preview: ctx.previews.get(id) ?? { ...samplePreview(id) },
        receipt: ctx.receipts.get(id) ?? null,
      });
      return;
    }
    await send(404, {
      detail: { code: "feedback_not_found", message: MSG.missing },
    });
  };
  await page.route(`**${FEEDBACK}/**`, handler);
  await page.route(`**${MESSAGING}/**`, handler);
  return ctx;
}
export type Ctx = Awaited<ReturnType<typeof setup>>;

// ---- locators shared by the specs ----
export const tablist = (page: Page) =>
  page.getByRole("tablist", { name: "Feedback sections", exact: true });
export const tab = (page: Page, name: string) =>
  tablist(page).getByRole("tab", { name, exact: true });
export const TABS = ["Forms", "Responses", "Analysis", "Follow-up"] as const;
export const heading = (page: Page, name: string, level = 1) =>
  page.getByRole("heading", { name, exact: true, level });
export const alertWith = (page: Page, text: string) =>
  page.getByRole("alert").filter({ hasText: text });
export const statusWith = (page: Page, text: string) =>
  page.getByRole("status").filter({ hasText: text });
export const link = (page: Page, name: string) =>
  page.getByRole("link", { name, exact: true });
export const button = (page: Page, name: string) =>
  page.getByRole("button", { name, exact: true });

/** Open a hub URL and wait for the tab bar. */
export async function open(page: Page, path: string) {
  await page.goto(path);
  await expect(tablist(page)).toBeVisible();
}
/** Wait until the count requests of a mount have all been seen. */
export async function settle(ctx: Ctx) {
  await expect
    .poll(
      () =>
        ctx.formsCountGets().length +
        ctx.analysesCountGets().length +
        ctx.followUpGets().length,
    )
    .toBeGreaterThanOrEqual(3);
}
/** Selected tab name or null. */
export async function selectedTab(page: Page) {
  const selected = tablist(page).getByRole("tab", { selected: true });
  return (await selected.count()) === 1 ? await selected.innerText() : null;
}
export const noStorage = (page: Page) =>
  page.evaluate(() => localStorage.length + sessionStorage.length);

/** Read what a native or custom form picker currently shows. */
export async function pickerText(page: Page, name = "Feedback form") {
  return page.getByRole("combobox", { name }).evaluate((el) => {
    if (el instanceof HTMLSelectElement)
      return el.selectedOptions[0]?.textContent ?? "";
    return el.textContent ?? "";
  });
}
export async function choosePicker(page: Page, name: string, option: string) {
  const control = page.getByRole("combobox", { name, exact: true });
  if ((await control.evaluate((el) => el.tagName)) === "SELECT")
    await control.selectOption({ label: option });
  else {
    await control.click();
    await page.getByRole("option", { name: option, exact: true }).click();
  }
}
export { analysisUuid };

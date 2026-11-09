import { type Page, type Route } from "@playwright/test";
import { ADMIN, mockAuthApi, type User } from "./authApi";

export const ROOT = "/api/admin/feedback";
export const FORM_ID = "a3000000-0000-4000-8000-000000000001";
export const TITLE = "Course feedback";
export const TIME = "2026-11-07T10:30:00Z";
export const uuid = (n: number) =>
  `a3000000-0000-4000-8000-${(n + 100).toString().padStart(12, "0")}`;

// Exact message texts copied from workflow/specs/ADM-03/spec.md "Failure messages".
export const MSG = {
  selection:
    "No responses are selected. Select at least one response, or use Select all, then generate the analysis.",
  expired: "Your session has expired. Sign in again.",
  forbidden:
    "You do not have access to this page. Only admin accounts can use feedback analysis.",
  analysisNotFound:
    "That analysis is not available. It does not exist or is not in your history.",
  evidenceNotFound:
    "This response cannot be shown. It was deleted, or the reference is not part of this analysis.",
  inProgress:
    "Another analysis started 12 seconds ago is still running its AI step. A running AI step finishes or fails within 780 seconds. Wait for it, then generate again.",
  progressNetwork:
    "Could not reach the server while checking the analysis progress. The analysis is saved and may still be running. Press Retry to check again.",
  progressUnreadable: (status: number) =>
    `The server answered the progress check with an unreadable reply (HTTP ${status}). The analysis is saved. Press Retry to check again.`,
  stoppedWaiting:
    "Stopped waiting after 810 seconds. The server may still be working. Reload this page to check again.",
  load: (what: string) =>
    `Could not reach the server while loading ${what}. Check your connection and press Retry.`,
  abort: (what: string) =>
    `The server did not answer within 15 seconds while loading ${what}. Press Retry.`,
  generateNetwork:
    "Could not reach the server while starting the analysis. If it did start it will appear in Previous analyses. Press Generate analysis again; repeating it will not start a second copy.",
  generateAbort:
    "The server did not answer within 15 seconds while starting the analysis. If it did start it will appear in Previous analyses. Press Generate analysis again; repeating it will not start a second copy.",
  deleteDone:
    "Analysis deleted. The original feedback responses and forms were not changed.",
  delete404:
    "This analysis was already deleted or is not in your history. The list has been refreshed.",
  deleteNetwork:
    "Could not reach the server while deleting the analysis. It was not confirmed as deleted. Press Delete permanently to try again.",
  deleteAbort:
    "The server did not answer within 15 seconds while deleting the analysis. It may or may not be deleted. Press Delete permanently again; if it was already deleted you will be told so.",
  deleteRunning:
    "This analysis cannot be deleted yet: its AI step has been running for 100 seconds. It finishes or is marked interrupted within 260 seconds (the limit is 780 seconds). Delete it after that.",
  deleteInternal:
    "An unexpected server error occurred while deleting the analysis. The cause was not an invalid request. Reference abc123 identifies it in the server logs.",
  aiTimeout:
    "The AI service did not answer within 15 seconds (after up to 2 attempts) while processing batch 2 of 3. The statistics are unaffected. Start a new analysis to run the AI part again.",
  aiRate:
    "The AI limit of 20 requests per minute was reached while processing batch 3 of 6. Try again in 41 seconds.",
  aiInvalid:
    "The AI reply for merging themes was rejected because a theme had no supporting responses. No AI result was saved. Start a new analysis.",
  aiInterrupted:
    "The AI step was interrupted: it had been running for 900 seconds without finishing (the limit is 780 seconds), probably because the server restarted. It had finished 1 of 3 steps. The statistics are unaffected. Start a new analysis.",
};

export type Step = {
  method?: string;
  suffix?: string;
  status?: number;
  code?: string;
  message?: string;
  json?: unknown;
  raw?: string;
  hold?: boolean;
  abort?: boolean;
};
export type Recorded = {
  method: string;
  path: string;
  query: URLSearchParams;
  body: Record<string, unknown>;
};

const scaleQuestion = {
  question_id: uuid(501),
  prompt: "How clear were the deadlines?",
  kind: "scale",
  answered: 120,
  skipped: 17,
  min: 1,
  max: 5,
  min_label: "Unclear",
  max_label: "Clear",
  mean: 3.4,
  median: 4.0,
  distribution: [1, 2, 3, 4, 5].map((v, i) => ({
    label: String(v),
    count: [10, 20, 30, 40, 20][i],
    percent: [8.3, 16.7, 25.0, 33.3, 16.7][i],
  })),
};
const choiceQuestion = {
  question_id: uuid(502),
  prompt: "Which tools helped?",
  kind: "multi",
  answered: 100,
  skipped: 37,
  options: [
    { option_id: uuid(601), label: "Slides", count: 70, percent: 70.0 },
    { option_id: uuid(602), label: "Videos", count: 40, percent: 40.0 },
  ],
};
const textQuestion = {
  question_id: uuid(503),
  prompt: "What should change?",
  kind: "text",
  answered: 90,
  skipped: 47,
};

export const COMPLETE_RESULT = {
  summary: "Students want clearer deadlines.",
  themes: [
    {
      title: "Deadlines",
      description: "Unclear due dates.",
      evidence: ["R1", "R3"],
    },
  ],
  suggestions: [
    {
      text: "Show due dates on the dashboard.",
      basis: "feedback",
      evidence: ["R1"],
    },
    { text: "Add a weekly digest.", basis: "ai", evidence: [] },
  ],
};

export type Analysis = ReturnType<typeof analysis>;
export function analysis(
  n = 1,
  state: "running" | "complete" | "failed" = "running",
  over: Record<string, unknown> = {},
) {
  const base = {
    id: uuid(n),
    form_id: FORM_ID,
    form_title: TITLE,
    created_at: TIME,
    response_count: 137,
    mode: "select_all",
    expected_count: 137,
    labels: ["R1", "R2", "R3"].map((label) => ({
      label,
      submitted_at: TIME,
    })),
    aggregates: [scaleQuestion, choiceQuestion, textQuestion],
    free_text: { total: 12, used: 12 },
    ai: {
      status: state,
      progress: {
        done: state === "complete" ? 3 : 1,
        total: 3,
        step:
          state === "running"
            ? { kind: "batch", index: 2, total: 2 }
            : null,
      },
      result: state === "complete" ? COMPLETE_RESULT : null,
      error:
        state === "failed"
          ? {
              code: "ai_timeout",
              message: MSG.aiTimeout,
              step: { kind: "batch", index: 2, total: 3 },
              details: { timeout_seconds: 15, attempts: 2 },
            }
          : null,
      completed_at: state === "running" ? null : TIME,
    },
  };
  return { ...base, ...over } as typeof base;
}

export const person = (i: number) => ({
  id: `u-${i}`,
  display_name: `Person ${i}`,
});

export async function setup(
  page: Page,
  opts: { user?: User | null; responses?: number; analyses?: Analysis[] } = {},
) {
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
    total: opts.responses ?? 137,
    analyses: [...(opts.analyses ?? [])] as Analysis[],
    /** per-analysis queue of states returned by successive GETs (the last one repeats) */
    script: new Map<string, Analysis[]>(),
    created: 0,
    release() {
      this.waiting.splice(0).forEach((r) => r());
    },
    of(method: string, suffix = "") {
      return this.requests.filter(
        (r) => r.method === method && (!suffix || r.path.endsWith(suffix)),
      );
    },
    analysesCalls() {
      return this.requests.filter(
        (r) => r.method === "GET" && r.path === `${ROOT}/analyses`,
      );
    },
  };
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
    ctx.requests.push({ method, path, query: url.searchParams, body });
    const index = ctx.steps.findIndex(
      (s) =>
        (!s.method || s.method === method) &&
        (!s.suffix || path.endsWith(s.suffix)),
    );
    const step = index >= 0 ? ctx.steps.splice(index, 1)[0] : undefined;
    if (step?.hold) await new Promise<void>((r) => ctx.waiting.push(r));
    if (step?.abort) {
      await route.abort("connectionrefused");
      return;
    }
    if (step?.raw !== undefined) {
      await route
        .fulfill({
          status: step.status ?? 502,
          contentType: "text/html",
          body: step.raw,
        })
        .catch(() => undefined);
      return;
    }
    if (step?.status) {
      await route
        .fulfill({
          status: step.status,
          json: step.json ?? {
            detail: { code: step.code, message: step.message ?? "x" },
          },
        })
        .catch(() => undefined);
      return;
    }
    let status = 200;
    let json: unknown = undefined;
    const rest = path.slice(ROOT.length);
    if (rest === "/forms") {
      json = {
        items: [{ id: FORM_ID, title: TITLE, state: "open", response_count: ctx.total }],
        next_offset: null,
      };
    } else if (rest === `/forms/${FORM_ID}/response-count`) {
      json = { form_id: FORM_ID, count: ctx.total };
    } else if (rest === `/forms/${FORM_ID}/responses`) {
      const limit = Number(url.searchParams.get("limit") ?? 20);
      const offset = Number(url.searchParams.get("offset") ?? 0);
      const items = [];
      for (let i = offset; i < Math.min(ctx.total, offset + limit); i++)
        items.push({
          id: uuid(1000 + i),
          form_id: FORM_ID,
          respondent: person(i + 1),
          submitted_at: TIME,
        });
      json = {
        items,
        next_offset: offset + limit < ctx.total ? offset + limit : null,
      };
    } else if (rest === "/analyses" && method === "GET") {
      const limit = Number(url.searchParams.get("limit") ?? 20);
      const offset = Number(url.searchParams.get("offset") ?? 0);
      const slice = ctx.analyses.slice(offset, offset + limit);
      json = {
        items: slice.map((a) => ({
          id: a.id,
          form_id: a.form_id,
          form_title: a.form_title,
          created_at: a.created_at,
          response_count: a.response_count,
          ai_status: a.ai.status,
        })),
        next_offset:
          offset + limit < ctx.analyses.length ? offset + limit : null,
      };
    } else if (rest === "/analyses" && method === "POST") {
      status = 201;
      const made = analysis(++ctx.created + 900, "running", {
        response_count: body.select_all ? ctx.total : (body.response_ids as string[]).length,
      });
      ctx.analyses.unshift(made);
      json = made;
    } else if (/^\/analyses\/[^/]+$/.test(rest)) {
      const id = rest.split("/")[2];
      if (method === "DELETE") {
        const at = ctx.analyses.findIndex((a) => a.id === id);
        if (at < 0) {
          status = 404;
          json = { detail: { code: "analysis_not_found", message: MSG.analysisNotFound } };
        } else {
          ctx.analyses.splice(at, 1);
          await route.fulfill({ status: 204 }).catch(() => undefined);
          return;
        }
      } else {
        const queue = ctx.script.get(id);
        const found = queue
          ? (queue.length > 1 ? queue.shift() : queue[0])
          : ctx.analyses.find((a) => a.id === id);
        if (!found) {
          status = 404;
          json = { detail: { code: "analysis_not_found", message: MSG.analysisNotFound } };
        } else json = found;
      }
    } else if (/^\/analyses\/[^/]+\/responses\/R\d+$/.test(rest)) {
      const label = rest.split("/")[4];
      json = {
        label,
        response: {
          id: uuid(1000),
          form_id: FORM_ID,
          respondent: person(1),
          submitted_at: TIME,
          form_snapshot: { title: TITLE, description: "", association: null, questions: [] },
          answers: [],
        },
      };
    } else {
      throw new Error(`Unexpected contract request ${method} ${path}`);
    }
    await route
      .fulfill({ status, json, headers: { "cache-control": "no-store" } })
      .catch(() => undefined);
  };
  await page.route(`**${ROOT}/**`, handler);
  return ctx;
}

export type Ctx = Awaited<ReturnType<typeof setup>>;

export async function chooseForm(page: Page) {
  await page.getByRole("combobox", { name: "Feedback form" }).click();
  await page.getByRole("option", { name: TITLE }).click();
}

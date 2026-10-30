import type { Page, Route } from "@playwright/test";

/**
 * Mock of the STU-03 companion endpoint (contract: workflow/specs/STU-03/plan.md,
 * POST /api/companion/messages). Records every request and lets a test script
 * replies, failures and held (pending) requests. No backend or model is used.
 */

export const COMPANION_PATH = "/api/companion/messages";

export interface CompanionRequestBody {
  message: string;
  history: { role: "user" | "assistant"; text: string }[];
  context: {
    page: "practice" | "other";
    set_id?: string | null;
    attempt_id?: string | null;
    label?: string | null;
  };
}

export interface CompanionReply {
  status?: number;
  json?: unknown;
  /** Raw body (for non-JSON replies). */
  body?: string;
  /** Simulate an unreachable backend. */
  abort?: boolean;
  /** Do not answer until `mock.release()`, then answer with `json` (or the default). */
  hold?: boolean;
}

export interface RecordedCompanionRequest {
  method: string;
  headers: Record<string, string>;
  body: CompanionRequestBody;
  raw: string | null;
}

/** A successful reply body. */
export function companionOk(
  reply: string,
  mode: "hint" | "explain" | "help" = "hint",
  withheld = false,
): CompanionReply {
  return { status: 200, json: { reply, mode, withheld } };
}

/** A standard error body; `message` carries a marker the widget must not show. */
export function companionError(
  status: number,
  code: string,
  extra: Record<string, unknown> = {},
): CompanionReply {
  return {
    status,
    json: {
      detail: { code, message: `RAW-SERVER-TEXT ${code}`, ...extra },
    },
  };
}

export class CompanionApiMock {
  readonly requests: RecordedCompanionRequest[] = [];
  private readonly queue: CompanionReply[] = [];
  private readonly waiting: (() => void)[] = [];
  private counter = 0;

  /** Queue scripted replies, consumed in order; afterwards the default reply is used. */
  script(...replies: CompanionReply[]) {
    this.queue.push(...replies);
  }
  get count() {
    return this.requests.length;
  }
  get last() {
    return this.requests[this.requests.length - 1];
  }
  release() {
    this.waiting.splice(0).forEach((resolve) => resolve());
  }

  /** Default reply: numbered, so a test can tell which answer is on screen. */
  private defaultReply(): CompanionReply {
    return companionOk(`Mock companion reply ${++this.counter}`);
  }

  async handle(route: Route) {
    const request = route.request();
    let body: CompanionRequestBody;
    try {
      body = request.postDataJSON() as CompanionRequestBody;
    } catch {
      body = { message: "", history: [], context: { page: "other" } };
    }
    this.requests.push({
      method: request.method(),
      headers: request.headers(),
      body,
      raw: request.postData(),
    });
    const scripted = this.queue.shift();
    if (scripted?.abort) {
      await route.abort("connectionrefused");
      return;
    }
    if (scripted?.hold) {
      await new Promise<void>((resolve) => this.waiting.push(resolve));
    }
    const reply =
      scripted?.hold && !scripted.json && !scripted.body
        ? this.defaultReply()
        : (scripted ?? this.defaultReply());
    await route
      .fulfill({
        status: reply.status ?? 200,
        ...(reply.body !== undefined
          ? { body: reply.body, contentType: "application/json" }
          : { json: reply.json }),
      })
      // the page may have timed out and gone away by now
      .catch(() => undefined);
  }
}

/** Register the mock on a page. Call before `page.goto`. */
export async function mockCompanionApi(
  page: Page,
  replies: CompanionReply[] = [],
): Promise<CompanionApiMock> {
  const mock = new CompanionApiMock();
  mock.script(...replies);
  await page.route(
    (url) => url.pathname === COMPANION_PATH,
    (route) => mock.handle(route),
  );
  return mock;
}

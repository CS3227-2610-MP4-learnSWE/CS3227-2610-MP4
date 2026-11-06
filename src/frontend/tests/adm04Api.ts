import { expect, type Page, type Route } from "@playwright/test";
import { ADMIN, STUDENT, TEACHER, mockAuthApi, type User } from "./authApi";
import { FORM_ID, RESPONSE_ID, form } from "./adm02Api";

export { ADMIN, STUDENT, TEACHER, FORM_ID, RESPONSE_ID };
export const API = "/api/admin/messaging";
export const INBOX = "/api/messaging/inbox";
export const NEW = "/admin/announcements/new";
export const REPLY = `/admin/feedback/${FORM_ID}/responses/${RESPONSE_ID}/reply`;
export const SUBJECT = "A better learning experience";
export const BODY =
  "Thank you for sharing your feedback.\nWe have reviewed the issue.";
export const TIME = "2026-11-07T00:00:00Z";
export const MSG = {
  subject: "Enter a subject between 1 and 120 characters.",
  body: "Enter a message between 1 and 5000 characters.",
  recipients: "Select between 1 and 500 recipients.",
  invalid: "Check the message and audience, then review again.",
  missing: "This feedback recipient is unavailable.",
  preview: "This message review is unavailable. Review the message again.",
  changed:
    "The audience has changed. Review the recipients again before sending.",
  expired: "This review has expired. Review the message again.",
  network: "Could not reach the server. Check your connection and try again.",
  timeout:
    "The request timed out. Try again. If you were sending, retry this review to check delivery.",
  csrf: "Your security session has expired. Refresh the page and try again.",
  limited: "Too many messaging requests. Wait a minute and try again.",
  large: "The message request is too large. Shorten it and try again.",
  error: "Messaging encountered an error. Try again.",
  unavailable: "Messaging is temporarily unavailable. Try again.",
};
export type Recipient = { id: string; display_name: string; role: string };
export type Preview = {
  id: string;
  kind: string;
  response_id: string | null;
  audience_role: string;
  audience_mode: string | null;
  subject: string;
  body: string;
  recipients: Recipient[];
  recipient_count: number;
  created_at: string;
  expires_at: string;
};
export type Receipt = {
  message_id: string;
  preview_id: string;
  kind: string;
  recipient_count: number;
  sent_at: string;
};
export type Message = {
  id: string;
  kind: string;
  subject: string;
  body: string;
  sent_at: string;
  read_at: string | null;
};
export type Step = {
  method?: string;
  suffix?: string;
  status?: number;
  code?: string;
  hold?: boolean;
  abort?: boolean;
  commitThenAbort?: boolean;
  json?: unknown;
};
export type Recorded = {
  method: string;
  path: string;
  query: URLSearchParams;
  body: Record<string, unknown>;
  headers: Record<string, string>;
};
export const uuid = (n: number) =>
  `a4000000-0000-4000-8000-${n.toString().padStart(12, "0")}`;
export const person = (user: User): Recipient => ({
  id: user.id,
  display_name: user.display_name,
  role: user.role,
});
export const samplePreview = (id = uuid(1)): Preview => ({
  id,
  kind: "announcement",
  response_id: null,
  audience_role: "student",
  audience_mode: "all_active",
  subject: SUBJECT,
  body: BODY,
  recipients: [person(STUDENT)],
  recipient_count: 1,
  created_at: TIME,
  expires_at: "2026-11-07T00:15:00Z",
});
export const sampleMessage = (n = 1): Message => ({
  id: uuid(100 + n),
  kind: "announcement",
  subject: `Improvement ${n}`,
  body: `Message ${n}\nFull message body.`,
  sent_at: TIME,
  read_at: null,
});

export async function setup(page: Page, user: User | null = ADMIN) {
  await page.route("**/api/**", (route) =>
    route.fulfill({
      status: 503,
      json: {
        detail: {
          code: "test_unrelated",
          message: "Unavailable isolated fixture",
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
    requests: [] as Recorded[],
    steps: [] as Step[],
    waiting: [] as (() => void)[],
    recipients: [person(STUDENT), person(TEACHER)] as Recipient[],
    previews: new Map<string, Preview>(),
    receipts: new Map<string, Receipt>(),
    messages: [] as Message[],
    surveyRequests: 0,
    surveyFailure: false,
    release() {
      this.waiting.splice(0).forEach((resolve) => resolve());
    },
    of(method: string, suffix = "") {
      return this.requests.filter(
        (r) => r.method === method && (!suffix || r.path.endsWith(suffix)),
      );
    },
    makeReceipt(value: Preview): Receipt {
      const old = this.receipts.get(value.id);
      if (old) return old;
      const receipt = {
        message_id: uuid(200 + this.receipts.size),
        preview_id: value.id,
        kind: value.kind,
        recipient_count: value.recipient_count,
        sent_at: TIME,
      };
      this.receipts.set(value.id, receipt);
      return receipt;
    },
  };
  await page.route("**/api/feedback/inbox**", (route) => {
    ctx.surveyRequests++;
    return route.fulfill(
      ctx.surveyFailure
        ? { status: 503, json: { detail: { code: "feedback_unavailable" } } }
        : { json: { items: [], next_offset: null, unread_count: 0 } },
    );
  });
  await page.route(
    `**/api/admin/feedback/forms/${FORM_ID}/responses/${RESPONSE_ID}`,
    (route) =>
      route.fulfill({
        json: {
          id: RESPONSE_ID,
          form_id: FORM_ID,
          respondent: { id: STUDENT.id, display_name: STUDENT.display_name },
          submitted_at: TIME,
          form_snapshot: form(),
          answers: [],
        },
      }),
  );
  const handler = async (route: Route) => {
    const req = route.request(),
      url = new URL(req.url()),
      path = url.pathname,
      method = req.method();
    let body: Record<string, unknown> = {};
    try {
      body = req.postDataJSON() ?? {};
    } catch {
      /* GET */
    }
    ctx.requests.push({
      method,
      path,
      query: url.searchParams,
      body,
      headers: req.headers(),
    });
    const index = ctx.steps.findIndex(
      (s) =>
        (!s.method || s.method === method) &&
        (!s.suffix || path.endsWith(s.suffix)),
    );
    const step = index >= 0 ? ctx.steps.splice(index, 1)[0] : undefined;
    if (step?.hold)
      await new Promise<void>((resolve) => ctx.waiting.push(resolve));
    if (step?.abort) {
      await route.abort("connectionrefused");
      return;
    }
    if (step?.status) {
      await route
        .fulfill({
          status: step.status,
          json: step.json ?? {
            detail: {
              code: step.code,
              message: "Private arbitrary server detail",
              retry_after_seconds: 1,
            },
          },
        })
        .catch(() => undefined);
      return;
    }
    let json: unknown;
    if (path === API + "/recipients") {
      const role = url.searchParams.get("role") ?? "student",
        search = (url.searchParams.get("search") ?? "").trim().toLowerCase(),
        current = Number(url.searchParams.get("page") ?? 1);
      const all = ctx.recipients.filter(
        (r) => r.role === role && r.display_name.toLowerCase().includes(search),
      );
      json = {
        items: all.slice((current - 1) * 50, current * 50),
        page: current,
        page_size: 50,
        total: all.length,
      };
    } else if (path.endsWith("/recipient")) {
      json = { response_id: RESPONSE_ID, recipient: person(STUDENT) };
    } else if (path === API + "/previews" && method === "POST") {
      const people =
        body.kind === "feedback_response"
          ? [person(STUDENT)]
          : ctx.recipients.filter(
              (r) =>
                r.role === body.audience_role &&
                (body.audience_mode === "all_active" ||
                  (body.recipient_ids as string[]).includes(r.id)),
            );
      const value: Preview = {
        id: uuid(ctx.previews.size + 1),
        kind: String(body.kind),
        response_id: body.kind === "feedback_response" ? RESPONSE_ID : null,
        audience_role: people[0]?.role ?? String(body.audience_role),
        audience_mode:
          body.kind === "feedback_response" ? null : String(body.audience_mode),
        subject: String(body.subject).trim(),
        body: String(body.body).trim(),
        recipients: people.sort((a, b) => a.id.localeCompare(b.id)),
        recipient_count: people.length,
        created_at: TIME,
        expires_at: "2026-11-07T00:15:00Z",
      };
      ctx.previews.set(value.id, value);
      json = value;
    } else if (path.endsWith("/send")) {
      const value = ctx.previews.get(path.split("/").at(-2)!)!;
      json = ctx.makeReceipt(value);
      if (step?.commitThenAbort) {
        await route.abort("connectionrefused");
        return;
      }
    } else if (path.startsWith(API + "/previews/")) {
      const id = path.split("/").at(-1)!;
      json = {
        preview: ctx.previews.get(id),
        receipt: ctx.receipts.get(id) ?? null,
      };
    } else if (path === INBOX) {
      const offset = Number(url.searchParams.get("offset") ?? 0),
        unread = ctx.messages.filter((m) => !m.read_at).length;
      json = {
        items: ctx.messages.slice(offset, offset + 20),
        next_offset: offset + 20 < ctx.messages.length ? offset + 20 : null,
        unread_count: unread,
      };
    } else if (path.endsWith("/read")) {
      const id = path.split("/").at(-2)!,
        item = ctx.messages.find((m) => m.id === id)!;
      item.read_at ??= TIME;
      json = { id, read_at: item.read_at };
    } else {
      throw new Error(`Unexpected contract request ${method} ${path}`);
    }
    await route
      .fulfill({
        status: path === API + "/previews" && method === "POST" ? 201 : 200,
        json: step?.json ?? json,
        headers: { "cache-control": "no-store" },
      })
      .catch(() => undefined);
  };
  await page.route("**/api/admin/messaging/**", handler);
  await page.route("**/api/messaging/**", handler);
  return ctx;
}
export const heading = (page: Page, name: string) =>
  page.getByRole("heading", { name, exact: true, level: 1 });
export const alert = (page: Page, text: string) =>
  page.getByRole("alert").filter({ hasText: text });
export async function fill(page: Page, subject = SUBJECT, body = BODY) {
  await page
    .getByRole("textbox", { name: "Subject", exact: true })
    .fill(subject);
  await page.getByRole("textbox", { name: "Message", exact: true }).fill(body);
}
export async function review(page: Page) {
  await fill(page);
  await page
    .getByRole("button", { name: "Review message", exact: true })
    .click();
  await expect(heading(page, "Review message")).toBeVisible();
}

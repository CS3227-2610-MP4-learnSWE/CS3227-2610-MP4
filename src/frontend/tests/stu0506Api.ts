import type { Page, Route } from "@playwright/test";
import { STUDENT, type User } from "./authApi";
import { setup as setupFeedback } from "./adm02Api";

/**
 * STU-05-06 fixture: the ADM-02 feedback mock (survey requests and the form) plus a small
 * stateful ADM-04 messaging mock (inbox, mark read, unread-count). Contracts only:
 * workflow/specs/ADM-08/retained-criteria.md.
 */
export const INBOX = "/api/messaging/inbox";
export const COUNT = "/api/messaging/unread-count";
export const SENT = "2026-11-07T00:00:00Z";
export type Message = {
  id: string;
  kind: string;
  subject: string;
  body: string;
  sent_at: string;
  read_at: string | null;
};
export const message = (n = 1, kind = "announcement"): Message => ({
  id: `a4000000-0000-4000-8000-${(100 + n).toString().padStart(12, "0")}`,
  kind,
  subject: `Improvement ${n}`,
  body: `Message ${n} body`,
  sent_at: SENT,
  read_at: null,
});

export async function setup(page: Page, user: User = STUDENT) {
  const feedback = await setupFeedback(page, user);
  const ctx = {
    feedback,
    messages: [] as Message[],
    /** Scripted failures for the next call whose path ends with `path`. */
    fail: [] as { path: string; status?: number; abort?: boolean }[],
    seen: [] as string[],
    of(method: string, path: string) {
      return this.seen.filter((s) => s === `${method} ${path}`);
    },
    unreadMessages() {
      return this.messages.filter((m) => !m.read_at).length;
    },
    unreadRequests() {
      return feedback.unread ? 1 : 0;
    },
  };
  await page.route("**/api/messaging/**", async (route: Route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    ctx.seen.push(`${req.method()} ${path}`);
    const at = ctx.fail.findIndex((f) => path.endsWith(f.path));
    if (at >= 0) {
      const f = ctx.fail.splice(at, 1)[0];
      if (f.abort) return route.abort("connectionrefused");
      return route.fulfill({
        status: f.status,
        json: { detail: { code: "MESSAGING_UNAVAILABLE", message: "private" } },
      });
    }
    const json = (body: unknown) =>
      route.fulfill({ json: body, headers: { "cache-control": "no-store" } });
    if (path === COUNT) {
      const messages = ctx.unreadMessages();
      const requests = ctx.unreadRequests();
      return json({
        unread_count: messages + requests,
        unread_messages: messages,
        unread_requests: requests,
      });
    }
    if (path === INBOX)
      return json({
        items: ctx.messages,
        next_offset: null,
        unread_count: ctx.unreadMessages(),
      });
    if (path.endsWith("/read")) {
      const id = path.split("/").at(-2);
      const item = ctx.messages.find((m) => m.id === id);
      if (!item) return route.fulfill({ status: 404, json: { detail: {} } });
      item.read_at ??= SENT;
      return json({ id, read_at: item.read_at });
    }
    return route.fulfill({ status: 404, json: { detail: {} } });
  });
  return ctx;
}

export const badge = (page: Page, n: number) =>
  page.getByRole("status", { name: `${n} unread inbox items`, exact: true });
export const anyBadge = (page: Page) =>
  page.getByRole("status", { name: /unread inbox items$/ });

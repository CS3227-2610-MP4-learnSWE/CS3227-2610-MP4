import { expect, type Page, type Route } from "@playwright/test";

/**
 * Mock of the SHR-01 auth API (contract: workflow/specs/SHR-01/plan.md).
 * A tiny stateful fake server: one signed-in user at most, a fixed CSRF token,
 * every request recorded, replies scriptable. No backend is used.
 */

export type Role = "student" | "teacher" | "admin";
export interface User {
  id: string;
  email: string | null;
  display_name: string;
  role: Role;
}

export const STUDENT: User = {
  id: "u-1111aaaa1111aaaa1111aaaa1111aaaa",
  email: "sam.student@example.com",
  display_name: "Sam Student",
  role: "student",
};
export const TEACHER: User = {
  id: "demo-teacher",
  email: "tess.teacher@example.com",
  display_name: "Tess Teacher",
  role: "teacher",
};
export const ADMIN: User = {
  id: "demo-admin",
  email: "adam.admin@example.com",
  display_name: "Adam Admin",
  role: "admin",
};
export const PASSWORD = "correct horse battery staple 42";
export const NOTICE = "Sign in to use live practice and the study companion";
export const DEMO_HEADING =
  "Demo shortcut (development): sample data, not signed in, no real account";

export interface Reply {
  status?: number;
  json?: unknown;
  /** Simulate an unreachable backend. */
  abort?: boolean;
  /** Do not answer until `mock.release()`. */
  hold?: boolean;
  delayMs?: number;
}

export type AuthStep = "me" | "login" | "logout" | "signup";

export interface RecordedAuthRequest {
  step: AuthStep;
  method: string;
  headers: Record<string, string>;
  body: unknown;
}

export function authError(
  status: number,
  code: string,
  extra: Record<string, unknown> = {},
): Reply {
  return {
    status,
    json: { detail: { code, message: `Server says ${code}`, ...extra } },
  };
}

export class AuthApiMock {
  readonly requests: RecordedAuthRequest[] = [];
  /** The signed-in user, or null for an anonymous visitor. */
  user: User | null;
  /** The session's CSRF token; the client must echo it on non-GET calls. */
  csrf: string;
  readonly accounts = new Map<string, { password: string; user: User }>();
  private readonly scripted: Partial<Record<AuthStep, Reply[]>> = {};
  private readonly waiting: (() => void)[] = [];
  private logins = 0;

  constructor(user: User | null, csrf = "csrf-token-fixture-0001") {
    this.user = user;
    this.csrf = csrf;
    for (const u of [STUDENT, TEACHER, ADMIN])
      this.accounts.set(u.email!, { password: PASSWORD, user: u });
  }

  script(step: AuthStep, ...replies: Reply[]) {
    this.scripted[step] = [...(this.scripted[step] ?? []), ...replies];
  }
  of(step: AuthStep) {
    return this.requests.filter((r) => r.step === step);
  }
  count(step: AuthStep) {
    return this.of(step).length;
  }
  release() {
    this.waiting.splice(0).forEach((resolve) => resolve());
  }
  /** The server revokes the session (expiry or logout elsewhere). */
  expire() {
    this.user = null;
  }

  private classify(method: string, path: string): AuthStep | null {
    if (path === "/api/auth/me" && method === "GET") return "me";
    if (path === "/api/auth/login" && method === "POST") return "login";
    if (path === "/api/auth/logout" && method === "POST") return "logout";
    if (path === "/api/auth/signup" && method === "POST") return "signup";
    return null;
  }

  async handle(route: Route) {
    const request = route.request();
    const step = this.classify(
      request.method(),
      new URL(request.url()).pathname,
    );
    if (!step) {
      await route.fulfill({
        status: 404,
        json: authError(404, "not_found").json,
      });
      return;
    }
    let body: unknown = null;
    try {
      body = request.postDataJSON();
    } catch {
      body = request.postData();
    }
    this.requests.push({
      step,
      method: request.method(),
      headers: request.headers(),
      body,
    });
    const scripted = this.scripted[step]?.shift();
    if (scripted?.abort) {
      await route.abort("connectionrefused");
      return;
    }
    if (scripted?.hold) {
      await new Promise<void>((resolve) => this.waiting.push(resolve));
    }
    if (scripted?.delayMs)
      await new Promise((resolve) => setTimeout(resolve, scripted.delayMs));
    const reply =
      scripted && (scripted.json !== undefined || scripted.status)
        ? scripted
        : this.defaultReply(step, request.headers(), body);
    await route
      .fulfill({
        status: reply.status ?? 200,
        json: reply.json,
        headers: { "cache-control": "no-store" },
      })
      .catch(() => undefined);
  }

  private defaultReply(
    step: AuthStep,
    headers: Record<string, string>,
    body: unknown,
  ): Reply {
    if (step === "me") {
      return this.user
        ? { json: { user: this.user, csrf_token: this.csrf } }
        : authError(401, "unauthenticated");
    }
    if (step === "login") {
      const b = body as { email?: string; password?: string } | null;
      const account = this.accounts.get((b?.email ?? "").trim().toLowerCase());
      if (!account || account.password !== b?.password)
        return authError(401, "invalid_credentials");
      this.user = account.user;
      this.csrf = `csrf-token-login-${++this.logins}`;
      return { json: { user: account.user, csrf_token: this.csrf } };
    }
    if (step === "logout") {
      if (this.user && headers["x-csrf-token"] !== this.csrf)
        return authError(403, "csrf_failed");
      this.user = null;
      return { json: { status: "ok" } };
    }
    return { status: 202, json: { status: "accepted" } };
  }
}

/** Register the auth mock on a page. Call before `page.goto`. */
export async function mockAuthApi(
  page: Page,
  options: { user?: User | null; csrf?: string } = {},
): Promise<AuthApiMock> {
  const mock = new AuthApiMock(options.user ?? null, options.csrf);
  // Navigation now reads metadata independently of the current page. Auth-only
  // tests must not forward fixture sessions to a real developer API (401).
  // Inbox-specific tests register their stateful summary handler after this.
  await page.route(
    (url) => url.pathname === "/api/messaging/unread-count",
    (route) =>
      route.fulfill({
        status: 503,
        json: {
          detail: {
            code: "MESSAGING_UNAVAILABLE",
            message: "Test inbox count is unavailable.",
          },
        },
      }),
  );
  // STU-04 loads progress on the student home page. Auth-only fixtures must
  // not send that request to a developer's real API and receive its 401.
  // Progress tests register their own route after this neutral fallback.
  await page.route(
    (url) => url.pathname === "/api/progress",
    (route) =>
      route.fulfill({
        status: 503,
        json: {
          detail: {
            code: "service_unavailable",
            message: "Test progress is unavailable.",
          },
        },
      }),
  );
  // TEA-05 loads the learning overview on the teacher home page. Auth-only fixtures must not
  // send that request to a developer's real API. TEA-05 tests register their own route after
  // this neutral empty report (the later route wins).
  await page.route(
    (url) => url.pathname === "/api/teacher/overview",
    (route) =>
      route.fulfill({
        json: {
          period: {
            preset: "30d",
            start: "2026-10-11T00:00:00Z",
            end: "2026-11-10T00:00:00Z",
            start_date: "2026-10-11",
            end_date: "2026-11-09",
            timezone: "UTC",
          },
          as_of: "2026-11-09T12:00:00Z",
          courses: [],
        },
      }),
  );
  await page.route(
    (url) => url.pathname.startsWith("/api/auth/"),
    (route) => mock.handle(route),
  );
  return mock;
}

/** Sign in as a user through the real login form. */
export async function signInThroughForm(
  page: Page,
  email: string,
  password = PASSWORD,
) {
  await page.goto("/login");
  await emailField(page).fill(email);
  await passwordField(page).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
}

export function emailField(page: Page) {
  return page.getByLabel(/^e-?mail( address)?\s*\*?$/i);
}
export function passwordField(page: Page) {
  return page.getByLabel(/^password\s*\*?$/i);
}

/** Explicit user logout: cancel tests use the dialog directly instead. */
export async function logOutWithConfirmation(page: Page) {
  const dialog = page.getByRole("dialog", {
    name: "Confirm logout",
    exact: true,
  });
  if (!(await dialog.isVisible())) {
    await page
      .getByRole("button", { name: /^log out$/i })
      .first()
      .click();
  }
  await dialog.getByRole("button", { name: "Log out", exact: true }).click();
}

/** Demo-mode storage and cookie state, read in the page. */
export async function browserState(page: Page) {
  return page.evaluate(() => ({
    local: Object.entries(localStorage),
    session: Object.entries(sessionStorage),
    cookie: document.cookie,
  }));
}

export async function expectNoSecretsInBrowser(page: Page, secrets: string[]) {
  const state = JSON.stringify(await browserState(page));
  for (const secret of secrets) expect(state).not.toContain(secret);
  expect(state.toLowerCase()).not.toContain("learnswe_session");
}

/**
 * The "Explore {role} demo" link. The login page shows the link of the selected role tab (student
 * by default), so select the tab first when there is one.
 */
export async function exploreDemoLink(page: Page, role: Role) {
  const tab = page.getByRole("tab", { name: new RegExp(`^${role}$`, "i") });
  if (await tab.count()) await tab.click();
  return page.getByRole("link", { name: `Explore ${role} demo` });
}

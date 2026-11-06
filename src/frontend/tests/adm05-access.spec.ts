import { expect, test, type Page } from "@playwright/test";
import { ADMIN, STUDENT, mockAuthApi } from "./authApi";

test("adm05 follow-up creation shows a green toast and resets fields while retaining role", async ({
  page,
}) => {
  await mockAdmin(page);
  await page.goto("/admin/users");
  await expect(
    page.getByRole("combobox", { name: "Account role", exact: true }),
  ).toContainText("Student");
  await page.getByLabel("Display name", { exact: true }).fill("Fresh Teacher");
  await page
    .getByLabel("Email", { exact: true })
    .fill("fresh-teacher@example.com");
  await choose(page, "Account role", "Teacher");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password", { exact: true }).fill(PASSWORD);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  const toast = page
    .getByRole("status")
    .filter({ hasText: "Account created." });
  await expect(toast).toBeVisible();
  await expect(toast).toHaveClass(/MuiAlert-filledSuccess/);
  for (const field of [
    "Display name",
    "Email",
    "Password",
    "Confirm password",
  ]) {
    await expect(page.getByLabel(field, { exact: true })).toHaveValue("");
  }
  await expect(
    page.getByRole("combobox", { name: "Account role", exact: true }),
  ).toContainText("Teacher");
});

test("adm05 follow-up Manage opens a focused overlay and Escape returns focus", async ({
  page,
}) => {
  await mockAdmin(page);
  await page.setViewportSize({ width: 1100, height: 560 });
  await page.goto("/admin/users");
  const manage = page.getByRole("button", {
    name: "Manage account ADM05 Learner",
    exact: true,
  });
  await manage.click();
  const details = page.getByRole("dialog", {
    name: "Account details",
    exact: true,
  });
  await expect(details).toBeVisible();
  await expect(details).toContainText("adm05-learner@example.com");
  await expect(
    details.getByRole("button", { name: "Close account details", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(details).toHaveCount(0);
  await expect(manage).toBeFocused();
});

test("adm05 follow-up logout stays inside a short sidebar with a long account name", async ({
  page,
}) => {
  await mockAuthApi(page, {
    user: {
      ...ADMIN,
      display_name: "Administrator with a deliberately long display name",
    },
  });
  await page.setViewportSize({ width: 1100, height: 500 });
  await page.goto("/admin/overview");
  const sidebar = page.locator("aside.sidebar");
  const logout = sidebar.getByRole("button", { name: "Log out", exact: true });
  await expect(logout).toBeVisible();
  const bounds = await logout.boundingBox();
  const shell = await sidebar.boundingBox();
  expect(bounds).not.toBeNull();
  expect(shell).not.toBeNull();
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(500);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(
    shell!.x + shell!.width,
  );
  expect(bounds!.height).toBeLessThanOrEqual(48);
});

const PASSWORD = "ExampleOnly!7Qm#42vL";
const learner = {
  id: "u-adm05student",
  email: "adm05-learner@example.com",
  display_name: "ADM05 Learner",
  role: "student",
  status: "enabled",
};
const course = {
  id: "11111111-1111-4111-8111-111111111111",
  title: "ADM05 Course",
};
type Account = typeof learner;
type Recorded = {
  method: string;
  path: string;
  body: unknown;
  headers: Record<string, string>;
};

async function mockAdmin(page: Page) {
  await mockAuthApi(page, { user: ADMIN });
  const requests: Recorded[] = [];
  let account: Account = { ...learner };
  let assigned: (typeof course)[] = [];
  const accounts: Account[] = [account];
  const courses = [course];
  let failure: { status: number; code: string } | null = null;
  let failRead = false;
  await page.route("**/api/admin/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const method = req.method();
    const path = url.pathname;
    let body: unknown;
    try {
      body = req.postDataJSON();
    } catch {
      body = null;
    }
    requests.push({ method, path, body, headers: req.headers() });
    if (failRead && method === "GET" && path.endsWith("/accounts")) {
      failRead = false;
      await route.fulfill({
        status: 503,
        json: {
          detail: { code: "service_unavailable", message: "Unavailable" },
        },
      });
      return;
    }
    if (failure && method !== "GET") {
      const error = failure;
      failure = null;
      await route.fulfill({
        status: error.status,
        json: { detail: { code: error.code, message: error.code } },
      });
      return;
    }
    let json: unknown;
    let status = 200;
    if (path === "/api/admin/accounts" && method === "GET") {
      const statusFilter = url.searchParams.get("status") ?? "enabled";
      const role = url.searchParams.get("role");
      const search = (url.searchParams.get("search") ?? "").toLowerCase();
      const rows = accounts.filter(
        (a) =>
          (statusFilter === "all" || a.status === statusFilter) &&
          (!role || a.role === role) &&
          `${a.display_name} ${a.email}`.toLowerCase().includes(search),
      );
      json = { accounts: rows, total: rows.length, page: 1, page_size: 20 };
    } else if (path === "/api/admin/accounts" && method === "POST") {
      const b = body as Account;
      const created = {
        id: "u-created",
        email: b.email,
        display_name: b.display_name,
        role: b.role,
        status: "enabled",
      };
      accounts.push(created);
      json = created;
      status = 201;
    } else if (path === "/api/admin/courses" && method === "GET") {
      json = { courses };
    } else if (path === "/api/admin/courses" && method === "POST") {
      const created = {
        id: "22222222-2222-4222-8222-222222222222",
        title: (body as { title: string }).title,
      };
      courses.push(created);
      json = created;
      status = 201;
    } else if (path.endsWith("/status")) {
      account.status = (body as { status: string }).status;
      json = { ...account };
    } else if (path.endsWith("/archive")) {
      account.status = "archived";
      assigned = [];
      json = { ...account };
    } else if (path.includes("/courses/")) {
      assigned = method === "PUT" ? [course] : [];
      json = { account, courses: assigned };
    } else {
      json = { account, courses: assigned };
    }
    await route.fulfill({
      status,
      json,
      headers: { "cache-control": "no-store" },
    });
  });
  await page.route("**/api/health", (r) =>
    r.fulfill({ json: { status: "ok" } }),
  );
  return {
    requests,
    failNextRead: () => {
      failRead = true;
    },
    failNextWrite: (status: number, code: string) => {
      failure = { status, code };
    },
    setArchived: () => {
      account = { ...account, status: "archived" };
      accounts[0] = account;
    },
  };
}

async function choose(page: Page, label: string, option: string) {
  const field = page.getByRole("combobox", { name: label, exact: true });
  if (await field.evaluate((el) => el.tagName === "SELECT")) {
    await field.selectOption({ label: option });
  } else {
    await field.click();
    await page.getByRole("option", { name: option, exact: true }).click();
  }
}

async function openAccount(page: Page) {
  await page
    .getByRole("button", { name: "Manage account ADM05 Learner", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Account details", exact: true }),
  ).toBeVisible();
}

test("adm05 AC18 initial reads happen once, account controls and search are accessible", async ({
  page,
}) => {
  const api = await mockAdmin(page);
  await page.goto("/admin/users");
  await expect(
    page.getByRole("heading", { name: "User and access management" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Manage account ADM05 Learner" }),
  ).toBeVisible();
  expect(
    api.requests.filter((r) => r.path === "/api/admin/accounts"),
  ).toHaveLength(1);
  expect(
    api.requests.filter((r) => r.path === "/api/admin/courses"),
  ).toHaveLength(1);
  await page.getByRole("textbox", { name: "Search accounts" }).fill("ADM05");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect
    .poll(
      () => api.requests.filter((r) => r.path === "/api/admin/accounts").length,
    )
    .toBe(2);
  await expect(
    page.getByRole("button", { name: "Previous", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Next", exact: true }),
  ).toBeDisabled();
});

test("adm05 AC5 AC7 creation confirms password, sends no confirmation field and clears secrets", async ({
  page,
}) => {
  const api = await mockAdmin(page);
  await page.goto("/admin/users");
  await page
    .getByRole("textbox", { name: "Display name", exact: true })
    .fill("New Teacher");
  await page
    .getByRole("textbox", { name: "Email", exact: true })
    .fill("new-teacher@example.com");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password", { exact: true }).fill("mismatch");
  await choose(page, "Account role", "Teacher");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Passwords do not match.",
  );
  expect(api.requests.filter((r) => r.method === "POST")).toHaveLength(0);
  await page.getByLabel("Confirm password", { exact: true }).fill(PASSWORD);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Account created." }),
  ).toBeVisible();
  const write = api.requests.find((r) => r.method === "POST")!;
  expect(write.body).toEqual({
    display_name: "New Teacher",
    email: "new-teacher@example.com",
    password: PASSWORD,
    role: "teacher",
  });
  expect(write.headers["x-csrf-token"]).toBeTruthy();
  await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
  await expect(
    page.getByLabel("Confirm password", { exact: true }),
  ).toHaveValue("");
  const storage = await page.evaluate(() =>
    JSON.stringify([
      Object.entries(localStorage),
      Object.entries(sessionStorage),
    ]),
  );
  expect(storage).not.toContain(PASSWORD);
});

test("adm05 AC19 disable requires confirmation and cancellation sends no mutation", async ({
  page,
}) => {
  const api = await mockAdmin(page);
  await page.goto("/admin/users");
  await openAccount(page);
  await page
    .getByRole("button", { name: "Disable account", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Confirm disable",
    exact: true,
  });
  await expect(dialog).toContainText("ADM05 Learner");
  expect(api.requests.filter((r) => r.method !== "GET")).toHaveLength(0);
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
  expect(api.requests.filter((r) => r.method !== "GET")).toHaveLength(0);
  await page
    .getByRole("button", { name: "Disable account", exact: true })
    .click();
  await dialog.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Enable account", exact: true }),
  ).toBeVisible();
});

test("adm05 AC9 AC19 grant and revoke use selected course and removal confirmation", async ({
  page,
}) => {
  const api = await mockAdmin(page);
  await page.goto("/admin/users");
  await openAccount(page);
  await choose(page, "Course", "ADM05 Course");
  await page
    .getByRole("button", { name: "Grant course access", exact: true })
    .click();
  const remove = page.getByRole("button", {
    name: "Remove course access ADM05 Course",
    exact: true,
  });
  await expect(remove).toBeVisible();
  await remove.click();
  const dialog = page.getByRole("dialog", {
    name: "Confirm removal",
    exact: true,
  });
  await expect(dialog).toContainText("ADM05 Course");
  expect(api.requests.filter((r) => r.method === "DELETE")).toHaveLength(0);
  await dialog.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(
    page.getByText("No course access.", { exact: true }),
  ).toBeVisible();
  expect(api.requests.filter((r) => r.method === "DELETE")).toHaveLength(1);
});

test("adm05 AC13 AC19 archive confirmation describes permanence and history", async ({
  page,
}) => {
  await mockAdmin(page);
  await page.goto("/admin/users");
  await openAccount(page);
  await page
    .getByRole("button", { name: "Archive account", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Confirm archive",
    exact: true,
  });
  await expect(dialog).toContainText(/permanent/i);
  await expect(dialog).toContainText(/history|records/i);
  await dialog.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(
    page.getByText("This account is permanently archived.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Enable account", exact: true }),
  ).toHaveCount(0);
});

test("adm05 AC16 course creation and courses navigation", async ({ page }) => {
  const api = await mockAdmin(page);
  await page.goto("/admin/courses");
  await expect(
    page.getByRole("heading", { name: "Courses", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Course title", exact: true })
    .fill("New Course");
  await page
    .getByRole("button", { name: "Create course", exact: true })
    .click();
  await expect(page.getByText("New Course", { exact: true })).toBeVisible();
  expect(api.requests.find((r) => r.method === "POST")?.body).toEqual({
    title: "New Course",
  });
  await page.getByRole("link", { name: "Users", exact: true }).click();
  await expect(page).toHaveURL(/\/admin\/users$/);
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: "Courses", exact: true }),
  ).toBeVisible();
});

test("adm05 read failure is specific and retry repeats only failed request", async ({
  page,
}) => {
  const api = await mockAdmin(page);
  api.failNextRead();
  await page.goto("/admin/users");
  await expect(page.getByRole("alert")).toContainText(
    "The account management service is unavailable. Try again later.",
  );
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Manage account ADM05 Learner" }),
  ).toBeVisible();
  expect(
    api.requests.filter((r) => r.path === "/api/admin/accounts"),
  ).toHaveLength(2);
  expect(
    api.requests.filter((r) => r.path === "/api/admin/courses"),
  ).toHaveLength(1);
});

test("adm05 failed creation preserves entered fields and reports duplicate email", async ({
  page,
}) => {
  const api = await mockAdmin(page);
  await page.goto("/admin/users");
  await page
    .getByRole("textbox", { name: "Display name", exact: true })
    .fill("New User");
  await page
    .getByRole("textbox", { name: "Email", exact: true })
    .fill("duplicate@example.com");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password", { exact: true }).fill(PASSWORD);
  api.failNextWrite(409, "email_exists");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "An account with this email already exists.",
  );
  await expect(
    page.getByRole("textbox", { name: "Display name", exact: true }),
  ).toHaveValue("New User");
  await expect(
    page.getByRole("textbox", { name: "Email", exact: true }),
  ).toHaveValue("duplicate@example.com");
  expect(api.requests.filter((r) => r.method === "POST")).toHaveLength(1);
});

test("adm05 wrong role redirects before any admin requests", async ({
  page,
}) => {
  const api = await mockAdmin(page);
  await mockAuthApi(page, { user: STUDENT });
  await page.goto("/admin/users");
  await expect(page).toHaveURL(/\/student\/overview$/);
  expect(api.requests).toHaveLength(0);
});

test("adm05 AC14 AC18 archived filter exposes read-only account details", async ({
  page,
}) => {
  const api = await mockAdmin(page);
  api.setArchived();
  await page.goto("/admin/users");
  await expect(
    page.getByText("No accounts found.", { exact: true }),
  ).toBeVisible();
  await choose(page, "Status filter", "Archived");
  await openAccount(page);
  await expect(
    page.getByText("This account is permanently archived.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Archive account", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Grant course access", exact: true }),
  ).toHaveCount(0);
});

test("adm05 failed confirmed write preserves dialog and shows CSRF recovery", async ({
  page,
}) => {
  const api = await mockAdmin(page);
  await page.goto("/admin/users");
  await openAccount(page);
  await page
    .getByRole("button", { name: "Disable account", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Confirm disable",
    exact: true,
  });
  api.failNextWrite(403, "csrf_failed");
  await dialog.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(dialog).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(
    "Your security token is invalid. Sign in again before making changes.",
  );
  expect(api.requests.filter((r) => r.method === "PUT")).toHaveLength(1);
});

test("adm05 session expiry clears selected account and entered password", async ({
  page,
}) => {
  const api = await mockAdmin(page);
  await page.goto("/admin/users");
  await openAccount(page);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page
    .getByRole("button", { name: "Disable account", exact: true })
    .click();
  api.failNextWrite(401, "unauthenticated");
  await page
    .getByRole("dialog", { name: "Confirm disable" })
    .getByRole("button", { name: "Confirm", exact: true })
    .click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("heading", { name: "Account details", exact: true }),
  ).toHaveCount(0);
  const passwords = await page
    .locator('input[type="password"]')
    .evaluateAll((nodes) => nodes.map((n) => (n as HTMLInputElement).value));
  expect(passwords).not.toContain(PASSWORD);
});

test("adm05 mobile account list visibly identifies the account before management", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockAdmin(page);
  await page.goto("/admin/users");
  await expect(
    page.getByRole("cell", { name: "ADM05 Learner adm05-learner@example.com" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Manage account ADM05 Learner" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("adm05 late old-session 401 cannot sign out a newly authenticated admin", async ({
  page,
}) => {
  await mockAdmin(page);
  const auth = await mockAuthApi(page, { user: ADMIN });
  const second = {
    ...ADMIN,
    id: "u-second-admin",
    email: "second-admin@example.com",
    display_name: "Second Admin",
  };
  auth.accounts.set(second.email!, {
    user: second,
    password: "second-admin-password-7391",
  });
  let release!: () => void;
  let entered!: () => void;
  const started = new Promise<void>((resolve) => {
    entered = resolve;
  });
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/admin/accounts/u-adm05student", async (route) => {
    entered();
    await gate;
    await route.fulfill({
      status: 401,
      json: {
        detail: { code: "unauthenticated", message: "Sign in to continue." },
      },
    });
  });
  await page.goto("/admin/users");
  await page
    .getByRole("button", { name: "Manage account ADM05 Learner", exact: true })
    .click();
  await started;
  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel(/^email/i).fill(second.email!);
  await page.getByLabel(/^password/i).fill("second-admin-password-7391");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/admin\/overview$/);
  await expect(page.getByText("Second Admin", { exact: true })).toBeVisible();
  const response = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/admin/accounts/u-adm05student") &&
      r.status() === 401,
  );
  release();
  await response;
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  await expect(page).toHaveURL(/\/admin\/overview$/);
  await expect(page.getByText("Second Admin", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Account details", exact: true }),
  ).toHaveCount(0);
});

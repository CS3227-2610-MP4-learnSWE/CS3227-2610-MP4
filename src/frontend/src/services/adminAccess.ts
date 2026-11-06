import { ApiError, getSessionGeneration, request } from "./client";

export type AccountRole = "student" | "teacher" | "admin";
export type AccountStatus = "enabled" | "disabled" | "archived";
export type Account = {
  id: string;
  email: string | null;
  display_name: string;
  role: AccountRole;
  status: AccountStatus;
};
export type Course = { id: string; title: string };
export type AccountDetail = { account: Account; courses: Course[] };
export type AccountPage = {
  accounts: Account[];
  total: number;
  page: number;
  page_size: number;
};
export type AccountQuery = {
  search?: string;
  role?: AccountRole;
  status?: AccountStatus | "all";
  page?: number;
  page_size?: number;
};

const object = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const count = (value: unknown): value is number =>
  Number.isInteger(value) && (value as number) >= 0;
const course = (value: unknown): value is Course =>
  object(value) &&
  typeof value.id === "string" &&
  typeof value.title === "string";
const account = (value: unknown): value is Account =>
  object(value) &&
  typeof value.id === "string" &&
  typeof value.display_name === "string" &&
  (value.email === null || typeof value.email === "string") &&
  ["student", "teacher", "admin"].includes(value.role as string) &&
  ["enabled", "disabled", "archived"].includes(value.status as string);
const detail = (value: unknown): value is AccountDetail =>
  object(value) &&
  account(value.account) &&
  Array.isArray(value.courses) &&
  value.courses.every(course);
const page = (value: unknown): value is AccountPage =>
  object(value) &&
  Array.isArray(value.accounts) &&
  value.accounts.every(account) &&
  count(value.total) &&
  count(value.page) &&
  value.page > 0 &&
  count(value.page_size) &&
  value.page_size > 0;
const courseList = (value: unknown): value is { courses: Course[] } =>
  object(value) && Array.isArray(value.courses) && value.courses.every(course);
const seg = encodeURIComponent;
const pending = new Map<string, Promise<unknown>>();
let mutation = 0;

async function checked<T>(
  value: Promise<unknown>,
  validate: (data: unknown) => data is T,
): Promise<T> {
  const data = await value;
  if (!validate(data)) throw new ApiError(0, "bad_response");
  return data;
}
function read(path: string): Promise<unknown> {
  const key = `${getSessionGeneration()}:${mutation}:${path}`;
  const existing = pending.get(key);
  if (existing) return existing;
  const started = request("GET", path).finally(() => pending.delete(key));
  pending.set(key, started);
  return started;
}
async function write(
  method: string,
  path: string,
  body?: unknown,
): Promise<unknown> {
  mutation += 1;
  try {
    return await request(method, path, body);
  } finally {
    mutation += 1;
  }
}

export function listAccounts(query: AccountQuery = {}) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query))
    if (value !== undefined && value !== "") search.set(key, String(value));
  const suffix = search.size ? `?${search}` : "";
  return checked(read(`/api/admin/accounts${suffix}`), page);
}
export function createAccount(body: {
  display_name: string;
  email: string;
  password: string;
  role: AccountRole;
}) {
  return checked(write("POST", "/api/admin/accounts", body), account);
}
export function getAccount(id: string) {
  return checked(read(`/api/admin/accounts/${seg(id)}`), detail);
}
export function setAccountStatus(id: string, status: "enabled" | "disabled") {
  return checked(
    write("PUT", `/api/admin/accounts/${seg(id)}/status`, { status }),
    account,
  );
}
export function archiveAccount(id: string) {
  return checked(
    write("POST", `/api/admin/accounts/${seg(id)}/archive`),
    account,
  );
}
export function grantCourseAccess(id: string, courseId: string) {
  return checked(
    write("PUT", `/api/admin/accounts/${seg(id)}/courses/${seg(courseId)}`),
    detail,
  );
}
export function revokeCourseAccess(id: string, courseId: string) {
  return checked(
    write("DELETE", `/api/admin/accounts/${seg(id)}/courses/${seg(courseId)}`),
    detail,
  );
}
export function listCourses() {
  return checked(read("/api/admin/courses"), courseList);
}
export function createCourse(title: string) {
  return checked(write("POST", "/api/admin/courses", { title }), course);
}

export function adminError(error: unknown): string {
  const failure =
    error instanceof ApiError ? error : new ApiError(0, "bad_response");
  const messages: Record<string, string> = {
    forbidden: "You do not have access to account management.",
    csrf_failed:
      "Your security token is invalid. Sign in again before making changes.",
    not_found: "This account or course is no longer available.",
    email_exists: "An account with this email already exists.",
    self_change: "You cannot disable or archive your own account.",
    last_admin: "At least one enabled administrator must remain.",
    account_archived: "Archived accounts cannot be changed.",
    invalid_assignment:
      "Course access is available only for student and teacher accounts.",
    validation_error: "Check the entered details and try again.",
    rate_limited: "Too many requests. Try again later.",
    network: "Could not reach the server. Try again.",
    bad_response: "The server returned an unexpected response. Try again.",
  };
  if (failure.status >= 500)
    return "The account management service is unavailable. Try again later.";
  return (
    messages[failure.code] ??
    (failure.status === 403
      ? messages.forbidden
      : failure.status === 404
        ? messages.not_found
        : failure.status === 422
          ? messages.validation_error
          : failure.status === 429
            ? messages.rate_limited
            : messages.bad_response)
  );
}

export const REQUEST_TIMEOUT_MS = 10_000;

// The CSRF token lives in memory only; AuthContext sets it after sign-in or /api/auth/me.
let csrfToken: string | null = null;
// Changes on every sign-in, sign-out and session clear, so callers can tell requests of different sessions apart.
let sessionGeneration = 0;
export function getSessionGeneration() {
  return sessionGeneration;
}
export function setCsrfToken(token: string | null) {
  csrfToken = token;
  sessionGeneration += 1;
}
// Called on 401 "unauthenticated" from `request`; the callback decides by auth state what to do.
let onUnauthenticated: (() => void) | null = null;
export function setUnauthenticatedHandler(handler: (() => void) | null) {
  onUnauthenticated = handler;
}
const SAFE_METHODS = ["GET", "HEAD", "OPTIONS"];

export class ApiError extends Error {
  status: number;
  code: string;
  missing: string[];
  retryAfterSeconds: number | null;
  constructor(
    status: number,
    code = "",
    missing: string[] = [],
    retryAfterSeconds: number | null = null,
  ) {
    super(code || `HTTP ${status}`);
    this.status = status;
    this.code = code;
    this.missing = missing;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

/** Builds the ApiError for a non-2xx response from the body's `detail`, if it is JSON. */
async function errorFrom(response: Response): Promise<ApiError> {
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    data = undefined;
  }
  const detail = (data as { detail?: unknown } | undefined)?.detail as
    | { code?: unknown; missing?: unknown; retry_after_seconds?: unknown }
    | undefined;
  const code = typeof detail?.code === "string" ? detail.code : "";
  const missing = Array.isArray(detail?.missing)
    ? detail.missing.filter((id): id is string => typeof id === "string")
    : [];
  const retry = detail?.retry_after_seconds;
  return new ApiError(
    response.status,
    code,
    missing,
    typeof retry === "number" && Number.isInteger(retry) && retry > 0
      ? retry
      : null,
  );
}

/** The one place that applies the timeout, runs fetch and maps failures to ApiError. */
async function send(
  path: string,
  init: RequestInit,
  timeoutMs: number,
  readOk: (response: Response) => Promise<unknown>,
  distinguishTimeout = false,
): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, { ...init, signal: controller.signal });
    if (!response.ok) throw await errorFrom(response);
    return await readOk(response);
  } catch (error) {
    if (distinguishTimeout && controller.signal.aborted)
      throw new ApiError(0, "timeout");
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, "network");
  } finally {
    clearTimeout(timer);
  }
}

/** Calls the business API. Throws ApiError for HTTP errors and network/timeout/bad JSON (status 0). */
export async function request(
  method: string,
  path: string,
  body?: unknown,
  options: {
    timeoutMs?: number;
    distinguishTimeout?: boolean;
    cache?: RequestCache;
  } = {},
): Promise<unknown> {
  // A delayed rejection from a previous account must not sign out a newer one.
  const originGeneration = getSessionGeneration();
  try {
    return await send(
      path,
      {
        method,
        credentials: "same-origin",
        cache: options.cache,
        headers: {
          ...(body === undefined ? {} : { "Content-Type": "application/json" }),
          ...(csrfToken && !SAFE_METHODS.includes(method.toUpperCase())
            ? { "X-CSRF-Token": csrfToken }
            : {}),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      },
      options.timeoutMs ?? REQUEST_TIMEOUT_MS,
      async (response) => {
        let data: unknown;
        try {
          data = await response.json();
        } catch {
          data = undefined;
        }
        if (data === undefined) throw new ApiError(0, "bad_response");
        return data;
      },
      options.distinguishTimeout ?? false,
    );
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      error.code === "unauthenticated" &&
      originGeneration === getSessionGeneration()
    )
      onUnauthenticated?.();
    throw error;
  }
}

const teacherReads = new Map<string, Promise<unknown>>();
let teacherMutationEpoch = 0;
export function invalidateTeacherReads() {
  teacherReads.clear();
}

/** Identical pending reads share one request, never data from a previous write/session. */
export function requestTeacher(
  method: string,
  path: string,
  body?: FormData | object,
  blob = false,
  timeoutMs = REQUEST_TIMEOUT_MS,
  includeStatus = false,
): Promise<unknown> {
  const verb = method.toUpperCase();
  if (verb === "GET") {
    const key = `${getSessionGeneration()}:${teacherMutationEpoch}:${path}:${blob}:${timeoutMs}:${includeStatus}`;
    const existing = teacherReads.get(key);
    if (existing) return existing;
    const pending = sendTeacher(
      verb,
      path,
      body,
      blob,
      timeoutMs,
      includeStatus,
    ).finally(() => {
      if (teacherReads.get(key) === pending) teacherReads.delete(key);
    });
    teacherReads.set(key, pending);
    return pending;
  }
  if (!SAFE_METHODS.includes(verb)) teacherMutationEpoch += 1;
  return sendTeacher(verb, path, body, blob, timeoutMs, includeStatus).finally(
    () => {
      if (!SAFE_METHODS.includes(verb)) teacherMutationEpoch += 1;
    },
  );
}

/** Teacher transport shares cookie/CSRF identity and handles empty DELETE responses. */
async function sendTeacher(
  method: string,
  path: string,
  body?: FormData | object,
  blob = false,
  timeoutMs = REQUEST_TIMEOUT_MS,
  includeStatus = false,
): Promise<unknown> {
  const token = csrfToken;
  const headers: Record<string, string> = {};
  if (token && !SAFE_METHODS.includes(method.toUpperCase()))
    headers["X-CSRF-Token"] = token;
  if (body !== undefined && !(body instanceof FormData))
    headers["Content-Type"] = "application/json";
  try {
    return await send(
      path,
      {
        method,
        credentials: "same-origin",
        headers,
        body:
          body instanceof FormData
            ? body
            : body === undefined
              ? undefined
              : JSON.stringify(body),
      },
      timeoutMs,
      async (response) => {
        const data =
          response.status === 204
            ? undefined
            : blob
              ? await response.blob()
              : await response.json();
        return includeStatus ? { data, status: response.status } : data;
      },
    );
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      error.code === "unauthenticated" &&
      token === csrfToken
    )
      onUnauthenticated?.();
    throw error;
  }
}

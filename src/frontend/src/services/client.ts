export const REQUEST_TIMEOUT_MS = 10_000;

// The CSRF token lives in memory only; AuthContext sets it after sign-in or /api/auth/me.
let csrfToken: string | null = null;
export function setCsrfToken(token: string | null) {
  csrfToken = token;
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

/** Calls the business API. Throws ApiError for HTTP errors and network/timeout/bad JSON (status 0). */
export async function request(
  method: string,
  path: string,
  body?: unknown,
  options: { timeoutMs?: number } = {},
): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? REQUEST_TIMEOUT_MS,
  );
  try {
    const response = await fetch(path, {
      method,
      signal: controller.signal,
      credentials: "same-origin",
      headers: {
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...(csrfToken && !SAFE_METHODS.includes(method.toUpperCase())
          ? { "X-CSRF-Token": csrfToken }
          : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      data = undefined;
    }
    if (!response.ok) {
      const detail = (data as { detail?: unknown } | undefined)?.detail as
        | { code?: unknown; missing?: unknown; retry_after_seconds?: unknown }
        | undefined;
      const code = typeof detail?.code === "string" ? detail.code : "";
      const missing = Array.isArray(detail?.missing)
        ? detail.missing.filter((id): id is string => typeof id === "string")
        : [];
      const retry = detail?.retry_after_seconds;
      if (response.status === 401 && code === "unauthenticated")
        onUnauthenticated?.();
      throw new ApiError(
        response.status,
        code,
        missing,
        typeof retry === "number" && Number.isInteger(retry) && retry > 0
          ? retry
          : null,
      );
    }
    if (data === undefined) throw new ApiError(0, "bad_response");
    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, "network");
  } finally {
    clearTimeout(timer);
  }
}

/** Teacher-only transport. The demo header is sent only with an explicit local gate. */
export async function requestTeacher(
  method: string,
  path: string,
  body?: FormData | object,
  blob = false,
  timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const headers: Record<string, string> = {};
  if (
    import.meta.env.VITE_APP_ENV === "development" &&
    import.meta.env.VITE_ALLOW_DEMO_IDENTITY === "true"
  ) {
    headers["X-Demo-User-Id"] =
      import.meta.env.VITE_DEMO_USER_ID || "demo-teacher";
  }
  if (body !== undefined && !(body instanceof FormData))
    headers["Content-Type"] = "application/json";
  try {
    const response = await fetch(path, {
      method,
      signal: controller.signal,
      headers,
      body:
        body instanceof FormData
          ? body
          : body === undefined
            ? undefined
            : JSON.stringify(body),
    });
    if (!response.ok) {
      let code = "";
      let retryAfter: number | null = null;
      try {
        const data = await response.json();
        code = typeof data?.detail?.code === "string" ? data.detail.code : "";
        const retry = data?.detail?.retry_after_seconds;
        if (Number.isInteger(retry) && retry > 0) retryAfter = retry;
      } catch {
        /* unavailable response body */
      }
      throw new ApiError(response.status, code, [], retryAfter);
    }
    return blob ? response.blob() : response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, "network");
  } finally {
    clearTimeout(timer);
  }
}

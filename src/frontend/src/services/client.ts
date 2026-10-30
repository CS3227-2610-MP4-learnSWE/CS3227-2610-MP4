import { STUDENT_ID } from "../config";

export const REQUEST_TIMEOUT_MS = 10_000;

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
      headers: {
        "X-Student-Id": STUDENT_ID,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
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

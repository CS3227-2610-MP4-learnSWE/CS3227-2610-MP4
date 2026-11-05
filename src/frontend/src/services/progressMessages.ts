import type { ApiError } from "./client";

const UNREACHABLE =
  "Could not reach the server. Check your connection and try again.";
const UNAVAILABLE = "Progress is unavailable right now. Please try again.";
const BAD_RESPONSE = "Progress could not be read. Please try again.";
const FORBIDDEN = "You do not have access to progress.";

const isUnauthenticated = (error: ApiError) =>
  error.status === 401 && error.code === "unauthenticated";
const isForbidden = (error: ApiError) =>
  error.status === 403 && error.code === "forbidden";
const isNetwork = (error: ApiError) =>
  error.status === 0 && error.code === "network";

/** The exact text of a failed Progress page load; null when the auth hook handles it (401). */
export function progressErrorMessage(error: ApiError): string | null {
  if (isUnauthenticated(error)) return null;
  if (isForbidden(error)) return FORBIDDEN;
  if (isNetwork(error)) return UNREACHABLE;
  if (error.status === 0) return BAD_RESPONSE;
  return UNAVAILABLE;
}

/** The detail line of an Overview stat after a failed load. */
export function progressStatDetail(error: ApiError, demoMode: boolean): string {
  if (isUnauthenticated(error))
    return demoMode ? "Sign in to see your progress" : UNAVAILABLE;
  if (isForbidden(error)) return FORBIDDEN;
  if (isNetwork(error)) return "Could not reach the server.";
  return UNAVAILABLE;
}

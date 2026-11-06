import type { ApiError } from "./client";

const UNREACHABLE =
  "Could not reach the server. Check your connection and try again.";
const UNAVAILABLE =
  "Practice sets are unavailable right now. Please try again.";
const BAD_RESPONSE = "Practice sets could not be read. Please try again.";
export const PRACTICE_FORBIDDEN = "You do not have access to practice.";
export const SET_NOT_AVAILABLE = "This practice set is not available to you.";
export const SET_NO_LONGER_AVAILABLE =
  "This practice set is no longer available to you.";

/** The exact text of a failed picker load; null when the auth hook handles it (401). */
export function catalogErrorMessage(error: ApiError): string | null {
  if (error.status === 401 && error.code === "unauthenticated") return null;
  if (error.status === 403 && error.code === "forbidden")
    return PRACTICE_FORBIDDEN;
  if (error.status === 0 && error.code === "network") return UNREACHABLE;
  if (error.status === 0) return BAD_RESPONSE;
  return UNAVAILABLE;
}

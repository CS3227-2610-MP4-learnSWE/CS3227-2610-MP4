import type { ApiError } from "./client";

const UNREACHABLE =
  "Could not reach the server. Check your connection and try again.";
const NOT_SAVED_UNREACHABLE =
  "Could not reach the server. Your progress was not saved.";
const NOT_SAVED = "Could not save your progress. Nothing was changed.";

/** The exact user-facing text for a failed study-materials call; null when the auth hook handles it. */
export function lessonErrorMessage(
  error: ApiError,
  action: "load" | "save",
): string | null {
  if (error.status === 401 && error.code === "unauthenticated") return null;
  if (error.status === 403 && error.code === "forbidden")
    return "You do not have access to study materials.";
  if (error.status === 0 && error.code === "network")
    return action === "save" ? NOT_SAVED_UNREACHABLE : UNREACHABLE;
  if (action === "save") return NOT_SAVED;
  if (error.status === 0)
    return "Study materials could not be read. Please try again.";
  return "Study materials are unavailable right now. Please try again.";
}

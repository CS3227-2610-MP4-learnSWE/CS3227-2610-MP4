import { ApiError } from "../services/client";
import type { Step } from "../services/feedbackAnalysisApi";

export const NO_ACCESS =
  "You do not have access to this page. Only admin accounts can use feedback analysis.";
export const SELECTION_REQUIRED =
  "No responses are selected. Select at least one response, or use Select all, then generate the analysis.";
export const DELETED_STATUS =
  "Analysis deleted. The original feedback responses and forms were not changed.";
export const DELETE_404 =
  "This analysis was already deleted or is not in your history. The list has been refreshed.";
export const NETWORK_PROGRESS =
  "Could not reach the server while checking the analysis progress. The analysis is saved and may still be running. Press Retry to check again.";
export const STOPPED_WAITING =
  "Stopped waiting after 450 seconds. The server may still be working. Reload this page to check again.";
export const unreadableStatus = (status: number) =>
  `The server answered the progress check with an unreadable reply (HTTP ${status}). The analysis is saved. Press Retry to check again.`;

const asApiError = (error: unknown) =>
  error instanceof ApiError ? error : new ApiError(0, "network");

/** The exact message for a failed request; `doing` completes "while ..." (for example "loading forms"). */
export function failureMessage(error: unknown, doing: string): string {
  const e = asApiError(error);
  if (e.status === 403) return NO_ACCESS;
  if (e.code === "timeout")
    return `The server did not answer within 15 seconds while ${doing}. Press Retry.`;
  if (e.status === 0 && e.code === "network")
    return `Could not reach the server while ${doing}. Check your connection and press Retry.`;
  const message = e.detail.message;
  if (typeof message === "string" && message) return message;
  return `The server returned an unrecognised failure (HTTP ${e.status}) while ${doing}.`;
}

export const loadMessage = (error: unknown, what: string) =>
  failureMessage(error, `loading ${what}`);

const START_TAIL =
  "If it did start it will appear in Previous analyses. Press Generate analysis again; repeating it will not start a second copy.";
export function generateMessage(error: unknown): string {
  const e = asApiError(error);
  if (e.code === "timeout")
    return `The server did not answer within 15 seconds while starting the analysis. ${START_TAIL}`;
  if (e.status === 0 && e.code === "network")
    return `Could not reach the server while starting the analysis. ${START_TAIL}`;
  return failureMessage(e, "starting the analysis");
}

export function deleteMessage(error: unknown): string {
  const e = asApiError(error);
  if (e.code === "timeout")
    return "The server did not answer within 15 seconds while deleting the analysis. It may or may not be deleted. Press Delete permanently again; if it was already deleted you will be told so.";
  if (e.status === 0 && e.code === "network")
    return "Could not reach the server while deleting the analysis. It was not confirmed as deleted. Press Delete permanently to try again.";
  if (e.status === 404) return DELETE_404;
  return failureMessage(e, "deleting the analysis");
}

/** A network failure or abort: the request may or may not have reached the server. */
export const isTransport = (error: unknown) =>
  !(error instanceof ApiError) ||
  (error.status === 0 &&
    (error.code === "network" || error.code === "timeout"));

export const localTime = (iso: string) => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? "date unavailable"
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
};

export const stepText = (step: Step | null) =>
  !step
    ? ""
    : step.kind === "batch"
      ? `batch ${step.index} of ${step.total}`
      : step.kind === "merge"
        ? "merging themes"
        : "starting";

export const RESPONSE_NOT_FOUND =
  "This response was not found. It may already have been deleted, or it does not belong to this form.";
export const RESPONSE_DELETED_STATUS =
  "Response deleted. The form, the respondent's account and stored analyses were not changed. The respondent can submit again only if the form is open.";

export function deleteResponseMessage(error: unknown): string {
  const e = asApiError(error);
  if (e.code === "timeout")
    return "The server did not answer within 15 seconds while deleting the response. It may or may not be deleted. Press Delete permanently again; if it was already deleted you will be told so.";
  if (e.status === 0 && e.code === "network")
    return "Could not reach the server while deleting the response. It was not confirmed as deleted. Press Delete permanently to try again.";
  if (e.status === 404) return RESPONSE_NOT_FOUND;
  if (e.status === 403)
    return "You do not have permission to delete feedback responses. Only admin accounts can.";
  return failureMessage(e, "deleting the response");
}

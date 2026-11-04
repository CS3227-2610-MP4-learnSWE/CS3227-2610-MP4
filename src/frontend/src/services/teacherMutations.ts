import { ApiError } from "./client";

export const conflictMessage =
  "This draft has changed. Load the latest saved version before trying again.";
export function teacherMutationError(
  error: unknown,
  action: "save" | "delete",
) {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      csrf_failed:
        "Your request could not be verified. Refresh the page and try again.",
      forbidden: "You do not have permission to manage teacher content.",
      not_found: "This item is no longer available. Refresh the list.",
      draft_conflict: conflictMessage,
      material_in_use:
        "Delete the note drafts and MCQ batches referencing this material first.",
      draft_in_use:
        "This draft is referenced by other content and cannot be deleted.",
      service_unavailable: "Teacher service is unavailable. Please try again.",
      validation_error:
        action === "save"
          ? "Check the question fields and try again."
          : "Could not verify the draft version. Load the latest saved version and try again.",
    };
    if (messages[error.code]) return messages[error.code];
    if (error.status === 0)
      return action === "save"
        ? "Could not save changes. Your edits are still here."
        : "Could not confirm deletion. Refresh the list before trying again.";
  }
  return action === "save"
    ? "Could not save changes. Your edits are still here."
    : "Could not delete this item. Please try again.";
}

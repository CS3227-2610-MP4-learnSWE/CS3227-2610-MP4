import { ApiError } from "./client";

export function teacherGenerationError(
  error: unknown,
  kind: "notes" | "MCQs",
): string {
  if (!(error instanceof ApiError))
    return `Could not generate draft ${kind}. Please try again.`;
  const messages: Record<string, string> = {
    source_text_empty:
      "No usable source text was found. Scanned PDFs need a text-based source.",
    source_text_too_large:
      "Choose a source with at most 8,000 characters and 100 PDF pages.",
    source_unreadable:
      "The source could not be read. Choose a UTF-8 text file or text-based PDF.",
    llm_not_configured:
      "The AI service is not configured. Ask your developer to check the backend settings.",
    llm_timeout: "Generation timed out. Please try again.",
    llm_bad_response: `The AI service returned unusable or incomplete ${kind}. Please try again.`,
    llm_upstream_error: `The AI service could not generate ${kind}. Please try again.`,
    llm_unavailable: "The AI service is unavailable. Please try again later.",
    llm_rate_limited:
      "Too many generation requests. Please wait before retrying.",
    llm_busy: "The AI service is busy. Please wait before retrying.",
  };
  const message =
    messages[error.code] ||
    `Could not generate draft ${kind}. Please try again.`;
  return error.retryAfterSeconds
    ? `${message} Try again in ${error.retryAfterSeconds} seconds.`
    : message;
}

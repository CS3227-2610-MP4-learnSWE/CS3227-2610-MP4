import { ApiError, request } from "./client";

const options = {
  timeoutMs: 15000,
  distinguishTimeout: true,
  cache: "no-store" as const,
};

export type FormsCounts = {
  open: number;
  drafts: number;
  submitted: number;
  truncated: boolean;
};
export type CountSource = "forms" | "analyses" | "followup";

const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const isCount = (v: unknown): v is number =>
  Number.isSafeInteger(v) && (v as number) >= 0;

function items(data: unknown): Record<string, unknown>[] {
  if (!isObject(data) || !Array.isArray(data.items))
    throw new ApiError(0, "bad_response");
  return data.items.map((item) => {
    if (!isObject(item)) throw new ApiError(0, "bad_response");
    return item;
  });
}
const truncated = (data: unknown) =>
  isObject(data) && data.next_offset !== null && data.next_offset !== undefined;

/** Form counts for the Forms and Responses tabs, from the newest 100 forms (one shared request). */
export async function fetchFormsCounts(
  signal: AbortSignal,
): Promise<FormsCounts> {
  const data = await request(
    "GET",
    "/api/admin/feedback/forms?limit=100&offset=0",
    undefined,
    { ...options, signal },
  );
  const forms = items(data);
  let submitted = 0;
  for (const form of forms) {
    if (form.state !== "draft" && isCount(form.response_count))
      submitted += form.response_count;
  }
  return {
    open: forms.filter((form) => form.state === "open").length,
    drafts: forms.filter((form) => form.state === "draft").length,
    submitted,
    truncated: truncated(data),
  };
}

/** Saved analyses for the Analysis tab, from the newest 50. */
export async function fetchAnalysesCount(
  signal: AbortSignal,
): Promise<{ value: number; truncated: boolean }> {
  const data = await request(
    "GET",
    "/api/admin/feedback/analyses?limit=50&offset=0",
    undefined,
    { ...options, signal },
  );
  return { value: items(data).length, truncated: truncated(data) };
}

/** Responses still without a sent reply, for the Follow-up tab. */
export async function fetchFollowUpCount(signal: AbortSignal): Promise<number> {
  const data = await request(
    "GET",
    "/api/admin/messaging/followup-counts",
    undefined,
    { ...options, signal },
  );
  if (!isObject(data) || !isCount(data.unanswered_responses))
    throw new ApiError(0, "bad_response");
  return data.unanswered_responses;
}

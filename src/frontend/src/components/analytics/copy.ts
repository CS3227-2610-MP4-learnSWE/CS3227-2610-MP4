import type { Reason } from "../../services/featureAnalytics";

/** Shown after "Unavailable: ". */
const UNAVAILABLE: Record<string, (recorded: string) => string> = {
  period_before_recording: (recorded) =>
    `recording began on ${recorded}, after this period ended`,
  no_source: () => "this activity is not recorded",
  read_failed: () => "the value could not be read reliably",
  not_collected: () => "collection of this metric has not started",
  beyond_retention: () =>
    "hourly data is kept for 30 days and this period starts earlier",
};

/** Shown after "Not applicable: ". */
const NOT_APPLICABLE: Record<string, string> = {
  no_practice_attempts: "no practice attempts were started in this period",
  no_generation_attempts: "no generation attempts in this period",
  no_chat_requests: "no chatbot requests in this period",
  no_eligible_records: "no eligible records in this period",
  none_graded: "no responses have been graded for this period yet",
};

export const unavailableReason = (reason: Reason | null, recorded = "") =>
  UNAVAILABLE[reason ?? ""]?.(recorded) ?? "the value is not available";

export const notApplicableReason = (reason: Reason | null) =>
  NOT_APPLICABLE[reason ?? ""] ?? "there is nothing to calculate";

export const unavailableText = (reason: Reason | null, recorded = "") =>
  `Unavailable: ${unavailableReason(reason, recorded)}.`;

export const startsNote = (date: string) =>
  `Data starts on ${date}. Earlier days in this period are not included.`;

export const seconds2 = (ms: number) => `${(ms / 1000).toFixed(2)} s`;
export const percent1 = (value: number) => `${value.toFixed(1)}%`;

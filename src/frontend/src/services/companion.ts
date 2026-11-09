import { ApiError, request } from "./client";

export const COMPANION_TIMEOUT_MS = 40_000;

export type CompanionMode = "hint" | "explain" | "help" | "lesson";
export type CompanionSource = { lesson_id: string; title: string };
export type CompanionRequest = {
  message: string;
  history: { role: "user" | "assistant"; text: string }[];
  context: {
    page: "practice" | "lesson" | "other";
    set_id: string | null;
    attempt_id: string | null;
    lesson_id: string | null;
    label: string | null;
  };
};
export type CompanionReply = {
  reply: string;
  mode: CompanionMode;
  withheld: boolean;
  sources: CompanionSource[];
};

const MODES: string[] = ["hint", "explain", "help", "lesson"];

function isSources(value: unknown): value is CompanionSource[] {
  return (
    Array.isArray(value) &&
    value.every(
      (s) =>
        typeof s === "object" &&
        s !== null &&
        typeof s.lesson_id === "string" &&
        typeof s.title === "string",
    )
  );
}

/** The server picks the mode; the request carries only page context, never a mode or an answer. */
export async function sendCompanionMessage(
  req: CompanionRequest,
): Promise<CompanionReply> {
  const data = await request("POST", "/api/companion/messages", req, {
    timeoutMs: COMPANION_TIMEOUT_MS,
  });
  const d = data as Partial<Record<keyof CompanionReply, unknown>> | null;
  if (
    typeof d !== "object" ||
    d === null ||
    typeof d.reply !== "string" ||
    typeof d.mode !== "string" ||
    !MODES.includes(d.mode) ||
    typeof d.withheld !== "boolean" ||
    !isSources(d.sources)
  )
    throw new ApiError(0, "bad_response");
  return data as CompanionReply;
}

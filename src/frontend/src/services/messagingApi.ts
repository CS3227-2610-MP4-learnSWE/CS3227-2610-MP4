import { ApiError, getSessionGeneration, request } from "./client";

export type Recipient = {
  id: string;
  display_name: string;
  role: "student" | "teacher";
};
export type Preview = {
  id: string;
  kind: "feedback_response" | "announcement";
  response_id: string | null;
  audience_role: "student" | "teacher";
  audience_mode: "all_active" | "selected" | null;
  subject: string;
  body: string;
  recipients: Recipient[];
  recipient_count: number;
  created_at: string;
  expires_at: string;
};
export type Receipt = {
  message_id: string;
  preview_id: string;
  kind: string;
  recipient_count: number;
  sent_at: string;
};
export type RecipientPage = {
  items: Recipient[];
  page: number;
  page_size: number;
  total: number;
};
export type InboxMessage = {
  id: string;
  kind: string;
  subject: string;
  body: string;
  sent_at: string;
  read_at: string | null;
};
export type MessagePage = {
  items: InboxMessage[];
  next_offset: number | null;
  unread_count: number;
};
export const messagingBase = "/api/admin/messaging";

const messages: Record<string, string> = {
  unauthenticated: "Your session has expired. Sign in again.",
  forbidden: "Only admins can send messages.",
  csrf_failed:
    "Your security session has expired. Refresh the page and try again.",
  INVALID_SUBJECT: "Enter a subject between 1 and 120 characters.",
  INVALID_BODY: "Enter a message between 1 and 5000 characters.",
  INVALID_RECIPIENTS: "Select between 1 and 500 recipients.",
  INVALID_REQUEST: "Check the message and audience, then review again.",
  RECIPIENT_UNAVAILABLE: "This feedback recipient is unavailable.",
  PREVIEW_UNAVAILABLE:
    "This message review is unavailable. Review the message again.",
  MESSAGE_UNAVAILABLE: "This message is unavailable.",
  AUDIENCE_CHANGED:
    "The audience has changed. Review the recipients again before sending.",
  PREVIEW_EXPIRED: "This review has expired. Review the message again.",
  MESSAGING_RATE_LIMITED:
    "Too many messaging requests. Wait a minute and try again.",
  REQUEST_TOO_LARGE:
    "The message request is too large. Shorten it and try again.",
  MESSAGING_ERROR: "Messaging encountered an error. Try again.",
  MESSAGING_UNAVAILABLE: "Messaging is temporarily unavailable. Try again.",
  network: "Could not reach the server. Check your connection and try again.",
  timeout:
    "The request timed out. Try again. If you were sending, retry this review to check delivery.",
  bad_response: "The server returned an invalid message response. Try again.",
};
export function messagingCode(error: unknown) {
  return error instanceof ApiError ? error.code : "";
}
export function messagingError(error: unknown) {
  const code = messagingCode(error);
  if (messages[code]) return messages[code];
  if (error instanceof ApiError) {
    if (error.status === 503) return messages.MESSAGING_UNAVAILABLE;
    if (error.status === 500) return messages.MESSAGING_ERROR;
    if (error.status === 413) return messages.REQUEST_TOO_LARGE;
    if (error.status === 429) return messages.MESSAGING_RATE_LIMITED;
    return `The message request failed (HTTP ${error.status}). Try again.`;
  }
  return messages.MESSAGING_ERROR;
}

async function send<T>(
  method: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const generation = getSessionGeneration();
  const result = await request(method, path, body, {
    timeoutMs: 15000,
    distinguishTimeout: true,
    cache: "no-store",
    signal,
  });
  if (generation !== getSessionGeneration() || signal?.aborted)
    throw new ApiError(0, "stale_session");
  if (!validResponse(path, result)) throw new ApiError(0, "bad_response");
  return result as T;
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
const string = (value: unknown) => typeof value === "string";
const count = (value: unknown) =>
  Number.isSafeInteger(value) && Number(value) >= 0;
function recipient(value: unknown) {
  return (
    object(value) &&
    string(value.id) &&
    string(value.display_name) &&
    ["student", "teacher"].includes(String(value.role))
  );
}
function preview(value: unknown) {
  return (
    object(value) &&
    string(value.id) &&
    ["feedback_response", "announcement"].includes(String(value.kind)) &&
    (value.response_id === null || string(value.response_id)) &&
    ["student", "teacher"].includes(String(value.audience_role)) &&
    (value.audience_mode === null ||
      ["all_active", "selected"].includes(String(value.audience_mode))) &&
    string(value.subject) &&
    string(value.body) &&
    Array.isArray(value.recipients) &&
    value.recipients.every(recipient) &&
    value.recipients.length === value.recipient_count &&
    string(value.created_at) &&
    string(value.expires_at)
  );
}
function receipt(value: unknown) {
  return (
    object(value) &&
    string(value.message_id) &&
    string(value.preview_id) &&
    string(value.kind) &&
    count(value.recipient_count) &&
    string(value.sent_at)
  );
}
function validResponse(path: string, value: unknown): boolean {
  if (!object(value)) return false;
  const pathname = path.split("?")[0];
  if (pathname.endsWith("/recipient"))
    return string(value.response_id) && recipient(value.recipient);
  if (pathname.endsWith("/recipients"))
    return (
      Array.isArray(value.items) &&
      value.items.every(recipient) &&
      count(value.page) &&
      value.page_size === 50 &&
      count(value.total)
    );
  if (pathname.endsWith("/send")) return receipt(value);
  if (pathname.endsWith("/previews")) return preview(value);
  if (pathname.includes("/previews/"))
    return (
      preview(value.preview) &&
      (value.receipt === null || receipt(value.receipt))
    );
  if (pathname.endsWith("/read"))
    return string(value.id) && string(value.read_at);
  if (pathname === "/api/messaging/inbox")
    return (
      Array.isArray(value.items) &&
      value.items.every(
        (item) =>
          object(item) &&
          string(item.id) &&
          ["feedback_response", "announcement"].includes(String(item.kind)) &&
          string(item.subject) &&
          string(item.body) &&
          string(item.sent_at) &&
          (item.read_at === null || string(item.read_at)),
      ) &&
      (value.next_offset === null || count(value.next_offset)) &&
      count(value.unread_count)
    );
  return false;
}

// Share only pending reads. Delay abort through StrictMode cleanup/replay; never
// retain private result data across routes, writes, accounts or browser history.
const pending = new Map<
  string,
  {
    promise: Promise<unknown>;
    controller: AbortController;
    users: number;
    timer?: ReturnType<typeof setTimeout>;
  }
>();
export function messagingRead<T>(path: string) {
  const key = `${getSessionGeneration()}:${path}`;
  let entry = pending.get(key);
  if (!entry) {
    const controller = new AbortController();
    entry = {
      controller,
      users: 0,
      promise: send<T>("GET", path, undefined, controller.signal).finally(
        () => {
          if (pending.get(key) === entry) pending.delete(key);
        },
      ),
    };
    pending.set(key, entry);
  }
  entry.users++;
  clearTimeout(entry.timer);
  const owned = entry;
  return {
    promise: owned.promise as Promise<T>,
    release: () => {
      owned.users--;
      if (!owned.users)
        owned.timer = setTimeout(() => {
          if (!owned.users) owned.controller.abort();
        }, 0);
    },
  };
}
export function messagingWrite<T>(
  path: string,
  body: unknown,
  signal?: AbortSignal,
) {
  return send<T>("POST", path, body, signal);
}

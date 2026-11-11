import { createContext, useContext } from "react";

/** Every page address of the feedback screens. Screens read it from context so they do not know where they are mounted. */
export type FeedbackPaths = {
  forms(): string;
  newForm(): string;
  form(id: string): string;
  editForm(id: string): string;
  responses(): string;
  formResponses(formId: string): string;
  response(formId: string, responseId: string): string;
  analysis(): string;
  analysisResult(id: string): string;
  analysisEvidence(id: string, label: string): string;
  announcement(): string;
  reply(formId: string, responseId: string): string;
  /** Link to the Analysis screen with a form preselected; null where the screen does not offer the shortcut. */
  analysisForForm(formId: string): string | null;
};

const LEGACY = "/admin/feedback";
const HUB = "/admin/feedback-hub";

export const legacyPaths: FeedbackPaths = {
  forms: () => LEGACY,
  newForm: () => `${LEGACY}/new`,
  form: (id) => `${LEGACY}/${id}`,
  editForm: (id) => `${LEGACY}/${id}/edit`,
  responses: () => LEGACY,
  formResponses: (formId) => `${LEGACY}/${formId}/responses`,
  response: (formId, responseId) =>
    `${LEGACY}/${formId}/responses/${responseId}`,
  analysis: () => `${LEGACY}/analysis`,
  analysisResult: (id) => `${LEGACY}/analysis/${id}`,
  analysisEvidence: (id, label) =>
    `${LEGACY}/analysis/${id}/responses/${label}`,
  announcement: () => "/admin/announcements/new",
  reply: (formId, responseId) =>
    `${LEGACY}/${formId}/responses/${responseId}/reply`,
  analysisForForm: () => null,
};

export const hubPaths: FeedbackPaths = {
  forms: () => `${HUB}/forms`,
  newForm: () => `${HUB}/forms/new`,
  form: (id) => `${HUB}/forms/${id}`,
  editForm: (id) => `${HUB}/forms/${id}/edit`,
  responses: () => `${HUB}/responses`,
  formResponses: (formId) => `${HUB}/responses/${formId}`,
  response: (formId, responseId) => `${HUB}/responses/${formId}/${responseId}`,
  analysis: () => `${HUB}/analysis`,
  analysisResult: (id) => `${HUB}/analysis/${id}`,
  analysisEvidence: (id, label) => `${HUB}/analysis/${id}/responses/${label}`,
  announcement: () => `${HUB}/follow-up`,
  reply: (formId, responseId) =>
    `${HUB}/follow-up/reply/${formId}/${responseId}`,
  analysisForForm: (formId) =>
    `${HUB}/analysis?form=${encodeURIComponent(formId)}`,
};

const FeedbackPathsContext = createContext<FeedbackPaths>(legacyPaths);
export const FeedbackPathsProvider = FeedbackPathsContext.Provider;
export const useFeedbackPaths = () => useContext(FeedbackPathsContext);

export type HubTab = "forms" | "responses" | "analysis" | "follow-up";
export type HubScreen =
  | "forms"
  | "form-new"
  | "form"
  | "form-edit"
  | "chooser"
  | "response-list"
  | "response"
  | "analysis"
  | "analysis-result"
  | "analysis-evidence"
  | "announcement"
  | "reply";
export type HubRoute =
  | { notFound: true }
  | {
      notFound?: false;
      tab: null;
      screen: "root" | "unknown";
      params: Record<string, never>;
    }
  | {
      notFound?: false;
      tab: HubTab;
      screen: HubScreen;
      params: Record<string, string>;
    };

/** Maps a pathname under the hub base to its tab, screen and route parameters (the route table of ADM-08). */
export function parseHubPath(pathname: string): HubRoute {
  if (pathname !== HUB && !pathname.startsWith(`${HUB}/`))
    return { notFound: true };
  const rest = pathname.slice(HUB.length).replace(/\/$/, "");
  if (!rest) return { tab: null, screen: "root", params: {} };
  const s = rest.slice(1).split("/");
  if (s.some((part) => !part)) return { notFound: true };
  const found = (
    tab: HubTab,
    screen: HubScreen,
    params: Record<string, string> = {},
  ): HubRoute => ({ tab, screen, params });
  const [first, a, b, c] = s;
  switch (first) {
    case "forms":
      if (s.length === 1) return found("forms", "forms");
      if (a === "new")
        return s.length === 2 ? found("forms", "form-new") : { notFound: true };
      if (s.length === 2) return found("forms", "form", { formId: a });
      if (s.length === 3 && b === "edit")
        return found("forms", "form-edit", { formId: a });
      return { notFound: true };
    case "responses":
      if (s.length === 1) return found("responses", "chooser");
      if (s.length === 2)
        return found("responses", "response-list", { formId: a });
      if (s.length === 3)
        return found("responses", "response", { formId: a, responseId: b });
      return { notFound: true };
    case "analysis":
      if (s.length === 1) return found("analysis", "analysis");
      if (s.length === 2)
        return found("analysis", "analysis-result", { analysisId: a });
      if (s.length === 4 && b === "responses")
        return found("analysis", "analysis-evidence", {
          analysisId: a,
          label: c,
        });
      return { notFound: true };
    case "follow-up":
      if (s.length === 1) return found("follow-up", "announcement");
      if (s.length === 4 && a === "reply")
        return found("follow-up", "reply", { formId: b, responseId: c });
      return { notFound: true };
    default:
      return { tab: null, screen: "unknown", params: {} };
  }
}

export type FeedbackScreenRoute =
  | { screen: "forms" }
  | { screen: "form-new" }
  | { screen: "form"; formId: string }
  | { screen: "form-edit"; formId: string }
  | { screen: "response-list"; formId: string }
  | { screen: "response"; formId: string; responseId: string };

/** The screen of an old `/admin/feedback/...` address (same segment positions the old page used). */
export function parseLegacyFeedbackPath(pathname: string): FeedbackScreenRoute {
  const [, , , id, action, responseId] = pathname.split("/");
  if (!id) return { screen: "forms" };
  if (id === "new") return { screen: "form-new" };
  if (action === "edit") return { screen: "form-edit", formId: id };
  if (action === "responses")
    return responseId
      ? { screen: "response", formId: id, responseId }
      : { screen: "response-list", formId: id };
  return { screen: "form", formId: id };
}

export type ReplyTarget = { formId: string; responseId: string };

/** The reply target of an old `/admin/feedback/{form}/responses/{response}/reply` address, else undefined. */
export function parseLegacyReplyPath(
  pathname: string,
): ReplyTarget | undefined {
  if (!pathname.endsWith("/reply")) return undefined;
  const parts = pathname.split("/");
  return { formId: parts[3], responseId: parts[5] };
}

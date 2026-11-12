import { createContext, useContext } from "react";

export type Count = {
  state: "loading" | "unavailable" | "ready";
  value: number;
  truncated: boolean;
};
export type HubCounts = {
  forms: Count;
  responses: Count;
  analysis: Count;
  followUp: Count;
  /** Forms in state draft, only for the Forms tab description. */
  drafts: number;
};
export type CountKind = "forms" | "responses" | "analysis" | "followUp";

const loadingCount: Count = { state: "loading", value: 0, truncated: false };
export const initialCounts: HubCounts = {
  forms: loadingCount,
  responses: loadingCount,
  analysis: loadingCount,
  followUp: loadingCount,
  drafts: 0,
};

export const HubCountsContext = createContext<HubCounts>(initialCounts);
export const useHubCounts = () => useContext(HubCountsContext);

const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

/** Badge and screen-reader text of a tab count; null when nothing is shown (not loaded, or zero). */
export function formatCount(
  count: Count,
  kind: CountKind,
  drafts = 0,
): { badge: string; description: string } | null {
  if (count.state !== "ready" || count.value <= 0) return null;
  const n = count.value;
  const lead = count.truncated ? `at least ${n}` : `${n}`;
  const badge = count.truncated ? `${n}+` : `${n}`;
  switch (kind) {
    case "forms": {
      const draftText =
        drafts > 0 ? `, ${drafts} ${plural(drafts, "draft", "drafts")}` : "";
      return {
        badge,
        description: `${lead} open ${plural(n, "form", "forms")}${draftText}`,
      };
    }
    case "responses":
      return {
        badge,
        description: `${lead} submitted ${plural(n, "response", "responses")}`,
      };
    case "analysis":
      return {
        badge,
        description: `${lead} saved ${plural(n, "analysis", "analyses")}`,
      };
    case "followUp":
      return {
        badge: n > 99 ? "99+" : `${n}`,
        description: `${n} ${plural(n, "response", "responses")} without a reply`,
      };
  }
}

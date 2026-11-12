import type { Page } from "@playwright/test";

/**
 * The hub mounts three count requests once per page load (ADM-08 AC26). The old ADM-02 and ADM-03
 * assertions count only the requests of the screen itself, so the ported helpers leave the count
 * requests out of their request log. A forms or analyses request that has the exact shape of a
 * count request is treated as the count the first time it is seen after each full page load; any
 * further identical request still counts (it is the screen's own).
 */
export function hubCountFilter(page: Page) {
  let forms = false;
  let analyses = false;
  page.on("load", () => {
    forms = false;
    analyses = false;
  });
  return (method: string, path: string, search: string) => {
    if (method !== "GET") return false;
    if (path === "/api/admin/messaging/followup-counts") return true;
    if (
      path === "/api/admin/feedback/forms" &&
      search === "?limit=100&offset=0" &&
      !forms
    )
      return (forms = true);
    if (
      path === "/api/admin/feedback/analyses" &&
      search === "?limit=50&offset=0" &&
      !analyses
    )
      return (analyses = true);
    return false;
  };
}

import { mockAuthApi, TEACHER } from "./authApi";
import type { Page, Route } from "@playwright/test";
import { TeacherMcqsApi, BATCH, SAVED, COURSE_A } from "./teacherMcqsApi";
import { TOPIC_A } from "./teacherMaterialsApi";
export { BATCH, SAVED, COURSE_A, TOPIC_A };
export type Publication = {
  id: string;
  kind: "note" | "practice_set";
  course_id: string;
  topic_id: string | null;
  topic_name: string | null;
  title: string;
  published_at: string;
  source_draft_id: string | null;
  source_version: number | null;
  published_by: string;
  withdrawn: boolean;
  question_count?: number;
  content?: string;
  questions?: typeof BATCH.questions;
};
export function snapshot(kind: "note" | "practice_set" = "note"): Publication {
  return {
    id:
      kind === "note"
        ? "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
        : "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    kind,
    course_id: COURSE_A,
    topic_id: TOPIC_A,
    topic_name: "Testing",
    title: kind === "note" ? SAVED.title : BATCH.source_title,
    published_at: "2026-11-05T10:00:00Z",
    source_draft_id: kind === "note" ? SAVED.id : BATCH.id,
    source_version: 1,
    published_by: "demo-teacher",
    withdrawn: false,
    ...(kind === "note"
      ? { content: SAVED.content }
      : { question_count: 3, questions: structuredClone(BATCH.questions) }),
  };
}
export class TeacherPublicationsApi extends TeacherMcqsApi {
  publications: Publication[] = [];
  publicationCalls = 0;
  failStatus = 0;
  failDetail = 0;
  publishStatus = 0;
  publishCode = "service_unavailable";
  holdPublish: Promise<void> | null = null;
  holdStatus: Promise<void> | null = null;
  loseResponse = false;
  override async handle(route: Route) {
    const req = route.request(),
      path = new URL(req.url()).pathname,
      method = req.method();
    const list = path.match(/^\/api\/teacher\/courses\/([^/]+)\/publications$/);
    const detail = path.match(
      /^\/api\/teacher\/(published-notes|published-practice-sets)\/([^/]+)$/,
    );
    const publish = path.match(
      /^\/api\/teacher\/(note-drafts|mcq-drafts)\/([^/]+)\/publish$/,
    );
    if (!list && !detail && !publish) return super.handle(route);
    this.requests.push({
      method,
      path,
      body: req.postData(),
      headers: req.headers(),
    });
    const fail = (status: number, code = "service_unavailable") =>
      route.fulfill({
        status,
        json: { detail: { code, message: "PRIVATE SENTINEL" } },
      });
    if (list) {
      if (this.holdStatus) await this.holdStatus;
      if (this.failStatus-- > 0) return fail(503);
      return route.fulfill({
        json: this.publications
          .filter((p) => p.course_id === list[1])
          .map((p) => {
            const m = { ...p };
            delete m.content;
            delete m.questions;
            return m;
          }),
      });
    }
    if (detail) {
      if (this.failDetail-- > 0) return fail(503);
      const p = this.publications.find((p) => p.id === detail[2]);
      return p ? route.fulfill({ json: p }) : fail(404, "not_found");
    }
    this.publicationCalls++;
    if (this.holdPublish) await this.holdPublish;
    if (this.publishStatus) return fail(this.publishStatus, this.publishCode);
    const payload = JSON.parse(req.postData() || "{}");
    const old = this.publications.find(
      (p) => p.source_draft_id === publish![2],
    );
    if (old) return route.fulfill({ status: 200, json: old });
    const p = {
      ...snapshot(publish![1] === "note-drafts" ? "note" : "practice_set"),
      title: payload.title,
      topic_id: payload.topic_id,
      source_version: payload.version,
    };
    this.publications.unshift(p);
    if (this.loseResponse) return route.abort("failed");
    return route.fulfill({ status: 201, json: p });
  }
}
export async function mockTeacherPublicationsApi(page: Page) {
  await mockAuthApi(page, { user: TEACHER });
  const api = new TeacherPublicationsApi();
  await page.route("**/api/health", (r) =>
    r.fulfill({ json: { status: "ok" } }),
  );
  await page.route(
    (url) => url.pathname.startsWith("/api/teacher/"),
    (r) => api.handle(r),
  );
  return api;
}

import type { Page, Route } from "@playwright/test";
import {
  TeacherMaterialsApi,
  COURSE_A,
  COURSE_B,
  NEW,
  OLD,
} from "./teacherMaterialsApi";
export { COURSE_A, COURSE_B, NEW, OLD };
export type NoteDraft = {
  id: string;
  course_id: string;
  source_material_id: string;
  created_by: string;
  title: string;
  created_at: string;
  content: string;
};
export const SAVED: NoteDraft = {
  id: "88888888-8888-4888-8888-888888888888",
  course_id: COURSE_A,
  source_material_id: NEW.id,
  created_by: "demo-teacher",
  title: "Saved draft 1",
  created_at: "2026-11-01T10:00:00Z",
  content: "Core concept\n- One responsibility per function.",
};

export class TeacherNotesApi extends TeacherMaterialsApi {
  drafts: NoteDraft[] = [SAVED];
  generationCalls = 0;
  failGeneration = 0;
  failDrafts = 0;
  failGet = 0;
  holdGeneration: Promise<void> | null = null;
  override async handle(route: Route) {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();
    const json = (status: number, value: unknown) =>
      route.fulfill({ status, json: value });
    const fail = () =>
      json(503, {
        detail: {
          code: "llm_unavailable",
          message: "Upstream private sentinel must not be shown",
        },
      });
    const create = path.match(
      /^\/api\/teacher\/materials\/([^/]+)\/note-drafts$/,
    );
    const list = path.match(/^\/api\/teacher\/courses\/([^/]+)\/note-drafts$/);
    const get = path.match(/^\/api\/teacher\/note-drafts\/([^/]+)$/);
    if (!create && !list && !get) return super.handle(route);
    this.requests.push({
      method,
      path,
      body: request.postData(),
      headers: request.headers(),
    });
    if (create && method === "POST") {
      this.generationCalls++;
      if (this.holdGeneration) await this.holdGeneration;
      if (this.failGeneration-- > 0) return fail();
      const material = this.materials.find((item) => item.id === create[1])!;
      const draft = {
        ...SAVED,
        id: `99999999-9999-4999-8999-${String(this.generationCalls).padStart(12, "0")}`,
        course_id: material.course_id,
        source_material_id: material.id,
        title: "Generated draft",
        created_at: "2026-11-01T12:00:00Z",
      };
      this.drafts.unshift(draft);
      return json(201, draft);
    }
    if (list && method === "GET") {
      if (this.failDrafts-- > 0) return fail();
      return json(
        200,
        this.drafts
          .filter((draft) => draft.course_id === list[1])
          .map(({ content: _content, ...metadata }) => metadata),
      );
    }
    if (get && method === "GET") {
      if (this.failGet-- > 0) return fail();
      const draft = this.drafts.find((item) => item.id === get[1]);
      return draft
        ? json(200, draft)
        : json(404, {
            detail: { code: "not_found", message: "Draft not found." },
          });
    }
    return json(405, {});
  }
}
export async function mockTeacherNotesApi(page: Page) {
  const api = new TeacherNotesApi();
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.route(
    (url) => url.pathname.startsWith("/api/teacher/"),
    (route) => api.handle(route),
  );
  return api;
}

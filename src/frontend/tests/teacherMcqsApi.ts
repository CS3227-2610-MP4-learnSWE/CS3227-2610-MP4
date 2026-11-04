import { mockAuthApi, TEACHER } from "./authApi";
import type { Page, Route } from "@playwright/test";
import { TeacherNotesApi, COURSE_A, NEW } from "./teacherNotesApi";
export { COURSE_A, COURSE_B, NEW, SAVED } from "./teacherNotesApi";
export const BATCH = {
  id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  course_id: COURSE_A,
  source_material_id: NEW.id,
  source_title: "Original testing source",
  created_by: "demo-teacher",
  created_at: "2026-11-02T10:00:00Z",
  question_count: 3,
  version: 1,
  updated_at: "2026-11-02T10:00:00Z",
  updated_by: "demo-teacher",
  questions: [1, 2, 3].map((position) => ({
    id: `bbbbbbbb-bbbb-4bbb-8bbb-${String(position).padStart(12, "0")}`,
    position,
    question: `What does unit test ${position} check?`,
    choices: ["One behaviour", "All code", "No code", "A database"],
    correct_choice_index: position - 1,
    explanation: `Explanation for question ${position}.`,
  })),
};
export class TeacherMcqsApi extends TeacherNotesApi {
  batches = [structuredClone(BATCH)];
  mcqCalls = 0;
  failMcq = 0;
  failBatches = 0;
  failBatch = 0;
  holdMcq: Promise<void> | null = null;
  mcqPatchCalls = 0;
  failMcqPatch = 0;
  holdMcqPatch: Promise<void> | null = null;
  override async handle(route: Route) {
    const request = route.request(),
      path = new URL(request.url()).pathname,
      method = request.method();
    const create = path.match(
      /^\/api\/teacher\/materials\/([^/]+)\/mcq-drafts$/,
    );
    const list = path.match(/^\/api\/teacher\/courses\/([^/]+)\/mcq-drafts$/);
    const get = path.match(/^\/api\/teacher\/mcq-drafts\/([^/]+)$/);
    if (!create && !list && !get) return super.handle(route);
    this.requests.push({
      method,
      path,
      body: request.postData(),
      headers: request.headers(),
    });
    const json = (status: number, value: unknown) =>
      route.fulfill({ status, json: value });
    const fail = () =>
      json(503, {
        detail: {
          code: "llm_unavailable",
          message: "sentinel-private-provider-error",
        },
      });
    if (get && method === "PATCH") {
      this.mcqPatchCalls++;
      if (this.holdMcqPatch) await this.holdMcqPatch;
      const index = this.batches.findIndex((b) => b.id === get[1]);
      if (index < 0)
        return json(404, {
          detail: { code: "not_found", message: "Batch not found." },
        });
      const payload = JSON.parse(request.postData() || "{}");
      if (this.failMcqPatch || payload.version !== this.batches[index].version)
        return json(this.failMcqPatch || 409, {
          detail: {
            code:
              this.failMcqPatch === 503
                ? "service_unavailable"
                : "draft_conflict",
            message: "sentinel-private",
          },
        });
      const old = this.batches[index];
      this.batches[index] = {
        ...old,
        version: old.version + 1,
        updated_by: this.editorId,
        updated_at: "2026-11-04T12:00:00Z",
        questions: old.questions.map((q) => ({
          ...q,
          ...payload.questions.find((p: { id: string }) => p.id === q.id),
        })),
      };
      return json(200, this.batches[index]);
    }
    if (get && method === "DELETE") {
      this.deleteCalls++;
      if (this.holdDelete) await this.holdDelete;
      if (this.failDeleteStatus)
        return json(this.failDeleteStatus, {
          detail: { code: this.failDeleteCode, message: "sentinel-private" },
        });
      const index = this.batches.findIndex((b) => b.id === get[1]);
      if (index < 0)
        return json(404, {
          detail: { code: "not_found", message: "Batch not found." },
        });
      if (
        new URL(request.url()).searchParams.get("version") !==
        String(this.batches[index].version)
      )
        return json(409, {
          detail: { code: "draft_conflict", message: "sentinel-private" },
        });
      this.batches.splice(index, 1);
      return route.fulfill({ status: 204 });
    }
    if (create && method === "POST") {
      this.mcqCalls++;
      if (this.holdMcq) await this.holdMcq;
      if (this.failMcq-- > 0) return fail();
      const material = this.materials.find((item) => item.id === create[1])!;
      const batch = {
        ...structuredClone(BATCH),
        id: `cccccccc-cccc-4ccc-8ccc-${String(this.mcqCalls).padStart(12, "0")}`,
        course_id: material.course_id,
        source_material_id: material.id,
        source_title: material.title,
        created_at: "2026-11-02T12:00:00Z",
      };
      this.batches.unshift(batch);
      return json(201, batch);
    }
    if (list && method === "GET") {
      if (this.failBatches-- > 0) return fail();
      return json(
        200,
        this.batches
          .filter((b) => b.course_id === list[1])
          .map((b) => ({
            id: b.id,
            course_id: b.course_id,
            source_material_id: b.source_material_id,
            source_title: b.source_title,
            created_by: b.created_by,
            created_at: b.created_at,
            question_count: b.question_count,
            version: b.version,
            updated_at: b.updated_at,
            updated_by: b.updated_by,
          })),
      );
    }
    if (get && method === "GET") {
      if (this.failBatch-- > 0) return fail();
      const batch = this.batches.find((b) => b.id === get[1]);
      return batch
        ? json(200, batch)
        : json(404, {
            detail: { code: "not_found", message: "Batch not found." },
          });
    }
    return json(405, {});
  }
}
export async function mockTeacherMcqsApi(page: Page, authenticated = true) {
  if (authenticated) await mockAuthApi(page, { user: TEACHER });
  const api = new TeacherMcqsApi();
  await page.route("**/api/health", (r) =>
    r.fulfill({ json: { status: "ok" } }),
  );
  await page.route(
    (url) => url.pathname.startsWith("/api/teacher/"),
    (r) => api.handle(r),
  );
  return api;
}

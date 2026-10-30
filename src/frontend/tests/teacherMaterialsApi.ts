import type { Page, Route } from "@playwright/test";

export const COURSE_A = "11111111-1111-4111-8111-111111111111";
export const COURSE_B = "22222222-2222-4222-8222-222222222222";
export const TOPIC_A = "33333333-3333-4333-8333-333333333333";
export const TOPIC_B = "44444444-4444-4444-8444-444444444444";
const now = "2026-10-30T00:00:00Z";

export interface Material {
  id: string;
  course_id: string;
  topic_id: string | null;
  uploaded_by: string;
  title: string;
  original_filename: string;
  media_type: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
}

export const OLD: Material = {
  id: "55555555-5555-4555-8555-555555555555",
  course_id: COURSE_A,
  topic_id: null,
  uploaded_by: "demo-teacher",
  title: "Older source",
  original_filename: "architecture.txt",
  media_type: "text/plain; charset=utf-8",
  size_bytes: 12,
  created_at: "2026-10-20T00:00:00Z",
  updated_at: "2026-10-20T00:00:00Z",
};
export const NEW: Material = {
  ...OLD,
  id: "66666666-6666-4666-8666-666666666666",
  topic_id: TOPIC_A,
  title: "Newer testing guide",
  original_filename: "testing-guide.pdf",
  media_type: "application/pdf",
  created_at: now,
  updated_at: now,
};

export class TeacherMaterialsApi {
  materials: Material[] = [NEW, OLD];
  requests: { method: string; path: string; body: string | null }[] = [];
  failCourses = 0;
  failMaterials = 0;
  failUpload = 0;

  async handle(route: Route) {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    const path = url.pathname + url.search;
    const body = request.postData();
    this.requests.push({ method, path, body });
    const json = (status: number, value: unknown) => route.fulfill({ status, json: value });
    const error = (status: number, code: string) =>
      json(status, { detail: { code, message: `Could not load materials: ${code}` } });

    if (method === "GET" && url.pathname === "/api/teacher/courses") {
      if (this.failCourses-- > 0) return error(503, "service_unavailable");
      return json(200, [
        { id: COURSE_A, title: "Software Engineering", created_at: now },
        { id: COURSE_B, title: "Programming", created_at: now },
      ]);
    }
    const topics = url.pathname.match(/^\/api\/teacher\/courses\/([^/]+)\/topics$/);
    if (method === "GET" && topics) {
      return json(200, topics[1] === COURSE_A
        ? [{ id: TOPIC_A, course_id: COURSE_A, name: "Testing", created_at: now }]
        : [{ id: TOPIC_B, course_id: COURSE_B, name: "Basics", created_at: now }]);
    }
    const list = url.pathname.match(/^\/api\/teacher\/courses\/([^/]+)\/materials$/);
    if (method === "GET" && list) {
      if (this.failMaterials-- > 0) return error(503, "service_unavailable");
      const topic = url.searchParams.get("topic_id");
      return json(200, this.materials.filter((m) => m.course_id === list[1] && (!topic || m.topic_id === topic)));
    }
    if (method === "POST" && list) {
      if (this.failUpload-- > 0) return error(503, "service_unavailable");
      const title = body?.match(/name="title"\r?\n\r?\n([^\r\n]+)/)?.[1] ?? "Uploaded source";
      const filename = body?.match(/filename="([^"]+)"/)?.[1] ?? "notes.txt";
      const topic = body?.match(/name="topic_id"\r?\n\r?\n([^\r\n]+)/)?.[1] ?? null;
      const created: Material = {
        ...OLD,
        id: "77777777-7777-4777-8777-777777777777",
        course_id: list[1],
        topic_id: topic,
        title,
        original_filename: filename,
        created_at: "2026-10-31T00:00:00Z",
        updated_at: "2026-10-31T00:00:00Z",
      };
      this.materials.unshift(created);
      return json(201, created);
    }
    const material = url.pathname.match(/^\/api\/teacher\/materials\/([^/]+)(\/file)?$/);
    if (material && method === "PATCH") {
      const index = this.materials.findIndex((m) => m.id === material[1]);
      if (index < 0) return error(404, "not_found");
      const topic_id = JSON.parse(body ?? "{}").topic_id;
      this.materials[index] = { ...this.materials[index], topic_id, updated_at: now };
      return json(200, this.materials[index]);
    }
    if (material && method === "GET" && material[2] === "/file") {
      const found = this.materials.find((m) => m.id === material[1]);
      if (!found) return error(404, "not_found");
      return route.fulfill({
        status: 200,
        contentType: found.media_type,
        headers: { "Content-Disposition": `attachment; filename="${found.original_filename}"` },
        body: "source bytes",
      });
    }
    return error(404, "not_found");
  }
}

export async function mockTeacherMaterialsApi(page: Page) {
  const api = new TeacherMaterialsApi();
  await page.route((url) => url.pathname.startsWith("/api/teacher/"), (route) => api.handle(route));
  return api;
}

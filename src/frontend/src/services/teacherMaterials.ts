import { ApiError, requestTeacher } from "./client";

export type Course = { id: string; title: string; created_at: string };
export type Topic = {
  id: string;
  course_id: string;
  name: string;
  created_at: string;
};
export type Material = {
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
};

const base = "/api/teacher";
export const listTeacherCourses = () =>
  requestTeacher("GET", `${base}/courses`) as Promise<Course[]>;
export const listTeacherTopics = (courseId: string) =>
  requestTeacher("GET", `${base}/courses/${courseId}/topics`) as Promise<
    Topic[]
  >;
export const listTeacherMaterials = (courseId: string, topicId?: string) =>
  requestTeacher(
    "GET",
    `${base}/courses/${courseId}/materials${topicId ? `?topic_id=${encodeURIComponent(topicId)}` : ""}`,
  ) as Promise<Material[]>;
export const uploadTeacherMaterial = (
  courseId: string,
  input: { file: File; title: string; topicId?: string },
) => {
  const form = new FormData();
  form.append("file", input.file);
  form.append("title", input.title);
  if (input.topicId) form.append("topic_id", input.topicId);
  return requestTeacher(
    "POST",
    `${base}/courses/${courseId}/materials`,
    form,
  ) as Promise<Material>;
};
export const setTeacherMaterialTopic = (
  materialId: string,
  topicId: string | null,
) =>
  requestTeacher("PATCH", `${base}/materials/${materialId}`, {
    topic_id: topicId,
  }) as Promise<Material>;
export const downloadTeacherMaterial = (materialId: string) =>
  requestTeacher(
    "GET",
    `${base}/materials/${materialId}/file`,
    undefined,
    true,
  ) as Promise<Blob>;
export { ApiError };

export const deleteTeacherMaterial = (id: string) =>
  requestTeacher("DELETE", `/api/teacher/materials/${id}`);

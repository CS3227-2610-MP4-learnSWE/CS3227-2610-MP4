import { requestTeacher } from "./client";

export type NoteDraftMetadata = {
  id: string;
  course_id: string;
  source_material_id: string;
  created_by: string;
  title: string;
  created_at: string;
};
export type NoteDraft = NoteDraftMetadata & { content: string };

export const listNoteDrafts = (courseId: string) =>
  requestTeacher(
    "GET",
    `/api/teacher/courses/${courseId}/note-drafts`,
  ) as Promise<NoteDraftMetadata[]>;
export const getNoteDraft = (draftId: string) =>
  requestTeacher(
    "GET",
    `/api/teacher/note-drafts/${draftId}`,
  ) as Promise<NoteDraft>;
export const generateNoteDraft = (materialId: string) =>
  requestTeacher(
    "POST",
    `/api/teacher/materials/${materialId}/note-drafts`,
    undefined,
    false,
    45_000,
  ) as Promise<NoteDraft>;

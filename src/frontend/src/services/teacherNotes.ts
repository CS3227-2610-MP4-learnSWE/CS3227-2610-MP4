import { requestTeacher } from "./client";

export type NoteDraftMetadata = {
  id: string;
  course_id: string;
  source_material_id: string;
  created_by: string;
  title: string;
  created_at: string;
  source_title: string;
  version: number;
  updated_at: string;
  updated_by: string;
};
export type NoteDraft = NoteDraftMetadata & { content: string };

export const listNoteDrafts = (courseId: string) =>
  requestTeacher(
    "GET",
    `/api/teacher/courses/${courseId}/note-drafts`,
  ) as Promise<NoteDraftMetadata[]>;
export const getNoteDraft = (draftId: string) =>
  requestTeacher("GET", `/api/teacher/note-drafts/${draftId}`).then(
    decodeDraft,
  );
export const generateNoteDraft = (materialId: string) =>
  requestTeacher(
    "POST",
    `/api/teacher/materials/${materialId}/note-drafts`,
    undefined,
    false,
    45_000,
  ).then(decodeDraft);

export const saveNoteDraft = (
  draftId: string,
  input: { title: string; content: string; version: number },
) =>
  requestTeacher("PATCH", `/api/teacher/note-drafts/${draftId}`, input).then(
    decodeDraft,
  );

function decodeDraft(value: unknown): NoteDraft {
  const draft = value as NoteDraft | null;
  const fields = [
    "id",
    "course_id",
    "source_material_id",
    "created_by",
    "title",
    "created_at",
    "source_title",
    "updated_at",
    "updated_by",
    "content",
  ] as const;
  if (
    !draft ||
    fields.some(
      (key) => typeof draft[key] !== "string" || draft[key].length === 0,
    ) ||
    !Number.isInteger(draft.version) ||
    draft.version < 1 ||
    Array.from(draft.title).length > 200 ||
    Array.from(draft.source_title).length > 200 ||
    Array.from(draft.content).length > 2000 ||
    Number.isNaN(Date.parse(draft.created_at)) ||
    Number.isNaN(Date.parse(draft.updated_at))
  ) {
    throw new Error("The saved draft response was invalid.");
  }
  return draft;
}

export const deleteNoteDraft = (id: string, version: number) =>
  requestTeacher("DELETE", `/api/teacher/note-drafts/${id}?version=${version}`);

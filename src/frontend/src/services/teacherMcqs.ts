import { requestTeacher } from "./client";

export type McqDraftMetadata = {
  id: string;
  course_id: string;
  source_material_id: string;
  source_title: string;
  created_by: string;
  created_at: string;
  question_count: number;
};
export type McqDraftQuestion = {
  id: string;
  position: number;
  question: string;
  choices: string[];
  correct_choice_index: number;
  explanation: string;
};
export type McqDraft = McqDraftMetadata & { questions: McqDraftQuestion[] };

const invalid = () => new Error("The saved MCQ response was invalid.");
function text(value: unknown, max = Infinity): value is string {
  return (
    typeof value === "string" &&
    value.trim().length > 0 &&
    Array.from(value).length <= max &&
    !Array.from(value).some((c) => {
      const code = c.codePointAt(0)!;
      return code === 0 || (code >= 0xd800 && code <= 0xdfff);
    })
  );
}
function metadata(value: unknown): McqDraftMetadata {
  const item = value as McqDraftMetadata | null;
  if (
    !item ||
    ![item.id, item.course_id, item.source_material_id, item.created_by].every(
      (v) => text(v),
    ) ||
    !text(item.source_title, 200) ||
    !text(item.created_at) ||
    Number.isNaN(Date.parse(item.created_at)) ||
    item.question_count !== 3
  )
    throw invalid();
  return item;
}
function detail(value: unknown): McqDraft {
  const item = metadata(value) as McqDraft;
  if (
    !Array.isArray(item.questions) ||
    item.questions.length !== 3 ||
    item.questions.some(
      (q, i) =>
        !q ||
        !text(q.id) ||
        q.position !== i + 1 ||
        !text(q.question, 200) ||
        !text(q.explanation, 200) ||
        !Array.isArray(q.choices) ||
        q.choices.length !== 4 ||
        !q.choices.every((c) => text(c, 80)) ||
        !Number.isInteger(q.correct_choice_index) ||
        q.correct_choice_index < 0 ||
        q.correct_choice_index > 3,
    )
  )
    throw invalid();
  return item;
}
export const listMcqDrafts = (courseId: string) =>
  requestTeacher("GET", `/api/teacher/courses/${courseId}/mcq-drafts`).then(
    (value) => {
      if (!Array.isArray(value)) throw invalid();
      return value.map(metadata);
    },
  );
export const getMcqDraft = (batchId: string) =>
  requestTeacher("GET", `/api/teacher/mcq-drafts/${batchId}`).then(detail);
export const generateMcqDraft = (materialId: string) =>
  requestTeacher(
    "POST",
    `/api/teacher/materials/${materialId}/mcq-drafts`,
    undefined,
    false,
    45_000,
  ).then(detail);

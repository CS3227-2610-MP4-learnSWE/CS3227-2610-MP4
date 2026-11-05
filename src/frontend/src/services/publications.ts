import { ApiError, requestTeacher } from "./client";
import type { McqDraftQuestion } from "./teacherMcqs";

export type PublicationKind = "note" | "practice_set";
export type Publication = {
  id: string;
  kind: PublicationKind;
  course_id: string;
  topic_id: string | null;
  topic_name: string;
  title: string;
  published_at: string;
  source_draft_id: string | null;
  source_version: number | null;
  published_by: string;
  withdrawn: boolean;
  question_count?: number;
};
export type PublicationDetail = Publication & {
  content?: string;
  questions?: McqDraftQuestion[];
};
export type PublishInput = { version: number; title: string; topic_id: string };
const bad = () => new ApiError(0, "bad_response");
const text = (v: unknown): v is string => typeof v === "string" && v.length > 0;
function metadata(value: unknown): Publication {
  const p = value as Publication | null;
  if (
    !p ||
    ![
      p.id,
      p.course_id,
      p.title,
      p.topic_name,
      p.published_by,
      p.published_at,
    ].every(text) ||
    !["note", "practice_set"].includes(p.kind) ||
    Number.isNaN(Date.parse(p.published_at)) ||
    !(p.topic_id === null || text(p.topic_id)) ||
    !(p.source_draft_id === null || text(p.source_draft_id)) ||
    !(
      p.source_version === null ||
      (Number.isInteger(p.source_version) && p.source_version > 0)
    ) ||
    typeof p.withdrawn !== "boolean" ||
    (p.kind === "practice_set" &&
      (p.question_count !== 3 ||
        !p.topic_id ||
        !p.source_draft_id ||
        !p.source_version))
  )
    throw bad();
  return p;
}
function detail(value: unknown): PublicationDetail {
  const p = metadata(value) as PublicationDetail;
  if (p.kind === "note") {
    if (!text(p.content)) throw bad();
  } else if (
    !Array.isArray(p.questions) ||
    p.questions.length !== 3 ||
    p.questions.some(
      (q, i) =>
        !text(q.id) ||
        q.position !== i + 1 ||
        !text(q.question) ||
        !text(q.explanation) ||
        !Array.isArray(q.choices) ||
        q.choices.length !== 4 ||
        !q.choices.every(text) ||
        !Number.isInteger(q.correct_choice_index) ||
        q.correct_choice_index < 0 ||
        q.correct_choice_index > 3,
    )
  )
    throw bad();
  return p;
}
export async function listPublications(course: string): Promise<Publication[]> {
  const data = await requestTeacher(
    "GET",
    `/api/teacher/courses/${encodeURIComponent(course)}/publications`,
  );
  if (!Array.isArray(data)) throw bad();
  return data.map(metadata);
}
export const publicationPath = (p: Publication) =>
  `/teacher/review?${new URLSearchParams({ course: p.course_id, kind: p.kind, publication: p.id })}`;
export async function getPublication(kind: PublicationKind, id: string) {
  return detail(
    await requestTeacher(
      "GET",
      `/api/teacher/${kind === "note" ? "published-notes" : "published-practice-sets"}/${encodeURIComponent(id)}`,
    ),
  );
}
export async function publishDraft(
  kind: PublicationKind,
  id: string,
  input: PublishInput,
) {
  return detail(
    await requestTeacher(
      "POST",
      `/api/teacher/${kind === "note" ? "note-drafts" : "mcq-drafts"}/${encodeURIComponent(id)}/publish`,
      input,
    ),
  );
}
export function publicationError(error: unknown, fallback: string) {
  if (!(error instanceof ApiError) || error.status === 0) return fallback;
  const messages: Record<string, string> = {
    csrf_failed:
      "Your request could not be verified. Refresh the page and try again.",
    forbidden: "You do not have permission to publish or view this content.",
    not_found: "This item is no longer available or you cannot access it.",
    draft_conflict:
      "This draft has changed. Reload and review it before publishing.",
    already_published: "This draft has already been published.",
    validation_error: "Check the title, topic and draft version.",
    service_unavailable: "Published content is unavailable. Please try again.",
  };
  return (
    messages[error.code] || "The publication request failed. Please try again."
  );
}

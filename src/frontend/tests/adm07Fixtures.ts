/**
 * Response bodies for the ADM-07 hub mock (adm07Api.ts): generation, quality and grading-run shapes
 * of workflow/specs/ADM-07/plan.md. Copied unchanged from adm01Api.ts so that adm01Api.ts can be
 * deleted in phase 5 (adm07Api.ts must then import from this file instead).
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Json = any;

export type Workflow = "student_exercise" | "teacher_lesson_planning";

export const DIM_NAMES = [
  "relevance",
  "factual_accuracy",
  "clarity",
  "safety",
] as const;

const unavailable = (reason: string) => ({ state: "unavailable", reason });

export function generationBody(url: URL): Json {
  return {
    period_start: url.searchParams.get("period_start"),
    period_end: url.searchParams.get("period_end"),
    recording_started_on: "2020-01-01",
    workflows: [
      {
        workflow: "study_notes",
        label: "Study notes",
        state: "available",
        reason: null,
        attempts: 9,
        successful: 6,
        unsuccessful: 3,
        rate_percent: 66.7,
      },
      {
        workflow: "mcq_batch",
        label: "MCQ batches",
        state: "not_applicable",
        reason: "no_generation_attempts",
        attempts: 0,
        successful: 0,
        unsuccessful: 0,
        rate_percent: null,
      },
    ],
  };
}

const GRADES = (n: number) =>
  DIM_NAMES.map((dimension, i) => ({
    dimension,
    state:
      dimension === "factual_accuracy" && n % 2 === 0
        ? "unassessable"
        : "graded",
    score:
      dimension === "factual_accuracy" && n % 2 === 0
        ? null
        : 3 + ((n + i) % 3),
    reason:
      dimension === "factual_accuracy" && n % 2 === 0
        ? "No authorised context was available."
        : `Reason ${dimension} ${n}.`,
  }));

export function itemRows(offset: number, limit: number, total: number): Json[] {
  const rows: Json[] = [];
  for (let i = offset; i < Math.min(offset + limit, total); i++) {
    const graded = i === 0;
    rows.push({
      item_id: 1000 + i,
      received_at: "2026-11-08T09:12:44Z",
      status: graded ? "graded" : "pending",
      response_time_ms: 2312,
      failure_code: null,
      graded_at: graded ? "2026-11-09T05:01:10Z" : null,
      grades: graded ? GRADES(1) : [],
    });
  }
  return rows;
}

export function qualityBody(url: URL, total = 2): Json {
  const workflow = (url.searchParams.get("workflow") ??
    "student_exercise") as Workflow;
  const limit = Number(url.searchParams.get("limit") ?? 25);
  const offset = Number(url.searchParams.get("offset") ?? 0);
  const teacher = workflow === "teacher_lesson_planning";
  return {
    workflow,
    period_start: url.searchParams.get("period_start"),
    period_end: url.searchParams.get("period_end"),
    recording_started_on: "2020-01-01",
    grades: {
      state: "available",
      reason: null,
      assessed_count: 12,
      pending_count: 5,
      grading_failed_count: 1,
      content_expired_count: 0,
      privacy_blocked_count: 0,
      privacy_mode: "local_dlp",
      dimensions: [
        {
          dimension: "relevance",
          average: 4.25,
          graded_count: 12,
          unassessable_count: 0,
        },
        {
          dimension: "factual_accuracy",
          average: 3.5,
          graded_count: 6,
          unassessable_count: 6,
        },
        {
          dimension: "clarity",
          average: 4.0,
          graded_count: 12,
          unassessable_count: 0,
        },
        {
          dimension: "safety",
          average: 5.0,
          graded_count: 12,
          unassessable_count: 0,
        },
      ],
    },
    response_time: {
      state: "available",
      reason: null,
      successful_count: 40,
      mean_ms: 2400,
      median_ms: 2100,
      failed_or_incomplete_count: 3,
    },
    sessions: teacher
      ? {
          ...unavailable("no_source"),
          session_count: null,
          average_messages_per_session: null,
          user_messages: null,
          ai_messages: null,
        }
      : {
          state: "available",
          reason: null,
          session_count: 9,
          average_messages_per_session: 6.5,
          user_messages: 30,
          ai_messages: 28,
        },
    activity_time: teacher
      ? {
          ...unavailable("no_source"),
          linked_session_count: null,
          distinct_activity_count: null,
          excluded_session_count: null,
          average_messages_per_session: null,
          average_activity_seconds: null,
          start_event: null,
          end_event: null,
        }
      : {
          state: "available",
          reason: null,
          linked_session_count: 7,
          distinct_activity_count: 6,
          excluded_session_count: 2,
          average_messages_per_session: 7.14,
          average_activity_seconds: 912.5,
          start_event: "Practice attempt started",
          end_event: "Practice attempt submitted",
        },
    items: { total, limit, offset, rows: itemRows(offset, limit, total) },
    active_run: null,
  };
}

export interface Run {
  run_id: number;
  workflow: Workflow;
  period_start: string;
  period_end: string;
  status: "queued" | "running" | "completed" | "failed";
  items_total: number;
  items_graded: number;
  items_failed: number;
  failure_code: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export function run(over: Partial<Run> = {}): Run {
  return {
    run_id: 12,
    workflow: "student_exercise",
    period_start: "2026-10-11",
    period_end: "2026-11-09",
    status: "queued",
    items_total: 3,
    items_graded: 0,
    items_failed: 0,
    failure_code: null,
    created_at: "2026-11-09T05:00:00Z",
    started_at: null,
    finished_at: null,
    ...over,
  };
}

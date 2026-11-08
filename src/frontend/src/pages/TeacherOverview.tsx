import { useEffect, useRef, useState } from "react";
import { Alert, Button, MenuItem, TextField } from "@mui/material";
import { useLocation } from "react-router";
import { useAuth } from "../auth/AuthContext";
import LocalTime from "../components/LocalTime";
import SignInNotice from "../auth/SignInNotice";
import { Panel } from "../components/ui";
import { ApiError, getSessionGeneration } from "../services/client";
import * as api from "../services/teacherOverview";

type View = {
  report: api.Overview | null;
  error: string;
  loading: boolean;
  retry: boolean;
};

const NOTE = [
  "Students are the people enrolled in the course with a student account. Disabled students still count; a student removed from the course no longer appears in any figure.",
  "A lesson counts as completed when the student has it marked complete and the completion time falls inside the period. Lessons marked complete and later unmarked do not count. Only published lessons are included.",
  "Completion rate for a lesson = students who completed it ÷ students enrolled. Lesson completion rate for a course = completions in the period ÷ (students enrolled × published lessons). Percentages are rounded down; Not available means there is nothing to divide by.",
  "Practice results include submitted attempts on the course's published practice sets that were submitted inside the period. Average score uses each student's latest submitted attempt: all correct answers ÷ all answers.",
  "A question is missed when a student's latest attempt answered it incorrectly. Miss rate = missed ÷ answered, rounded down. The five questions with the highest miss rate are listed, ties broken by more misses, then set title, then question number.",
  "Periods use UTC calendar days and include today. All time has no start date. Figures show current enrolment and current records only. Totals are shown, never individual students.",
];

const pct = (value: number | null) =>
  value === null ? "Not available" : `${value}%`;

function LessonTable({ course }: { course: api.OverviewCourse }) {
  const { lessons, student_count: students } = course;
  if (!lessons.length)
    return <p role="status">No lessons are published in this course yet.</p>;
  return (
    <>
      <div
        className="table-scroll teacher-overview-scroll"
        role="region"
        aria-label={`Lesson completion results, ${course.title}`}
        tabIndex={0}
      >
        <table aria-label={`Lesson completion, ${course.title}`}>
          <thead>
            <tr>
              <th scope="col">Lesson</th>
              <th scope="col">Topic</th>
              <th scope="col">Students completed</th>
              <th scope="col">Completion rate</th>
            </tr>
          </thead>
          <tbody>
            {lessons.map((lesson) => (
              <tr key={lesson.lesson_id}>
                <td>{lesson.title}</td>
                <td>{lesson.topic}</td>
                <td>
                  {lesson.completed_students} of {students}
                </td>
                <td>{pct(lesson.rate_percent)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {lessons.every((l) => l.completed_students === 0) && (
        <p role="status">No lessons were completed in this period.</p>
      )}
    </>
  );
}

function PracticeTable({ course }: { course: api.OverviewCourse }) {
  const { sets } = course.practice;
  if (!sets.length)
    return (
      <p role="status">No practice sets are published in this course yet.</p>
    );
  return (
    <>
      <div
        className="table-scroll teacher-overview-scroll"
        role="region"
        aria-label={`Practice set results, ${course.title}`}
        tabIndex={0}
      >
        <table aria-label={`Practice results, ${course.title}`}>
          <thead>
            <tr>
              <th scope="col">Practice set</th>
              <th scope="col">Topic</th>
              <th scope="col">Students attempted</th>
              <th scope="col">Submitted attempts</th>
              <th scope="col">Average score</th>
            </tr>
          </thead>
          <tbody>
            {sets.map((set) => (
              <tr key={set.set_id}>
                <td>{set.title}</td>
                <td>{set.topic}</td>
                <td>{set.students_attempted}</td>
                <td>{set.submitted_attempts}</td>
                <td>{pct(set.average_score_percent)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sets.every((s) => s.submitted_attempts === 0) && (
        <p role="status">No practice attempts were submitted in this period.</p>
      )}
    </>
  );
}

function MissedList({ course }: { course: api.OverviewCourse }) {
  const { sets, missed_questions: missed } = course.practice;
  if (sets.every((s) => s.submitted_attempts === 0))
    return (
      <p role="status">
        No missed questions to show because no practice attempts were submitted
        in this period.
      </p>
    );
  if (!missed.length)
    return <p role="status">No questions were missed in this period.</p>;
  return (
    <ol
      className="teacher-overview-missed"
      aria-label={`Commonly missed questions, ${course.title}`}
    >
      {missed.map((item) => (
        <li key={`${item.set_id}:${item.position}`}>
          <span>
            {item.set_title}, question {item.position}: {item.question}
          </span>
          <small>
            Missed {item.missed} of {item.answered} answers (
            {item.miss_rate_percent}%)
          </small>
        </li>
      ))}
    </ol>
  );
}

function CourseReport({ course }: { course: api.OverviewCourse }) {
  return (
    <Panel className="teacher-overview-panel">
      <h3>{course.title}</h3>
      <p>Students enrolled: {course.student_count}</p>
      <p>Published lessons: {course.lesson_count}</p>
      <p>Lesson completion rate: {pct(course.completion_rate_percent)}</p>
      {course.student_count === 0 ? (
        <p role="status">No students are enrolled in this course yet.</p>
      ) : (
        <>
          <div className="teacher-overview-tables">
            <section>
              <h4>Lesson completion</h4>
              <LessonTable course={course} />
            </section>
            <section>
              <h4>Practice results</h4>
              <PracticeTable course={course} />
            </section>
          </div>
          <h4>Commonly missed questions</h4>
          <MissedList course={course} />
        </>
      )}
    </Panel>
  );
}

function Report() {
  const [period, setPeriod] = useState<api.Period>(api.DEFAULT_PERIOD);
  const applied = useRef<api.Period>(api.DEFAULT_PERIOD);
  const initial = useRef<Promise<api.Overview> | null>(null);
  const serial = useRef(0);
  const [view, setView] = useState<View>({
    report: null,
    error: "",
    loading: true,
    retry: false,
  });

  function load(next: api.Period, pending?: Promise<api.Overview>) {
    const current = ++serial.current;
    const generation = getSessionGeneration();
    applied.current = next;
    setView({ report: null, error: "", loading: true, retry: false });
    void (pending ?? api.readOverview(next))
      .then((report) => {
        if (current === serial.current && generation === getSessionGeneration())
          setView({ report, error: "", loading: false, retry: false });
      })
      .catch((error: unknown) => {
        if (current === serial.current && generation === getSessionGeneration())
          setView({
            report: null,
            error: api.overviewError(error),
            loading: false,
            retry: !(
              error instanceof ApiError &&
              [401, 403, 422].includes(error.status)
            ),
          });
      });
  }

  useEffect(() => {
    // StrictMode reattaches to this one activation read; no private cross-page cache.
    initial.current ??= api.readOverview(applied.current);
    load(applied.current, initial.current);
    return () => {
      serial.current += 1;
    };
  }, []);

  const { report } = view;
  return (
    <section aria-labelledby="teacher-overview-heading">
      <h2 id="teacher-overview-heading">Learning overview</h2>
      <p className="muted">
        Lesson completion, practice results and commonly missed questions for
        the courses you manage. Totals only: no student names or individual
        scores.
      </p>
      <Panel className="teacher-overview-panel">
        <TextField
          select
          label="Reporting period"
          value={period}
          slotProps={{
            select: {
              SelectDisplayProps: {
                "aria-label": "Reporting period",
                "aria-labelledby": undefined,
              },
            },
          }}
          onChange={(event) => {
            const next = event.target.value as api.Period;
            setPeriod(next);
            load(next);
          }}
        >
          {api.OVERVIEW_PERIODS.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
        {report && (
          <>
            <p>{api.periodLine(report.period)}</p>
            <p>
              Data as of <LocalTime value={report.as_of} />
            </p>
          </>
        )}
      </Panel>
      {view.loading && <p role="status">Loading learning overview…</p>}
      {view.error && (
        <Alert
          severity="error"
          action={
            view.retry ? (
              <Button onClick={() => load(applied.current)}>Try again</Button>
            ) : undefined
          }
        >
          {view.error}
        </Alert>
      )}
      {report && (
        <>
          {report.courses.length === 0 && (
            <p role="status">
              You do not manage any courses yet. Ask an administrator to assign
              you to a course.
            </p>
          )}
          {report.courses.map((course) => (
            <CourseReport key={course.course_id} course={course} />
          ))}
          <Panel className="teacher-overview-panel">
            <h3>How these figures are calculated</h3>
            <ul>
              {NOTE.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </Panel>
        </>
      )}
    </section>
  );
}

export default function TeacherOverviewReport() {
  const { status, user } = useAuth();
  const location = useLocation();
  if (status === "loading")
    return <p role="status">Loading learning overview…</p>;
  if (status !== "authenticated")
    return <SignInNotice message="Sign in to view your learning overview." />;
  return (
    <Report key={`${user?.id}:${getSessionGeneration()}:${location.key}`} />
  );
}

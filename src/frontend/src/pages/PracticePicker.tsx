import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Alert, Button } from "@mui/material";
import { EmptyState, PageHeading, Panel } from "../components/ui";
import { useAuth } from "../auth/AuthContext";
import SignInNotice, { isSignInNeeded } from "../auth/SignInNotice";
import { ApiError } from "../services/client";
import {
  listPracticeSets,
  type PracticeCatalogCourse,
} from "../services/practice";
import {
  catalogErrorMessage,
  PRACTICE_FORBIDDEN,
} from "../services/practiceMessages";

type Load =
  | { state: "loading" }
  | { state: "ready"; courses: PracticeCatalogCourse[] }
  | { state: "error"; error: ApiError };

function CourseSets({ course }: { course: PracticeCatalogCourse }) {
  const headingId = `practice-course-${course.id}`;
  return (
    <section aria-labelledby={headingId}>
      <h2 id={headingId}>{course.title}</h2>
      {course.sets.length === 0 ? (
        <p>No practice sets published in this course yet.</p>
      ) : (
        <ul
          aria-label={`Practice sets in ${course.title}`}
          className="practice-set-list"
        >
          {course.sets.map((set) => (
            <li key={set.id}>
              <Panel className="practice-set-row">
                <h3>
                  <Link
                    className="text-link"
                    to={`/student/practice/${set.id}`}
                  >
                    {set.title}
                  </Link>
                </h3>
                <p>Topic: {set.topic.name}</p>
                <p>
                  {set.best
                    ? `Best score: ${set.best.correct} / ${set.best.total}`
                    : "No attempts yet"}
                </p>
              </Panel>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function PracticePicker() {
  const demoMode = useAuth().status === "anonymous";
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let current = true;
    setLoad({ state: "loading" });
    listPracticeSets().then(
      (courses) => current && setLoad({ state: "ready", courses }),
      (error) =>
        current &&
        setLoad({
          state: "error",
          error: error instanceof ApiError ? error : new ApiError(0, "network"),
        }),
    );
    return () => {
      current = false;
    };
  }, [attempt]);

  const heading = (
    <PageHeading
      eyebrow="UNDERSTAND IT. THEN TRY IT."
      title="Choose a practice set"
      description="Pick a set your teacher has published for one of your courses."
    />
  );
  let body;
  if (load.state === "loading")
    body = <p role="status">Loading practice sets…</p>;
  else if (load.state === "error") {
    const message = catalogErrorMessage(load.error);
    if (isSignInNeeded(load.error))
      body = demoMode ? (
        <SignInNotice message="Sign in to see your practice sets." />
      ) : null;
    else
      body = (
        <Alert
          severity="error"
          sx={{ my: 2 }}
          action={
            message === PRACTICE_FORBIDDEN ? undefined : (
              <Button
                color="inherit"
                size="small"
                onClick={() => setAttempt((n) => n + 1)}
              >
                Try again
              </Button>
            )
          }
        >
          {message}
        </Alert>
      );
  } else if (load.courses.length === 0)
    body = (
      <EmptyState title="Join a course to start">
        You are not enrolled in any course yet. Ask your teacher or an
        administrator to add you, and practice sets will appear here.
      </EmptyState>
    );
  else
    body = load.courses.map((course) => (
      <CourseSets key={course.id} course={course} />
    ));
  return (
    <>
      {heading}
      {body}
    </>
  );
}

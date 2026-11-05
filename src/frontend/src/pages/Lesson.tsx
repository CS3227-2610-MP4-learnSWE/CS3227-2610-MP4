import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { Alert, Button } from "@mui/material";
import { ArrowLeft, Check, Sparkles } from "lucide-react";
import { EmptyState, PageHeading, Panel, PrimaryLink } from "../components/ui";
import { useAuth } from "../auth/AuthContext";
import SignInNotice, { isSignInNeeded } from "../auth/SignInNotice";
import { useCompanion } from "../components/StudyCompanion";
import { ApiError } from "../services/client";
import {
  getLesson,
  setCompletion,
  type LessonDetail,
} from "../services/lessons";
import { lessonErrorMessage } from "../services/lessonMessages";

type Load =
  | { state: "loading" }
  | { state: "ready"; lesson: LessonDetail }
  | { state: "missing" }
  | { state: "error"; error: ApiError };

const asError = (error: unknown) =>
  error instanceof ApiError ? error : new ApiError(0, "network");

export default function Lesson({ id }: { id: string }) {
  const demoMode = useAuth().status === "anonymous";
  const { setOpen } = useCompanion();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  // Synchronous guard: two quick clicks must send one request.
  const inFlight = useRef(false);
  useEffect(() => {
    let current = true;
    setLoad({ state: "loading" });
    setNotice(null);
    setFailure(null);
    getLesson(id).then(
      (lesson) => current && setLoad({ state: "ready", lesson }),
      (error) => {
        if (!current) return;
        const failed = asError(error);
        setLoad(
          failed.status === 404 || failed.status === 422
            ? { state: "missing" }
            : { state: "error", error: failed },
        );
      },
    );
    return () => {
      current = false;
    };
  }, [id, attempt]);

  const listLink =
    load.state === "ready"
      ? `/student/materials?course=${encodeURIComponent(load.lesson.course.id)}`
      : "/student/materials";
  const back = (
    <Link className="back-link" to={listLink}>
      <ArrowLeft size={16} /> All study materials
    </Link>
  );

  if (load.state === "loading")
    return (
      <>
        {back}
        <div role="status">Loading lesson…</div>
      </>
    );
  if (load.state === "missing")
    return (
      <>
        {back}
        <EmptyState title="Lesson not found">
          <Link to="/student/materials">Return to materials</Link>
        </EmptyState>
      </>
    );
  if (load.state === "error") {
    const { error } = load;
    return (
      <>
        {back}
        {isSignInNeeded(error) ? (
          demoMode && (
            <SignInNotice message="Sign in to read study materials and track your progress." />
          )
        ) : (
          <Alert
            severity="error"
            sx={{ my: 2 }}
            action={
              error.status === 403 ? undefined : (
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
            {lessonErrorMessage(error, "load")}
          </Alert>
        )}
      </>
    );
  }

  const { lesson } = load;
  const toggle = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setSaving(true);
    setNotice(null);
    setFailure(null);
    try {
      const result = await setCompletion(lesson.id, !lesson.completed);
      setLoad({
        state: "ready",
        lesson: {
          ...lesson,
          completed: result.completed,
          completed_at: result.completed_at,
        },
      });
      setNotice(
        result.completed ? "Marked as complete." : "Marked as incomplete.",
      );
    } catch (caught) {
      const error = asError(caught);
      if (error.status === 404) setLoad({ state: "missing" });
      else setFailure(lessonErrorMessage(error, "save"));
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  };
  return (
    <>
      {back}
      <PageHeading
        eyebrow={`${lesson.topic.name} · ${lesson.course.title}`.toUpperCase()}
        title={lesson.title}
        action={
          <Button
            variant={lesson.completed ? "outlined" : "contained"}
            startIcon={<Check size={17} />}
            disabled={saving}
            onClick={toggle}
          >
            {saving
              ? "Saving…"
              : lesson.completed
                ? "Mark as incomplete"
                : "Mark as complete"}
          </Button>
        }
      />
      {notice && <div role="status">{notice}</div>}
      {failure && (
        <Alert severity="error" sx={{ my: 2 }}>
          {failure}
        </Alert>
      )}
      <Panel className="lesson-reader">
        <div
          role="region"
          aria-label="Lesson content"
          style={{ whiteSpace: "pre-wrap" }}
        >
          {lesson.content}
        </div>
        <PrimaryLink to="/student/practice">Try the practice set</PrimaryLink>
        <Button
          onClick={() => setOpen(true)}
          startIcon={<Sparkles size={16} />}
        >
          Ask your companion
        </Button>
      </Panel>
    </>
  );
}

import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router";
import { Alert, Button } from "@mui/material";
import { EmptyState, PageHeading, Panel } from "../components/ui";
import { useAuth } from "../auth/AuthContext";
import SignInNotice from "../auth/SignInNotice";
import { ApiError } from "../services/client";
import {
  getProgress,
  type Progress as ProgressData,
  type ProgressTopic,
} from "../services/progress";
import { progressErrorMessage } from "../services/progressMessages";

type Load =
  | { state: "loading" }
  | { state: "ready"; data: ProgressData; key: string }
  | { state: "error"; error: ApiError };

const asError = (error: unknown) =>
  error instanceof ApiError ? error : new ApiError(0, "network");

function LessonSection({ lessons }: { lessons: ProgressData["lessons"] }) {
  return (
    <section aria-labelledby="progress-lessons">
      <h2 id="progress-lessons">Lesson progress</h2>
      {lessons.courses.length === 0 ? (
        <EmptyState title="Join a course to start">
          You are not enrolled in any course yet. Ask your teacher or an
          administrator to add you, and your lesson progress will appear here.
        </EmptyState>
      ) : (
        <>
          <ul className="progress-list" aria-label="Courses">
            {lessons.courses.map((course) => (
              <li key={course.id}>
                <strong>{course.title}</strong>
                <span>
                  {course.lesson_count === 0
                    ? "No lessons published yet."
                    : `${course.completed_count} of ${course.lesson_count} lessons complete`}
                </span>
                <div className="progress-bar" aria-hidden="true">
                  <div
                    style={{
                      width: `${course.lesson_count === 0 ? 0 : Math.floor((course.completed_count * 100) / course.lesson_count)}%`,
                    }}
                  />
                </div>
              </li>
            ))}
          </ul>
          {lessons.recent.length === 0 ? (
            <>
              <p>No lessons completed yet.</p>
              <Link to="/student/materials">Open study materials</Link>
            </>
          ) : (
            <ul className="progress-list" aria-label="Recently completed">
              {lessons.recent.map((lesson) => (
                <li key={lesson.lesson_id}>
                  <Link to={`/student/materials/${lesson.lesson_id}`}>
                    {lesson.title}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

function PracticeSection({ practice }: { practice: ProgressData["practice"] }) {
  return (
    <section aria-labelledby="progress-practice">
      <h2 id="progress-practice">Practice scores</h2>
      {practice.sets.length === 0 ? (
        <EmptyState title="No practice results yet">
          <span>Submit a practice set to see your scores here.</span>
          <br />
          <Link to="/student/practice">Go to practice</Link>
        </EmptyState>
      ) : (
        <div className="table-scroll">
          <table aria-label="Practice scores">
            <thead>
              <tr>
                <th scope="col">Practice set</th>
                <th scope="col">Best score</th>
                <th scope="col">Latest score</th>
                <th scope="col">Submitted attempts</th>
              </tr>
            </thead>
            <tbody>
              {practice.sets.map((set) => (
                <tr key={set.set_id}>
                  <td>{set.title}</td>
                  <td>
                    {set.best.correct} / {set.best.total}
                  </td>
                  <td>
                    {set.latest.correct} / {set.latest.total}
                  </td>
                  <td>{set.attempts_submitted}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function TopicList({
  label,
  items,
  min,
}: {
  label: string;
  items: ProgressTopic[];
  min: number;
}) {
  if (items.length === 0) return null;
  return (
    <ul className="progress-list" aria-label={label}>
      {items.map((item) => (
        <li key={item.topic.id ?? "general"}>
          {item.status === "insufficient"
            ? `${item.topic.name}: only ${item.answered} of ${min} answers so far, not enough activity yet.`
            : `${item.topic.name}: ${item.correct} of ${item.answered} correct (${item.accuracy_percent}%)`}
        </li>
      ))}
    </ul>
  );
}

function TopicSection({
  topics,
  hasPractice,
}: {
  topics: ProgressData["topics"];
  hasPractice: boolean;
}) {
  const { rule, items } = topics;
  const ofStatus = (status: ProgressTopic["status"]) =>
    items.filter((item) => item.status === status);
  const weak = ofStatus("needs_practice");
  const insufficient = ofStatus("insufficient");
  const allInsufficient =
    items.length > 0 && insufficient.length === items.length;
  return (
    <section aria-labelledby="progress-topics">
      <h2 id="progress-topics">Topics to revise</h2>
      <p>
        A topic needs practice when you have answered at least{" "}
        {rule.min_answers} questions on it and fewer than{" "}
        {rule.weak_below_percent}% were correct. Only your latest submitted
        attempt on each practice set counts.
      </p>
      {!hasPractice && items.length === 0 ? (
        <EmptyState title="Nothing to revise yet">
          Topics appear here after you submit a practice set.
        </EmptyState>
      ) : (
        <>
          {items.length > 0 && weak.length === 0 && !allInsufficient && (
            <p>No topics need extra practice right now.</p>
          )}
          <TopicList
            label="Topics to revise"
            items={weak}
            min={rule.min_answers}
          />
          {allInsufficient && (
            <EmptyState title="Not enough activity yet">
              Topics are suggested once you have answered at least{" "}
              {rule.min_answers} questions on them. Keep practising and check
              back.
            </EmptyState>
          )}
          <TopicList
            label="Not enough activity yet"
            items={insufficient}
            min={rule.min_answers}
          />
          <TopicList
            label="On track"
            items={ofStatus("on_track")}
            min={rule.min_answers}
          />
        </>
      )}
    </section>
  );
}

function Failure({
  error,
  demoMode,
  onRetry,
}: {
  error: ApiError;
  demoMode: boolean;
  onRetry: () => void;
}) {
  const message = progressErrorMessage(error);
  if (message === null)
    return demoMode ? (
      <SignInNotice message="Sign in to see your lessons and practice progress." />
    ) : null;
  return (
    <Alert
      severity="error"
      sx={{ my: 2 }}
      action={
        error.status === 403 ? undefined : (
          <Button color="inherit" size="small" onClick={onRetry}>
            Try again
          </Button>
        )
      }
    >
      {message}
    </Alert>
  );
}

export default function Progress() {
  const { key: locationKey } = useLocation();
  const { status, user } = useAuth();
  const demoMode = status === "anonymous";
  const userKey = user?.id ?? "";
  const keyRef = useRef(userKey);
  keyRef.current = userKey;
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  // Rapid history navigation can return before React commits an unmount.
  // Each history entry must still load fresh progress.
  useEffect(() => {
    let current = true;
    setLoad({ state: "loading" });
    const key = keyRef.current;
    getProgress().then(
      (data) => current && setLoad({ state: "ready", data, key }),
      (error) => current && setLoad({ state: "error", error: asError(error) }),
    );
    return () => {
      current = false;
    };
  }, [attempt, locationKey]);
  return (
    <>
      <PageHeading
        eyebrow="HOW YOU ARE DOING"
        title="Your progress"
        description="Your completed lessons, practice scores and the topics worth another look."
      />
      {(load.state === "loading" ||
        (load.state === "ready" && load.key !== userKey)) && (
        <div role="status">Loading your progress…</div>
      )}
      {load.state === "error" && (
        <Failure
          error={load.error}
          demoMode={demoMode}
          onRetry={() => setAttempt((n) => n + 1)}
        />
      )}
      {load.state === "ready" && load.key === userKey && (
        <div className="progress-sections">
          <Panel>
            <LessonSection lessons={load.data.lessons} />
          </Panel>
          <Panel>
            <PracticeSection practice={load.data.practice} />
          </Panel>
          <Panel>
            <TopicSection
              topics={load.data.topics}
              hasPractice={load.data.practice.sets.length > 0}
            />
          </Panel>
        </div>
      )}
    </>
  );
}

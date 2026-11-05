import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { Alert, Button, TextField } from "@mui/material";
import { CheckCircle2 } from "lucide-react";
import {
  ArrowBadge,
  CourseArt,
  EmptyState,
  PageHeading,
} from "../components/ui";
import { useAuth } from "../auth/AuthContext";
import SignInNotice, { isSignInNeeded } from "../auth/SignInNotice";
import { ApiError } from "../services/client";
import {
  listCourseLessons,
  listCourses,
  type CourseSummary,
  type TopicGroup,
} from "../services/lessons";
import { lessonErrorMessage } from "../services/lessonMessages";

const ALL = "all";
const topicKey = (topic: TopicGroup) => topic.id ?? "general";

type Load<T> =
  | { state: "loading" }
  | { state: "ready"; data: T }
  | { state: "error"; error: ApiError };

const asError = (error: unknown) =>
  error instanceof ApiError ? error : new ApiError(0, "network");

function Loading() {
  return <div role="status">Loading study materials…</div>;
}

/** The shared failure panel: a message, and "Try again" unless retrying cannot help. */
function Failure({
  error,
  onRetry,
  demoMode,
}: {
  error: ApiError;
  onRetry: () => void;
  demoMode: boolean;
}) {
  if (isSignInNeeded(error))
    return demoMode ? (
      <SignInNotice message="Sign in to read study materials and track your progress." />
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
      {lessonErrorMessage(error, "load")}
    </Alert>
  );
}

function LessonCards({
  topics,
  search,
  filter,
}: {
  topics: TopicGroup[];
  search: string;
  filter: string;
}) {
  const needle = search.trim().toLowerCase();
  const shown = topics
    .filter((topic) => filter === ALL || topicKey(topic) === filter)
    .flatMap((topic) =>
      topic.lessons
        .filter((lesson) => lesson.title.toLowerCase().includes(needle))
        .map((lesson) => ({ topic, lesson })),
    );
  if (shown.length === 0)
    return (
      <EmptyState title="Nothing here just yet">
        Try another topic or a different search.
      </EmptyState>
    );
  return (
    <div className="material-grid">
      {shown.map(({ topic, lesson }) => (
        <Link
          key={lesson.id}
          to={`/student/materials/${lesson.id}`}
          className="lesson-card"
        >
          <CourseArt />
          <div className="lesson-card-body">
            <div className="lesson-meta">
              <span>{topic.name}</span>
            </div>
            <h3>{lesson.title}</h3>
            <p>{lesson.excerpt}</p>
            <div className="lesson-card-bottom">
              <span>
                {lesson.completed ? (
                  <>
                    <CheckCircle2 size={14} /> Complete
                  </>
                ) : (
                  "Start learning"
                )}
              </span>
              <ArrowBadge />
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}

function CourseLessons({
  courseId,
  demoMode,
}: {
  courseId: string;
  demoMode: boolean;
}) {
  const [load, setLoad] = useState<Load<TopicGroup[]>>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [filter, setFilter] = useState(ALL);
  const [search, setSearch] = useState("");
  useEffect(() => {
    let current = true;
    setLoad({ state: "loading" });
    listCourseLessons(courseId).then(
      (result) => current && setLoad({ state: "ready", data: result.topics }),
      (error) => current && setLoad({ state: "error", error: asError(error) }),
    );
    return () => {
      current = false;
    };
  }, [courseId, attempt]);
  if (load.state === "loading") return <Loading />;
  if (load.state === "error") {
    if (load.error.status === 404)
      return (
        <Alert severity="error" sx={{ my: 2 }}>
          This course is not available to you.
        </Alert>
      );
    return (
      <Failure
        error={load.error}
        demoMode={demoMode}
        onRetry={() => setAttempt((n) => n + 1)}
      />
    );
  }
  const topics = load.data;
  if (topics.length === 0)
    return (
      <EmptyState title="No lessons published yet">
        Your teacher has not published lessons in this course yet. Check back
        soon.
      </EmptyState>
    );
  const all = topics.flatMap((topic) => topic.lessons);
  const done = all.filter((lesson) => lesson.completed).length;
  const filters = [
    { key: ALL, name: "All topics" },
    ...topics.map((topic) => ({ key: topicKey(topic), name: topic.name })),
  ];
  return (
    <>
      <div className="toolbar">
        <div className="filter-buttons">
          {filters.map((item) => (
            <Button
              key={item.key}
              onClick={() => setFilter(item.key)}
              variant={item.key === filter ? "contained" : "text"}
              size="small"
              aria-pressed={item.key === filter}
            >
              {item.name}
            </Button>
          ))}
        </div>
        <TextField
          label="Search materials"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ maxWidth: 240 }}
        />
      </div>
      <p>
        {done} of {all.length} lessons complete
      </p>
      <LessonCards topics={topics} search={search} filter={filter} />
    </>
  );
}

export default function Materials() {
  const demoMode = useAuth().status === "anonymous";
  const [params, setParams] = useSearchParams();
  const [courses, setCourses] = useState<Load<CourseSummary[]>>({
    state: "loading",
  });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let current = true;
    setCourses({ state: "loading" });
    listCourses().then(
      (result) =>
        current && setCourses({ state: "ready", data: result.courses }),
      (error) =>
        current && setCourses({ state: "error", error: asError(error) }),
    );
    return () => {
      current = false;
    };
  }, [attempt]);
  const heading = (
    <PageHeading
      eyebrow="A LIBRARY FOR YOUR CURIOSITY"
      title="Small lessons. Lasting understanding."
      description="Explore the ideas behind better software, one topic at a time."
    />
  );
  if (courses.state === "loading")
    return (
      <>
        {heading}
        <Loading />
      </>
    );
  if (courses.state === "error")
    return (
      <>
        {heading}
        <Failure
          error={courses.error}
          demoMode={demoMode}
          onRetry={() => setAttempt((n) => n + 1)}
        />
      </>
    );
  if (courses.data.length === 0)
    return (
      <>
        {heading}
        <EmptyState title="No courses yet">
          You are not enrolled in any course yet. Ask your teacher or an
          administrator to add you.
        </EmptyState>
      </>
    );
  const selected =
    courses.data.find((course) => course.id === params.get("course")) ??
    courses.data[0];
  return (
    <>
      {heading}
      <TextField
        select
        label="Course"
        value={selected.id}
        onChange={(e) => setParams({ course: e.target.value })}
        sx={{ minWidth: 240, my: 1 }}
        slotProps={{ select: { native: true } }}
      >
        {courses.data.map((course) => (
          <option key={course.id} value={course.id}>
            {course.title}
          </option>
        ))}
      </TextField>
      <CourseLessons
        key={selected.id}
        courseId={selected.id}
        demoMode={demoMode}
      />
    </>
  );
}

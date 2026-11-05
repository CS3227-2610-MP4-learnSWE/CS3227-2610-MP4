import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { Button, MenuItem, TextField } from "@mui/material";
import { PageHeading, Panel } from "../components/ui";
import PublicationContent from "../components/PublicationContent";
import { usePublications } from "../hooks/usePublications";
import { listTeacherCourses, type Course } from "../services/teacherMaterials";
import {
  getPublication,
  publicationError,
  type PublicationDetail,
  type PublicationKind,
} from "../services/publications";
export default function PublishedContent() {
  const [params, setParams] = useSearchParams();
  const [courses, setCourses] = useState<Course[]>([]);
  const [coursesError, setCoursesError] = useState("");
  const [coursesLoading, setCoursesLoading] = useState(true);
  const [courseRetry, setCourseRetry] = useState(0);
  const course = courses.some((item) => item.id === params.get("course"))
    ? params.get("course")!
    : courses[0]?.id || "";
  const publications = usePublications(course);
  const filter = params.get("type") || "";
  const kind = params.get("kind");
  const id = params.get("publication") || "";
  const [detail, setDetail] = useState<PublicationDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    let active = true;
    setCoursesLoading(true);
    setCoursesError("");
    listTeacherCourses()
      .then((items) => {
        if (active) setCourses(items);
      })
      .catch((reason) => {
        if (active)
          setCoursesError(
            publicationError(
              reason,
              "Could not load courses. Please try again.",
            ),
          );
      })
      .finally(() => {
        if (active) setCoursesLoading(false);
      });
    return () => {
      active = false;
    };
  }, [courseRetry]);
  useEffect(() => {
    let active = true;
    setDetail(null);
    setError("");
    setLoading(false);
    if (!course || !id || !["note", "practice_set"].includes(kind || ""))
      return;
    setLoading(true);
    getPublication(kind as PublicationKind, id)
      .then((item) => {
        if (!active) return;
        if (item.course_id !== course || item.id !== id || item.kind !== kind)
          throw new Error("Unexpected publication");
        setDetail(item);
      })
      .catch((reason) => {
        if (active)
          setError(
            publicationError(
              reason,
              "Could not load this published version. Please try again.",
            ),
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [course, id, kind, retry]);
  const clear = () => {
    const next = new URLSearchParams(params);
    next.delete("kind");
    next.delete("publication");
    setParams(next);
    heading.current?.focus();
  };
  return (
    <>
      <PageHeading
        eyebrow="SAVED VERSIONS"
        title="Published content"
        description="Immutable published lessons and complete three-question practice sets."
      />
      {coursesLoading && <p role="status">Loading courses…</p>}
      {coursesError && (
        <div role="alert">
          {coursesError}
          <Button onClick={() => setCourseRetry((value) => value + 1)}>
            Retry
          </Button>
        </div>
      )}
      <div className="studio-layout notes-studio">
        <Panel className="notes-list">
          <h2 ref={heading} tabIndex={-1}>
            Published items
          </h2>
          <TextField
            select
            fullWidth
            label="Course"
            value={course}
            disabled={coursesLoading}
            onChange={(event) => setParams({ course: event.target.value })}
          >
            {courses.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.title}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            fullWidth
            label="Content type"
            value={filter}
            onChange={(event) => {
              const next = new URLSearchParams(params);
              if (event.target.value) next.set("type", event.target.value);
              else next.delete("type");
              setParams(next);
            }}
          >
            <MenuItem value="">All content</MenuItem>
            <MenuItem value="note">Notes</MenuItem>
            <MenuItem value="practice_set">Practice sets</MenuItem>
          </TextField>
          {publications.loading && (
            <p role="status">Loading published content…</p>
          )}
          {publications.error && (
            <div role="alert">
              {publications.error.replace(
                "publication status",
                "published content",
              )}
              <Button onClick={publications.retry}>Retry</Button>
            </div>
          )}
          {publications.ready && !publications.items.length && (
            <p>No published content yet.</p>
          )}
          <ul>
            {publications.items
              .filter((item) => !filter || item.kind === filter)
              .map((item) => (
                <li key={`${item.kind}/${item.id}`}>
                  <Button
                    onClick={() => {
                      const next = new URLSearchParams(params);
                      next.set("course", course);
                      next.set("kind", item.kind);
                      next.set("publication", item.id);
                      setParams(next);
                    }}
                  >
                    Open {item.title}
                  </Button>
                  <small>
                    {item.topic_name}
                    {item.withdrawn ? " · Withdrawn" : ""}
                  </small>
                </li>
              ))}
          </ul>
        </Panel>
        <Panel className="notes-viewer">
          {loading && <p role="status">Loading published version…</p>}
          {error && (
            <div role="alert">
              {error}
              <Button onClick={() => setRetry((value) => value + 1)}>
                Retry
              </Button>
              <Button onClick={clear}>Clear publication selection</Button>
            </div>
          )}
          {!loading && !error && detail && <PublicationContent item={detail} />}
          {!loading && !error && !detail && (
            <p>Choose a published item to view it.</p>
          )}
        </Panel>
      </div>
    </>
  );
}

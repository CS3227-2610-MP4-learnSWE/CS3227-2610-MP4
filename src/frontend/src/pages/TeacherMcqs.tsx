import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { Button, MenuItem, TextField } from "@mui/material";
import { FileText, Sparkles } from "lucide-react";
import {
  EmptyState,
  PageHeading,
  Panel,
  PreviewNote,
  Tag,
} from "../components/ui";
import { teacherGenerationError } from "../services/teacherGeneration";
import {
  listTeacherCourses,
  listTeacherMaterials,
  type Course,
  type Material,
} from "../services/teacherMaterials";
import {
  generateMcqDraft,
  getMcqDraft,
  listMcqDrafts,
  type McqDraft,
  type McqDraftMetadata,
} from "../services/teacherMcqs";

export default function TeacherMcqs() {
  const [params, setParams] = useSearchParams();
  const queryCourse = params.get("course") || "";
  const draftId = params.get("batch") || "";
  const [courses, setCourses] = useState<Course[]>([]);
  const [coursesReady, setCoursesReady] = useState(false);
  const [coursesError, setCoursesError] = useState("");
  const [coursesReload, setCoursesReload] = useState(0);
  const [resources, setResources] = useState<{
    course: string;
    materials: Material[];
    drafts: McqDraftMetadata[];
  }>({ course: "", materials: [], drafts: [] });
  const [resourcesLoading, setResourcesLoading] = useState(false);
  const [resourcesError, setResourcesError] = useState("");
  const [reload, setReload] = useState(0);
  const [sourceId, setSourceId] = useState("");
  const [draft, setDraft] = useState<McqDraft | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftError, setDraftError] = useState("");
  const [draftReload, setDraftReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const courseId =
    coursesReady && (!queryCourse || courses.some((c) => c.id === queryCourse))
      ? queryCourse || courses[0]?.id || ""
      : "";
  const viewKey = `${courseId}/${sourceId}/${draftId}`;
  const currentView = useRef(viewKey);
  currentView.current = viewKey;
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    setCoursesError("");
    setCoursesReady(false);
    listTeacherCourses()
      .then((items) => {
        if (!active) return;
        setCourses(items);
        setCoursesReady(true);
      })
      .catch(() => {
        if (active)
          setCoursesError("Could not load courses. Please try again.");
      });
    return () => {
      active = false;
    };
  }, [coursesReload]);

  useEffect(() => {
    setSourceId("");
    setError("");
    setSuccess("");
  }, [courseId]);

  useEffect(() => {
    let active = true;
    setResourcesError("");
    if (!courseId) {
      setResourcesLoading(false);
      return;
    }
    setResourcesLoading(true);
    Promise.all([listTeacherMaterials(courseId), listMcqDrafts(courseId)])
      .then(([materials, drafts]) => {
        if (!active) return;
        setResources({ course: courseId, materials, drafts });
        setSourceId((previous) =>
          materials.some((m) => m.id === previous)
            ? previous
            : materials[0]?.id || "",
        );
      })
      .catch(() => {
        if (active)
          setResourcesError(
            "Could not load sources and saved drafts. Please try again.",
          );
      })
      .finally(() => {
        if (active) setResourcesLoading(false);
      });
    return () => {
      active = false;
    };
  }, [courseId, reload]);

  useEffect(() => {
    let active = true;
    setDraft(null);
    setDraftError("");
    if (!courseId || !draftId) {
      setDraftLoading(false);
      return;
    }
    setDraftLoading(true);
    getMcqDraft(draftId)
      .then((item) => {
        if (!active) return;
        if (item.course_id !== courseId || item.id !== draftId)
          throw new Error("Wrong draft");
        setDraft(item);
      })
      .catch(() => {
        if (active)
          setDraftError(
            "Could not load this draft. Check your course access or try again.",
          );
      })
      .finally(() => {
        if (active) setDraftLoading(false);
      });
    return () => {
      active = false;
    };
  }, [courseId, draftId, draftReload]);

  const materials = resources.course === courseId ? resources.materials : [];
  const drafts = resources.course === courseId ? resources.drafts : [];
  const shownDraft =
    draft?.course_id === courseId && draft.id === draftId ? draft : null;
  const changeCourse = (id: string) => {
    setParams(id ? { tab: "questions", course: id } : { tab: "questions" });
  };
  const generate = async () => {
    if (busyRef.current || !courseId || !sourceId) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    setSuccess("");
    const startedView = viewKey;
    try {
      const created = await generateMcqDraft(sourceId);
      if (!mounted.current || currentView.current !== startedView) return;
      if (
        created.course_id !== courseId ||
        created.source_material_id !== sourceId
      )
        throw new Error("Unexpected draft");
      setParams({ tab: "questions", course: courseId, batch: created.id });
      setSuccess("Draft MCQs generated and saved.");
      setReload((value) => value + 1);
    } catch (reason) {
      if (mounted.current && currentView.current === startedView)
        setError(teacherGenerationError(reason, "MCQs"));
    } finally {
      busyRef.current = false;
      if (mounted.current) setBusy(false);
    }
  };
  const demoEnabled =
    import.meta.env.VITE_APP_ENV === "development" &&
    import.meta.env.VITE_ALLOW_DEMO_IDENTITY === "true";

  return (
    <>
      <PageHeading
        eyebrow="A HEAD START, NOT A REPLACEMENT"
        title="AI content studio"
        description="Turn a private source material into three concise, unpublished draft MCQs."
      />
      <PreviewNote>
        Development identity:{" "}
        {demoEnabled
          ? import.meta.env.VITE_DEMO_USER_ID || "demo-teacher"
          : "disabled (configure local .env)"}
        . Local testing only; this is not a real login.
      </PreviewNote>
      {coursesError && (
        <div className="library-status" role="alert">
          {coursesError}
          <Button onClick={() => setCoursesReload((n) => n + 1)}>Retry</Button>
        </div>
      )}
      {!coursesReady && !coursesError && <p role="status">Loading courses…</p>}
      {coursesReady && queryCourse && !courseId && (
        <div className="library-status" role="alert">
          This course is unavailable. Choose a managed course below.
        </div>
      )}
      {coursesReady && !courses.length && (
        <EmptyState title="No courses yet">
          You do not manage a course.
        </EmptyState>
      )}
      <div className="studio-layout notes-studio">
        <div className="notes-sidebar">
          <Panel className="studio-controls">
            <span className="icon-box purple">
              <Sparkles size={23} />
            </span>
            <h2>Generate practice questions</h2>
            <TextField
              select
              label="Course"
              value={courseId}
              onChange={(event) => changeCourse(event.target.value)}
              disabled={!coursesReady || busy}
            >
              {courses.map((course) => (
                <MenuItem key={course.id} value={course.id}>
                  {course.title}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Source material"
              value={materials.some((m) => m.id === sourceId) ? sourceId : ""}
              onChange={(event) => {
                setSourceId(event.target.value);
                setError("");
                setSuccess("");
              }}
              disabled={busy || resourcesLoading || !materials.length}
            >
              {materials.map((material) => (
                <MenuItem key={material.id} value={material.id}>
                  {material.title}
                </MenuItem>
              ))}
            </TextField>
            <p>
              UTF-8 text or text-based PDF: up to 8,000 characters and 100
              pages. Scanned PDFs need a text-based source.
            </p>
            <p>Generation sends the selected source text to the SoC LLM.</p>
            <p>
              AI-generated questions may be inaccurate. Review every question
              before use.
            </p>
            {!resourcesLoading &&
              courseId &&
              resources.course === courseId &&
              !materials.length && (
                <p>
                  Upload a source material to generate MCQs.{" "}
                  <Link to="/teacher/materials">Open materials library</Link>
                </p>
              )}
            <Button
              fullWidth
              variant="contained"
              startIcon={<Sparkles size={17} />}
              disabled={busy || !sourceId || !courseId || resourcesLoading}
              onClick={generate}
            >
              {busy ? "Generating…" : "Generate 3 draft MCQs"}
            </Button>
            <p>
              If a response is lost, generating again may create another saved
              batch.
            </p>
            {busy && <p role="status">Generating draft MCQs…</p>}
            {error && <p role="alert">{error}</p>}
            {success && <p role="status">{success}</p>}
          </Panel>
          <Panel className="notes-list">
            <h2>Saved MCQ batches</h2>
            {resourcesLoading && (
              <p role="status">Loading sources and saved drafts…</p>
            )}
            {resourcesError && (
              <div role="alert">
                {resourcesError}
                <Button onClick={() => setReload((n) => n + 1)}>Retry</Button>
              </div>
            )}
            {!resourcesLoading &&
              !resourcesError &&
              courseId &&
              !drafts.length && <p>No saved MCQ batches yet</p>}
            <ul>
              {drafts.map((item) => (
                <li key={item.id}>
                  <Button
                    startIcon={<FileText size={16} />}
                    disabled={busy}
                    onClick={() =>
                      setParams({
                        tab: "questions",
                        course: courseId,
                        batch: item.id,
                      })
                    }
                    aria-pressed={draftId === item.id}
                  >
                    {item.source_title}
                    <small>Created by: {item.created_by}</small>
                    <small>{new Date(item.created_at).toLocaleString()}</small>
                  </Button>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
        <Panel className="draft-preview notes-viewer">
          {draftLoading && <p role="status">Loading draft…</p>}
          {draftError && (
            <div role="alert">
              {draftError}
              <Button onClick={() => setDraftReload((n) => n + 1)}>
                Retry
              </Button>
              <Button
                onClick={() =>
                  setParams({ tab: "questions", course: courseId })
                }
              >
                Clear draft selection
              </Button>
            </div>
          )}
          {shownDraft ? (
            <>
              <Tag tone="purple">Unpublished draft · Review required</Tag>
              <h2>{shownDraft.source_title}</h2>
              <p>Source: {shownDraft.source_title}</p>
              <p>Created by: {shownDraft.created_by}</p>
              <p>Created: {new Date(shownDraft.created_at).toLocaleString()}</p>
              <ol className="mcq-questions">
                {shownDraft.questions.map((question) => (
                  <li key={question.id}>
                    <h3>{question.question}</h3>
                    <ol
                      type="A"
                      aria-label={`Choices for question ${question.position}`}
                    >
                      {question.choices.map((choice, index) => (
                        <li key={index}>{choice}</li>
                      ))}
                    </ol>
                    <p>
                      <strong>Correct answer:</strong>{" "}
                      {String.fromCharCode(65 + question.correct_choice_index)}.{" "}
                      {question.choices[question.correct_choice_index]}
                    </p>
                    <p>
                      <strong>Explanation:</strong> {question.explanation}
                    </p>
                  </li>
                ))}
              </ol>
            </>
          ) : (
            !draftLoading &&
            !draftError && (
              <EmptyState title="Your draft MCQs appear here">
                Generate MCQs from a source or open a saved batch. Nothing is
                published to students.
              </EmptyState>
            )
          )}
        </Panel>
      </div>
    </>
  );
}

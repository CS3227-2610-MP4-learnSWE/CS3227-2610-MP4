import McqDraftEditor from "./McqDraftEditor";
import DeleteTeacherItem from "../components/DeleteTeacherItem";
import { useAuth } from "../auth/AuthContext";
import { useEffect, useState } from "react";
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
import { useTeacherStudioSources } from "../hooks/useTeacherStudioSources";
import { useStudioGeneration } from "../hooks/useStudioGeneration";
import {
  generateMcqDraft,
  deleteMcqDraft,
  getMcqDraft,
  listMcqDrafts,
  type McqDraft,
} from "../services/teacherMcqs";

export default function TeacherMcqs() {
  const [params, setParams] = useSearchParams();
  const queryCourse = params.get("course") || "";
  const draftId = params.get("batch") || "";
  const studio = useTeacherStudioSources(queryCourse, listMcqDrafts);
  const [draft, setDraft] = useState<McqDraft | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftError, setDraftError] = useState("");
  const [draftReload, setDraftReload] = useState(0);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const { busy, start } = useStudioGeneration(
    `${studio.courseId}/${studio.sourceId}/${draftId}`,
  );
  useEffect(() => {
    setError("");
    setSuccess("");
  }, [studio.courseId]);
  useEffect(() => {
    let active = true;
    setDraft(null);
    setDraftError("");
    if (!studio.courseId || !draftId) {
      setDraftLoading(false);
      return;
    }
    setDraftLoading(true);
    getMcqDraft(draftId)
      .then((item) => {
        if (!active) return;
        if (item.course_id !== studio.courseId || item.id !== draftId)
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
  }, [studio.courseId, draftId, draftReload]);
  const shownDraft =
    draft?.course_id === studio.courseId && draft.id === draftId ? draft : null;
  const changeCourse = (id: string) => {
    setParams(id ? { tab: "questions", course: id } : { tab: "questions" });
  };
  const generate = async () => {
    if (editing || saving || !studio.courseId || !studio.sourceId) return;
    const request = start();
    if (!request) return;
    setError("");
    setSuccess("");
    try {
      const created = await generateMcqDraft(studio.sourceId);
      if (!request.isCurrent()) return;
      if (
        created.course_id !== studio.courseId ||
        created.source_material_id !== studio.sourceId
      )
        throw new Error("Unexpected draft");
      setParams({
        tab: "questions",
        course: studio.courseId,
        batch: created.id,
      });
      setSuccess("Draft MCQs generated and saved.");
      studio.reloadResources();
    } catch (reason) {
      if (request.isCurrent()) setError(teacherGenerationError(reason, "MCQs"));
    } finally {
      request.finish();
    }
  };
  const { user } = useAuth();
  return (
    <>
      <PageHeading
        eyebrow="A HEAD START, NOT A REPLACEMENT"
        title="AI content studio"
        description="Turn a private source material into three concise, unpublished draft MCQs."
      />
      <PreviewNote>Signed in as {user?.display_name}</PreviewNote>
      {studio.coursesError && (
        <div className="library-status" role="alert">
          {studio.coursesError}
          <Button onClick={studio.retryCourses}>Retry</Button>
        </div>
      )}
      {!studio.coursesReady && !studio.coursesError && (
        <p role="status">Loading courses…</p>
      )}
      {studio.coursesReady && queryCourse && !studio.courseId && (
        <div className="library-status" role="alert">
          This course is unavailable. Choose a managed course below.
        </div>
      )}
      {studio.coursesReady && !studio.courses.length && (
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
              value={studio.courseId}
              onChange={(event) => changeCourse(event.target.value)}
              disabled={!studio.coursesReady || busy || saving}
            >
              {studio.courses.map((course) => (
                <MenuItem key={course.id} value={course.id}>
                  {course.title}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Source material"
              value={
                studio.materials.some((m) => m.id === studio.sourceId)
                  ? studio.sourceId
                  : ""
              }
              onChange={(event) => {
                studio.setSourceId(event.target.value);
                setError("");
                setSuccess("");
              }}
              disabled={
                busy ||
                saving ||
                studio.resourcesLoading ||
                !studio.materials.length
              }
            >
              {studio.materials.map((material) => (
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
            {!studio.resourcesLoading &&
              studio.courseId &&
              studio.resourcesReady &&
              !studio.materials.length && (
                <p>
                  Upload a source material to generate MCQs.{" "}
                  <Link to="/teacher/materials">Open materials library</Link>
                </p>
              )}
            <Button
              fullWidth
              variant="contained"
              startIcon={<Sparkles size={17} />}
              disabled={
                busy ||
                editing ||
                saving ||
                !studio.sourceId ||
                !studio.courseId ||
                studio.resourcesLoading
              }
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
            {studio.resourcesLoading && (
              <p role="status">Loading sources and saved drafts…</p>
            )}
            {studio.resourcesError && (
              <div role="alert">
                {studio.resourcesError}
                <Button onClick={studio.reloadResources}>Retry</Button>
              </div>
            )}
            {!studio.resourcesLoading &&
              !studio.resourcesError &&
              studio.courseId &&
              !studio.drafts.length && <p>No saved MCQ batches yet</p>}
            <ul>
              {studio.drafts.map((item) => (
                <li key={item.id}>
                  <Button
                    startIcon={<FileText size={16} />}
                    disabled={busy || saving}
                    onClick={() =>
                      setParams({
                        tab: "questions",
                        course: studio.courseId,
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
                  setParams({ tab: "questions", course: studio.courseId })
                }
              >
                Clear draft selection
              </Button>
            </div>
          )}
          {shownDraft ? (
            <>
              <Tag tone="purple">Unpublished draft · Review required</Tag>
              <McqDraftEditor
                key={shownDraft.id}
                draft={shownDraft}
                onSaved={(saved) => {
                  setDraft(saved);
                  studio.updateDraft(saved);
                }}
                onEditingChange={setEditing}
                onSavingChange={setSaving}
                deleteControl={
                  <DeleteTeacherItem
                    kind="batch"
                    name={shownDraft.source_title}
                    remove={() =>
                      deleteMcqDraft(shownDraft.id, shownDraft.version)
                    }
                    onDeleted={() => {
                      setSuccess("MCQ batch deleted.");
                      setParams({ tab: "questions", course: studio.courseId });
                      studio.reloadResources();
                    }}
                    onLatest={async () => {
                      const request = start();
                      if (!request) return;
                      try {
                        const latest = await getMcqDraft(shownDraft.id);
                        if (request.isCurrent()) {
                          setDraft(latest);
                          studio.updateDraft(latest);
                        }
                      } finally {
                        request.finish();
                      }
                    }}
                  />
                }
              />
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

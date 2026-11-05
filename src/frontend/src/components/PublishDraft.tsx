import { useTeacherReadLifetime } from "../hooks/useTeacherReadLifetime";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  TextField,
} from "@mui/material";
import { ApiError } from "../services/client";
import { count, invalidText, strip } from "../services/draftText";
import { listTeacherTopics, type Topic } from "../services/teacherMaterials";
import {
  publishDraft,
  publicationError,
  publicationPath,
  type PublicationKind,
} from "../services/publications";
import { usePublications } from "../hooks/usePublications";
import type { NoteDraft } from "../services/teacherNotes";
import type { McqDraft } from "../services/teacherMcqs";
import { QuestionPreview } from "./PublicationContent";

type Props = {
  kind: PublicationKind;
  draft: NoteDraft | McqDraft;
  sourceTopic?: string | null;
  status: ReturnType<typeof usePublications>;
  disabled: boolean;
  onReload: () => void;
};
export default function PublishDraft({
  kind,
  draft,
  sourceTopic,
  status,
  disabled,
  onReload,
}: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const epoch = useRef(0);
  const pending = useRef(false);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [topic, setTopic] = useState("");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [topicsError, setTopicsError] = useState("");
  const [topicsRetry, setTopicsRetry] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reload, setReload] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const refreshedFrom = useRef<number | null>(null);
  useTeacherReadLifetime(`${open}/${draft.id}/${topicsRetry}`);
  const view = useRef<HTMLButtonElement>(null);
  useLayoutEffect(() => {
    const invalidate = () => {
      epoch.current++;
    };
    invalidate();
    setOpen(false);
    setSaving(false);
    pending.current = false;
    setNotice("");
    return invalidate;
  }, [location.key, draft.id]);
  useEffect(() => {
    if (notice) view.current?.focus();
  }, [notice]);
  useEffect(() => {
    if (!open) return;
    let active = true;
    setTopicsLoading(true);
    setTopicsError("");
    setTopics([]);
    listTeacherTopics(draft.course_id)
      .then((items) => {
        if (active) {
          setTopics(items);
          setTopic(
            items.some((item) => item.id === sourceTopic) ? sourceTopic! : "",
          );
        }
      })
      .catch((reason) => {
        if (active)
          setTopicsError(
            publicationError(
              reason,
              "Could not load publication topics. Please try again.",
            ),
          );
      })
      .finally(() => {
        if (active) setTopicsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [open, draft.course_id, sourceTopic, topicsRetry]);
  const published = status.items.find(
    (item) => item.kind === kind && item.source_draft_id === draft.id,
  );
  useEffect(() => {
    if (
      refreshedFrom.current === null ||
      status.completed <= refreshedFrom.current
    )
      return;
    refreshedFrom.current = null;
    setUncertain(false);
    if (published) {
      setOpen(false);
      setNotice("Already published. Showing the existing version.");
    }
  }, [status.completed, published]);
  const close = () => {
    if (pending.current) return;
    setOpen(false);
    setTitle("");
    setTopic("");
    setError("");
    setReload(false);
  };
  const submit = async () => {
    if (pending.current) return;
    pending.current = true;
    setSaving(true);
    setError("");
    const owner = epoch.current;
    try {
      const result = await publishDraft(kind, draft.id, {
        version: draft.version,
        title: strip(title),
        topic_id: topic,
      });
      if (owner !== epoch.current) return;
      status.update(result.publication);
      setOpen(false);
      setTitle("");
      setTopic("");
      setNotice(
        result.existing
          ? "Already published. Showing the existing version."
          : kind === "note"
            ? "Notes published. Enrolled students can read them in Study materials."
            : "Practice set published. Student practice integration is pending.",
      );
    } catch (reason) {
      if (owner !== epoch.current) return;
      setError(
        publicationError(
          reason,
          "Could not confirm publication. Refresh publication status before retrying.",
        ),
      );
      if (reason instanceof ApiError && reason.code === "already_published")
        status.retry();
      setUncertain(!(reason instanceof ApiError) || reason.status === 0);
    } finally {
      if (owner === epoch.current) {
        pending.current = false;
        setSaving(false);
      }
    }
  };
  const validTitle =
    count(strip(title)) >= 1 &&
    count(strip(title)) <= 200 &&
    !invalidText(title);
  return (
    <div className="publication-controls">
      {status.loading && <p role="status">Checking publication status…</p>}
      {status.error && (
        <div role="alert">
          {status.error}
          <Button onClick={status.retry}>Retry publication status</Button>
        </div>
      )}
      {published ? (
        <>
          <Button
            ref={view}
            onClick={() => navigate(publicationPath(published))}
          >
            View published version
          </Button>
        </>
      ) : (
        <Button
          variant="contained"
          disabled={disabled || !status.ready}
          onClick={() => {
            setTitle("title" in draft ? draft.title : draft.source_title);
            setError(
              uncertain
                ? "Could not confirm publication. Refresh publication status before retrying."
                : "",
            );
            setOpen(true);
          }}
        >
          {kind === "note" ? "Publish notes" : "Publish practice set"}
        </Button>
      )}
      {notice && <p role="status">{notice}</p>}
      <Dialog
        open={open}
        onClose={close}
        fullWidth
        maxWidth="md"
        aria-labelledby="publish-title"
      >
        <DialogTitle id="publish-title">
          {kind === "note" ? "Publish notes?" : "Publish practice set?"}
        </DialogTitle>
        <DialogContent className="publication-dialog-content">
          <p>
            Publishing saves a permanent version once. Later draft changes will
            not update it.
          </p>
          {kind === "practice_set" && (
            <p>
              Student practice screens are not connected to these published sets
              yet.
            </p>
          )}
          <TextField
            fullWidth
            label="Publication title"
            value={title}
            disabled={saving}
            onChange={(event) => setTitle(event.target.value)}
            error={!validTitle}
            helperText={
              !validTitle
                ? "Enter 1–200 valid text characters."
                : `${count(strip(title))} / 200 characters`
            }
          />
          <TextField
            fullWidth
            select
            label="Publication topic"
            helperText={!topic ? "Choose a course topic." : " "}
            value={topic}
            disabled={saving || topicsLoading}
            onChange={(event) => setTopic(event.target.value)}
          >
            {topics.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>
          {topicsLoading && <p role="status">Loading publication topics…</p>}
          {topicsError && (
            <div role="alert">
              {topicsError}
              <Button onClick={() => setTopicsRetry((value) => value + 1)}>
                Retry topics
              </Button>
            </div>
          )}
          {!topicsLoading && !topicsError && !topics.length && (
            <p>
              No topics available. A course topic is required before publishing.
            </p>
          )}
          {"content" in draft ? (
            <div className="note-content">{draft.content}</div>
          ) : (
            <QuestionPreview questions={draft.questions} />
          )}
          {error && (
            <div role="alert">
              {error}
              {error.includes("Reload and review") && (
                <Button onClick={() => setReload(true)}>Reload draft</Button>
              )}
            </div>
          )}
          {uncertain && (
            <Button
              onClick={() => {
                refreshedFrom.current = status.completed;
                status.retry();
              }}
            >
              Refresh publication status
            </Button>
          )}
          {published && (
            <Button onClick={() => navigate(publicationPath(published))}>
              View published version
            </Button>
          )}
        </DialogContent>
        <DialogActions>
          <Button disabled={saving} onClick={close}>
            Cancel
          </Button>
          <Button
            disabled={
              saving ||
              uncertain ||
              !!published ||
              !status.ready ||
              !validTitle ||
              !topic ||
              topicsLoading ||
              !!topicsError ||
              error.includes("Reload and review")
            }
            onClick={submit}
          >
            {saving ? "Publishing…" : "Confirm publication"}
          </Button>
        </DialogActions>
      </Dialog>
      {reload && (
        <Dialog
          open
          onClose={() => setReload(false)}
          aria-labelledby="reload-publication-title"
        >
          <DialogTitle id="reload-publication-title">
            Reload latest draft?
          </DialogTitle>
          <DialogContent>
            Reloading will discard the publication form entries. Review the
            latest draft before publishing.
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setReload(false)}>Keep form</Button>
            <Button
              onClick={() => {
                close();
                onReload();
              }}
            >
              Reload draft
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </div>
  );
}

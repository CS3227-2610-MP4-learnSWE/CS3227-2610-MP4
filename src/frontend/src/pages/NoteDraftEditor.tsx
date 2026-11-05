import { useEffect, useRef, useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";
import { ApiError } from "../services/client";
import {
  getNoteDraft,
  saveNoteDraft,
  type NoteDraft,
} from "../services/teacherNotes";

import { strip, normalise, count, invalidText } from "../services/draftText";
import { useDraftNavigationGuard } from "../hooks/useDraftNavigationGuard";
const conflictMessage =
  "This draft has changed. Load the latest saved version before saving.";

type Props = {
  draft: NoteDraft;
  onSaved: (draft: NoteDraft) => void;
  onEditingChange: (value: boolean) => void;
  onSavingChange: (value: boolean) => void;
};

export default function NoteDraftEditor({
  draft,
  onSaved,
  onEditingChange,
  onSavingChange,
}: Props) {
  const [baseline, setBaseline] = useState(draft);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(draft.title);
  const [content, setContent] = useState(draft.content);
  const [saving, setSaving] = useState(false);
  const [loadingLatest, setLoadingLatest] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [notice, setNotice] = useState("");
  const [intent, setIntent] = useState<"cancel" | "latest" | null>(null);
  const pending = useRef(false);
  const mounted = useRef(true);
  const operation = useRef(0);
  const cleanTitle = strip(title);
  const cleanContent = normalise(content);
  const titleValid =
    count(cleanTitle) >= 1 && count(cleanTitle) <= 200 && !invalidText(title);
  const contentValid =
    count(cleanContent) >= 1 &&
    count(cleanContent) <= 2000 &&
    !invalidText(content);
  const dirty =
    editing && (title !== baseline.title || content !== baseline.content);
  const changed =
    cleanTitle !== strip(baseline.title) ||
    cleanContent !== normalise(baseline.content);
  const validChange = titleValid && contentValid && changed;
  const blocker = useDraftNavigationGuard(dirty, saving);
  const blocked = blocker.state === "blocked";

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      operation.current += 1;
    };
  }, []);
  useEffect(() => {
    onEditingChange(editing);
    return () => onEditingChange(false);
  }, [editing, onEditingChange]);
  useEffect(() => {
    onSavingChange(saving);
    return () => onSavingChange(false);
  }, [saving, onSavingChange]);
  const startEditing = () => {
    setBaseline(draft);
    setTitle(draft.title);
    setContent(draft.content);
    setError("");
    setConflict(false);
    setNotice("");
    setEditing(true);
  };
  const cancel = () => {
    if (saving) return;
    operation.current += 1;
    pending.current = false;
    setLoadingLatest(false);
    setEditing(false);
    setError("");
    setConflict(false);
    setIntent(null);
  };
  const matches = (item: NoteDraft, expected: NoteDraft) =>
    item.id === expected.id &&
    item.course_id === expected.course_id &&
    item.source_material_id === expected.source_material_id &&
    item.source_title === expected.source_title &&
    item.created_by === expected.created_by &&
    item.created_at === expected.created_at;
  const save = async () => {
    if (pending.current || !validChange || conflict) return;
    pending.current = true;
    setSaving(true);
    setError("");
    const token = ++operation.current;
    try {
      const saved = await saveNoteDraft(baseline.id, {
        title: cleanTitle,
        content: cleanContent,
        version: baseline.version,
      });
      if (!mounted.current || token !== operation.current) return;
      if (
        !matches(saved, baseline) ||
        saved.version !== baseline.version + 1 ||
        saved.title !== cleanTitle ||
        saved.content !== cleanContent
      )
        throw new Error("Invalid saved draft");
      onSaved(saved);
      setBaseline(saved);
      setEditing(false);
      setNotice("Draft changes saved.");
    } catch (reason) {
      if (mounted.current && token === operation.current) {
        const stale =
          reason instanceof ApiError &&
          reason.status === 409 &&
          reason.code === "draft_conflict";
        setConflict(stale);
        setError(
          stale
            ? conflictMessage
            : "Could not save changes. Your edits are still here.",
        );
      }
    } finally {
      if (mounted.current && token === operation.current) {
        pending.current = false;
        setSaving(false);
      }
    }
  };
  const loadLatest = async () => {
    if (pending.current) return;
    setIntent(null);
    pending.current = true;
    setLoadingLatest(true);
    setError("");
    const token = ++operation.current;
    try {
      const latest = await getNoteDraft(baseline.id);
      if (!mounted.current || token !== operation.current) return;
      if (!matches(latest, baseline) || latest.version < baseline.version)
        throw new Error("Invalid latest draft");
      setBaseline(latest);
      setTitle(latest.title);
      setContent(latest.content);
      setConflict(false);
      onSaved(latest);
    } catch {
      if (mounted.current && token === operation.current)
        setError(
          "Could not load the latest saved version. Your edits are still here.",
        );
    } finally {
      if (mounted.current && token === operation.current) {
        pending.current = false;
        setLoadingLatest(false);
      }
    }
  };
  const keepEditing = () => {
    setIntent(null);
    if (blocker.state === "blocked") blocker.reset();
  };
  const discard = () => {
    if (saving) return;
    if (blocker.state === "blocked") {
      cancel();
      blocker.proceed();
    } else if (intent === "latest") void loadLatest();
    else cancel();
  };

  return (
    <>
      <h2>{draft.title}</h2>
      <p className="muted">
        Source: {draft.source_title}
        <br />
        Created by: {draft.created_by}
        <br />
        Created: {new Date(draft.created_at).toLocaleString()}
        <br />
        Last edited by: {draft.updated_by}
        <br />
        Last edited: {new Date(draft.updated_at).toLocaleString()}
      </p>
      {editing ? (
        <div className="note-editor">
          <TextField
            label="Note title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            disabled={saving || loadingLatest}
            error={!titleValid}
            helperText={
              !titleValid
                ? "Use 1–200 valid text characters for the title."
                : `${count(cleanTitle)} / 200 characters`
            }
          />
          <TextField
            label="Note content"
            value={content}
            onChange={(event) => setContent(event.target.value)}
            disabled={saving || loadingLatest}
            multiline
            minRows={10}
            error={!contentValid}
            helperText={
              !contentValid
                ? `Use 1–2000 valid text characters. ${count(cleanContent)} / 2000 characters`
                : `${count(cleanContent)} / 2000 characters`
            }
          />
          {error && <p role="alert">{error}</p>}
          {conflict && (
            <Button
              onClick={() => setIntent("latest")}
              disabled={saving || loadingLatest}
            >
              Load latest saved version
            </Button>
          )}
          <div className="note-editor-actions">
            <Button
              variant="contained"
              onClick={save}
              disabled={saving || loadingLatest || !validChange || conflict}
            >
              {saving
                ? "Saving…"
                : error && !conflict
                  ? "Retry save"
                  : "Save changes"}
            </Button>
            <Button
              onClick={() => (dirty ? setIntent("cancel") : cancel())}
              disabled={saving || loadingLatest}
            >
              Cancel
            </Button>
          </div>
          {saving && <p role="status">Saving changes…</p>}
          {loadingLatest && <p role="status">Loading latest saved version…</p>}
        </div>
      ) : (
        <>
          <div className="note-content">{draft.content}</div>
          <Button variant="outlined" onClick={startEditing}>
            Edit notes
          </Button>
          <p className="muted">
            Draft edits remain private. Publish a reviewed saved draft from the
            read-only viewer.
          </p>
        </>
      )}
      {notice && <p role="status">{notice}</p>}
      <Dialog
        open={blocked || intent !== null}
        onClose={saving ? undefined : keepEditing}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>
          {saving
            ? "Saving changes"
            : intent === "latest" && !blocked
              ? "Load latest saved version?"
              : "Unsaved changes"}
        </DialogTitle>
        <DialogContent>
          {saving
            ? "Wait for the save to finish before leaving."
            : intent === "latest" && !blocked
              ? "Loading the latest saved version will discard your local changes."
              : "Discard your unsaved note changes?"}
        </DialogContent>
        <DialogActions>
          <Button onClick={keepEditing}>
            {saving ? "Stay here" : "Keep editing"}
          </Button>
          {!saving && <Button onClick={discard}>Discard changes</Button>}
        </DialogActions>
      </Dialog>
    </>
  );
}

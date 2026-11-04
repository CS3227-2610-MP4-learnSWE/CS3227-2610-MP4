import { useId, useLayoutEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import { ApiError } from "../services/client";
import { teacherMutationError } from "../services/teacherMutations";

type Props = {
  kind: "note" | "batch" | "material";
  name: string;
  remove: () => Promise<unknown>;
  onDeleted: () => void;
  onLatest?: () => Promise<void>;
};
export default function DeleteTeacherItem({
  kind,
  name,
  remove,
  onDeleted,
  onLatest,
}: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const pending = useRef(false);
  const epoch = useRef(0);
  const location = useLocation();
  const headingId = useId();
  useLayoutEffect(() => {
    epoch.current += 1;
    pending.current = false;
    setBusy(false);
    setOpen(false);
    setError("");
    setConflict(false);
    return () => {
      epoch.current += 1;
    };
  }, [location.key]);
  const label =
    kind === "note"
      ? "Delete note draft"
      : kind === "batch"
        ? "Delete MCQ batch"
        : "Delete material";
  const keep =
    kind === "note"
      ? "Keep draft"
      : kind === "batch"
        ? "Keep batch"
        : "Keep material";
  const perform = async () => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    const token = epoch.current;
    try {
      await remove();
      if (token !== epoch.current) return;
      setOpen(false);
      onDeleted();
    } catch (reason) {
      if (token !== epoch.current) return;
      setOpen(false);
      setConflict(
        reason instanceof ApiError && reason.code === "draft_conflict",
      );
      setError(teacherMutationError(reason, "delete"));
    } finally {
      if (token === epoch.current) {
        pending.current = false;
        setBusy(false);
      }
    }
  };
  const latest = async () => {
    if (pending.current || !onLatest) return;
    pending.current = true;
    setBusy(true);
    const token = epoch.current;
    try {
      await onLatest();
      if (token === epoch.current) {
        setError("");
        setConflict(false);
      }
    } catch (reason) {
      if (token === epoch.current)
        setError(teacherMutationError(reason, "delete"));
    } finally {
      if (token === epoch.current) {
        pending.current = false;
        setBusy(false);
      }
    }
  };
  return (
    <>
      <Button
        color="error"
        disabled={busy || conflict}
        aria-label={kind === "material" ? `${label} ${name}` : label}
        onClick={() => {
          setError("");
          setOpen(true);
        }}
      >
        {label}
      </Button>
      {error && <p role="alert">{error}</p>}
      {conflict && onLatest && (
        <Button disabled={busy} onClick={latest}>
          Load latest saved version
        </Button>
      )}
      <Dialog
        open={open}
        onClose={busy ? undefined : () => setOpen(false)}
        aria-labelledby={headingId}
      >
        <DialogTitle id={headingId}>{label}?</DialogTitle>
        <DialogContent>
          {kind === "batch"
            ? `Permanently delete the MCQ batch from “${name}” and all three questions? This cannot be undone.`
            : kind === "material"
              ? `Permanently delete “${name}” and its original file? This cannot be undone.`
              : `Permanently delete “${name}”? This cannot be undone.`}
          {busy && <p role="status">Deleting…</p>}
        </DialogContent>
        <DialogActions>
          <Button disabled={busy} onClick={() => setOpen(false)}>
            {keep}
          </Button>
          <Button disabled={busy} color="error" onClick={perform}>
            Delete permanently
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

import { useRef, useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import { deleteAnalysis } from "../services/feedbackAnalysisApi";
import {
  DELETE_404,
  deleteMessage,
  localTime,
} from "../messages/feedbackAnalysis";

export type DeleteTarget = {
  id: string;
  form_title: string;
  created_at: string;
  response_count: number;
};

/** Confirmation for a permanent delete. One DELETE per confirmation; failures stay inside the dialog. */
export default function DeleteAnalysisDialog({
  target,
  onClose,
  onDeleted,
}: {
  target: DeleteTarget;
  /** Cancel or Escape. */
  onClose: () => void;
  /** `alreadyGone` is true when the server answered 404. */
  onDeleted: (alreadyGone: boolean) => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const cancel = useRef<HTMLButtonElement>(null);
  // Rendered into its own empty container so the page behind stays in the accessibility tree (focus is still trapped).
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const confirm = async () => {
    if (pending) return;
    setPending(true);
    setError("");
    try {
      await deleteAnalysis(target.id);
      onDeleted(false);
    } catch (failure) {
      const message = deleteMessage(failure);
      if (message === DELETE_404) onDeleted(true);
      else {
        setError(message);
        setPending(false);
      }
    }
  };
  return (
    <div ref={setContainer}>
      {container && (
        <Dialog
          container={container}
          open
          onClose={() => !pending && onClose()}
          disableEscapeKeyDown={pending}
          slotProps={{
            transition: { onEntered: () => cancel.current?.focus() },
          }}
          role="alertdialog"
          aria-labelledby="delete-analysis-title"
          aria-describedby="delete-analysis-body"
        >
          <DialogTitle id="delete-analysis-title">
            Delete this analysis permanently?
          </DialogTitle>
          <DialogContent id="delete-analysis-body">
            <p>
              Form: {target.form_title}. Created {localTime(target.created_at)}.
              Responses analysed: {target.response_count}.
            </p>
            <p>
              This permanently deletes the analysis: its statistics and charts,
              the AI summary, themes and suggestions, and the links to
              supporting responses. This cannot be undone.
            </p>
            <p>The original feedback responses and forms are not deleted.</p>
            {error && <p role="alert">{error}</p>}
          </DialogContent>
          <DialogActions>
            <Button autoFocus ref={cancel} onClick={onClose} disabled={pending}>
              Cancel
            </Button>
            <Button
              color="error"
              variant="contained"
              onClick={confirm}
              disabled={pending}
            >
              {pending ? "Deleting..." : "Delete permanently"}
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </div>
  );
}

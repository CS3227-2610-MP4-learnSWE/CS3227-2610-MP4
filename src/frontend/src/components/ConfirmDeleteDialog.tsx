import { useRef, useState, type ReactNode } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";

/**
 * Confirmation for a permanent delete (role alertdialog). One request per confirmation; a failure stays inside the
 * dialog with its message; Cancel and Escape are disabled while the request is pending.
 */
export default function ConfirmDeleteDialog({
  title,
  children,
  run,
  failure,
  onClose,
  onDeleted,
}: {
  title: string;
  children: ReactNode;
  /** Sends the one DELETE. */
  run: () => Promise<void>;
  /** The exact message for a failed run; `gone` closes the dialog because the server answered 404. */
  failure: (error: unknown) => { message: string; gone: boolean };
  /** Cancel or Escape. */
  onClose: () => void;
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
      await run();
      onDeleted(false);
    } catch (e) {
      const { message, gone } = failure(e);
      if (gone) onDeleted(true);
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
          aria-labelledby="confirm-delete-title"
          aria-describedby="confirm-delete-body"
        >
          <DialogTitle id="confirm-delete-title">{title}</DialogTitle>
          <DialogContent id="confirm-delete-body">
            {children}
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

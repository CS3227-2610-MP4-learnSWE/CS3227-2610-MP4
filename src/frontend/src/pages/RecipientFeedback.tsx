import { useLocation, Link } from "react-router";
import { useEffect, useRef } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import { useAuth } from "../auth/AuthContext";
import { PageHeading, Panel } from "../components/ui";
import FeedbackQuestion from "../components/FeedbackQuestion";
import { useFeedbackRead } from "../hooks/useFeedbackRead";
import { useResponseDraft } from "../hooks/useResponseDraft";
import { recipientBase, type RecipientForm } from "../services/feedbackApi";

function Editor({ initial }: { initial: RecipientForm }) {
  const { user } = useAuth();
  const draft = useResponseDraft(initial);
  const formElement = useRef<HTMLFormElement>(null);
  useEffect(() => {
    if (draft.code !== "invalid_feedback_answers" || draft.submitting) return;
    const index = draft.form.questions.findIndex((q) => {
      const value = draft.answers.find((a) => a.question_id === q.id)?.value;
      return (
        q.required &&
        (value === null ||
          value === undefined ||
          (typeof value === "string" && !value.trim()) ||
          (Array.isArray(value) && !value.length))
      );
    });
    const field = formElement.current?.querySelectorAll("fieldset").item(index);
    if (index >= 0)
      field?.querySelector<HTMLElement>("input,textarea,select")?.focus();
  }, [draft.code, draft.submitting, draft.form.questions, draft.answers]);
  const terminal =
    draft.unavailable || draft.form.submitted || draft.form.state === "closed";
  const locked =
    draft.unavailable ||
    draft.submitting ||
    draft.leaving ||
    draft.checking ||
    draft.code === "feedback_draft_version_conflict" ||
    draft.code === "uncertain_submission";
  return (
    <>
      <PageHeading
        eyebrow="YOUR FEEDBACK"
        title={draft.form.title}
        description={draft.form.description}
      />
      <Panel className="feedback-form">
        <p>
          Once submitted, your name and feedback are visible to administrators.
          Your unfinished draft is private.
        </p>
        {draft.error && <p role="alert">{draft.error}</p>}
        {terminal ? (
          draft.unavailable ? null : (
            <p role="status">
              {draft.form.submitted ? (
                <>
                  <strong>Completed</strong>
                  <br />
                  {draft.completedNow
                    ? "Feedback submitted. Thank you."
                    : "You have already submitted feedback."}
                </>
              ) : (
                "This form is closed."
              )}
            </p>
          )
        ) : (
          <>
            <p role="status">
              {draft.submitting
                ? "Submitting feedback..."
                : draft.saving || draft.leaving
                  ? "Saving your draft..."
                  : draft.saved && !draft.dirty
                    ? "Draft saved. You can return to finish later."
                    : "Your answers will be saved as a draft as you fill in this form."}
            </p>
            {draft.error && draft.dirty && (
              <p role="alert">
                Your latest changes are not saved. Keep this page open and
                retry.
              </p>
            )}
            <form
              ref={formElement}
              onSubmit={(e) => {
                e.preventDefault();
                void draft.submit();
              }}
            >
              {draft.form.questions.map((q, i) => (
                <FeedbackQuestion
                  key={q.id}
                  question={q}
                  index={i}
                  value={
                    draft.answers.find((a) => a.question_id === q.id)?.value ??
                    null
                  }
                  disabled={locked}
                  change={(v) => draft.change(q.id, v)}
                />
              ))}
              {draft.code === "feedback_draft_version_conflict" && (
                <Button onClick={draft.openReload}>Reload saved draft</Button>
              )}
              {draft.code === "uncertain_submission" && (
                <Button onClick={draft.checkStatus} disabled={draft.checking}>
                  Check submission status
                </Button>
              )}
              {draft.error &&
                draft.code !== "feedback_draft_version_conflict" &&
                draft.code !== "uncertain_submission" && (
                  <Button onClick={draft.retry} disabled={locked}>
                    Retry saving draft
                  </Button>
                )}
              <Button
                type="submit"
                variant="contained"
                disabled={locked || draft.blocked}
              >
                Submit feedback
              </Button>
            </form>
          </>
        )}
        <Button component={Link} to={`/${user?.role}/inbox`}>
          Back to inbox
        </Button>
      </Panel>
      <Dialog
        open={draft.reloadDialog}
        onClose={draft.cancelReload}
        aria-labelledby="feedback-reload-title"
      >
        <DialogTitle id="feedback-reload-title">
          Reload saved draft?
        </DialogTitle>
        <DialogContent>
          Reloading replaces your current changes with the saved draft.
        </DialogContent>
        <DialogActions>
          <Button onClick={draft.cancelReload}>Keep editing</Button>
          <Button onClick={() => void draft.confirmReload()}>
            Reload draft
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default function RecipientFeedback() {
  const location = useLocation();
  const id = location.pathname.split("/")[3];
  const read = useFeedbackRead(
    `${recipientBase}/${encodeURIComponent(id ?? "")}`,
    "recipient",
  );
  if (read.loading) return <p role="status">Loading feedback form...</p>;
  if (read.error)
    return (
      <div>
        <p role="alert">{read.error}</p>
        <Button onClick={read.reload}>Retry</Button>
      </div>
    );
  return read.data ? (
    <Editor key={`${id}:${location.key}`} initial={read.data} />
  ) : null;
}

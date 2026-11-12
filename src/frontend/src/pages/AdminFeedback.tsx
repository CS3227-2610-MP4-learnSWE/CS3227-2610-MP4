import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import { PageHeading, Panel } from "../components/ui";
import LocalTime from "../components/LocalTime";
import FeedbackDraftEditor from "../components/FeedbackDraftEditor";
import FeedbackAudience from "../components/FeedbackAudience";
import ConfirmDeleteDialog from "../components/ConfirmDeleteDialog";
import { deleteFeedbackResponse } from "../services/feedbackAnalysisApi";
import {
  deleteResponseMessage,
  RESPONSE_DELETED_STATUS,
  RESPONSE_NOT_FOUND,
} from "../messages/feedbackAnalysis";
import { useFeedbackRead } from "../hooks/useFeedbackRead";
import { getSessionGeneration } from "../services/client";
import {
  parseLegacyFeedbackPath,
  useFeedbackPaths,
  type FeedbackScreenRoute,
} from "../lib/feedbackPaths";
import {
  adminBase,
  feedbackError,
  feedbackWrite,
  feedbackCode,
  uncertain,
  type Answer,
  type Question,
  type Form,
} from "../services/feedbackApi";

function ReadError({ error, retry }: { error: string; retry: () => void }) {
  return (
    <div>
      <p role="alert">{error}</p>
      <Button onClick={retry}>Retry</Button>
    </div>
  );
}

function Forms() {
  const paths = useFeedbackPaths();
  const [offset, setOffset] = useState(0);
  const read = useFeedbackRead(
    `${adminBase}?limit=20&offset=${offset}`,
    "forms",
  );
  return (
    <>
      <PageHeading
        eyebrow="LISTEN AND IMPROVE"
        title="Feedback forms"
        description="Prepare surveys, choose recipients and review their submitted feedback."
        action={
          <>
            <Button component={Link} to={paths.analysis()}>
              Feedback analysis
            </Button>
            <Button component={Link} to={paths.newForm()} variant="contained">
              New feedback form
            </Button>
          </>
        }
      />
      <Panel>
        <h2>Saved forms</h2>
        {read.loading && <p role="status">Loading feedback forms...</p>}
        {read.error && <ReadError error={read.error} retry={read.reload} />}
        {read.data && (
          <>
            {!read.data.items.length && (
              <p>No feedback forms yet. Create a form to collect feedback.</p>
            )}
            <div className="feedback-list">
              {read.data.items.map((form) => {
                const state =
                  form.state === "draft"
                    ? "Draft"
                    : form.state === "open"
                      ? "Open"
                      : "Closed";
                return (
                  <article
                    key={form.id}
                    className="feedback-list-entry-container"
                  >
                    <Link
                      className="feedback-list-entry"
                      to={paths.form(form.id)}
                      aria-label={`${form.title} · ${state} · Responses: ${form.response_count}`}
                    >
                      <span className="feedback-list-entry-title">
                        {form.title}
                      </span>
                      <span className="feedback-list-entry-meta">
                        {state} · Responses: {form.response_count}
                      </span>
                    </Link>
                  </article>
                );
              })}
            </div>
            {offset > 0 && (
              <Button onClick={() => setOffset(Math.max(0, offset - 20))}>
                Previous page
              </Button>
            )}
            {read.data.next_offset !== null && (
              <Button onClick={() => setOffset(read.data!.next_offset!)}>
                Next page
              </Button>
            )}
          </>
        )}
      </Panel>
    </>
  );
}

function Detail({ id, initial }: { id: string; initial?: Form }) {
  const paths = useFeedbackPaths();
  const location = useLocation();
  const read = useFeedbackRead(
    `${adminBase}/${encodeURIComponent(id)}`,
    "form",
    initial,
  );
  const [audience, setAudience] = useState(false);
  const [closeDialog, setCloseDialog] = useState(false);
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState(
    typeof location.state?.notice === "string" ? location.state.notice : "",
  );
  const [error, setError] = useState("");
  const [reconcile, setReconcile] = useState(false);
  const reloadBaseline = useRef<number | null>(null);
  const alive = useRef(true);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (
      reloadBaseline.current !== null &&
      read.revision > reloadBaseline.current &&
      !read.loading &&
      !read.error &&
      read.data
    ) {
      reloadBaseline.current = null;
      setReconcile(false);
      setError("");
    }
  }, [read.revision, read.loading, read.error, read.data]);
  function published(form: Form) {
    read.replace(form);
    setAudience(false);
    setNotice("Form published. Inbox requests sent.");
    setError("");
    setReconcile(false);
  }
  async function close() {
    if (pending || reconcile || !read.data) return;
    setPending(true);
    setError("");
    setNotice("");
    const operation = new AbortController();
    controller.current = operation;
    try {
      const result = await feedbackWrite(
        "POST",
        `${adminBase}/${id}/close`,
        "form",
        { version: read.data.version },
        operation.signal,
      );
      if (alive.current) {
        read.replace(result);
        setCloseDialog(false);
        setNotice("Collection closed.");
      }
    } catch (failure) {
      if (alive.current) {
        setError(feedbackError(failure));
        if (
          uncertain(failure) ||
          ["feedback_version_conflict", "feedback_state_conflict"].includes(
            feedbackCode(failure),
          )
        )
          setReconcile(true);
      }
    } finally {
      if (alive.current) setPending(false);
    }
  }
  function reloadForm() {
    setCloseDialog(false);
    setAudience(false);
    setError("");
    reloadBaseline.current = read.revision;
    read.reload();
  }
  function requireReload(message: string) {
    setReconcile(true);
    setError(message);
  }
  if (read.loading) return <p role="status">Loading feedback form...</p>;
  if (read.error) return <ReadError error={read.error} retry={read.reload} />;
  const form = read.data;
  if (!form) return null;
  return (
    <>
      <PageHeading
        eyebrow="FEEDBACK FORM"
        title={form.title}
        description={form.description}
      />
      <Panel>
        <h2>Form overview</h2>
        {notice && (
          <p role="status" className="feedback-notice-chip">
            {notice}
          </p>
        )}
        {error && !closeDialog && (
          <p role="alert">
            {error}
            <Button onClick={reloadForm}>Reload saved form</Button>
          </p>
        )}
        <p>
          {form.state === "draft"
            ? "Draft"
            : form.state === "open"
              ? "Open"
              : "Closed"}
        </p>
        <p className="admin-summary">Responses: {form.response_count}</p>
        <div className="admin-action-bar">
          {form.state === "draft" && (
            <>
              <Button
                component={Link}
                variant="outlined"
                to={paths.editForm(id)}
                disabled={reconcile}
              >
                Edit draft
              </Button>
              <Button variant="contained" onClick={() => setAudience(true)}>
                Review audience
              </Button>
            </>
          )}
          {form.state === "open" && (
            <Button variant="contained" onClick={() => setCloseDialog(true)}>
              Close collection
            </Button>
          )}
          <Button component={Link} to={paths.formResponses(id)}>
            Review responses
          </Button>
        </div>
      </Panel>
      <Panel>
        <h2>Questions</h2>
        <ol className="admin-question-summary">
          {form.questions.map((q) => (
            <li key={q.id}>
              <strong>{q.prompt}</strong>
              <p>{q.required ? "Required" : "Optional"}</p>
            </li>
          ))}
        </ol>
      </Panel>
      {audience && (
        <FeedbackAudience
          form={form}
          close={() => setAudience(false)}
          published={published}
          reload={reloadForm}
          reconcile={reconcile}
          reconcileError={error}
          requireReload={requireReload}
        />
      )}
      <Dialog
        className="admin-dialog"
        open={closeDialog}
        onClose={pending ? undefined : () => setCloseDialog(false)}
        aria-labelledby="feedback-close-title"
      >
        <DialogTitle id="feedback-close-title">Close collection</DialogTitle>
        <DialogContent>
          Closing collection prevents new responses and keeps existing
          responses.{pending && <p role="status">Closing collection...</p>}
          {error && <p role="alert">{error}</p>}
          {reconcile && <Button onClick={reloadForm}>Reload saved form</Button>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCloseDialog(false)} disabled={pending}>
            Cancel
          </Button>
          <Button onClick={() => void close()} disabled={pending || reconcile}>
            Confirm close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

function Edit({ id }: { id: string }) {
  const read = useFeedbackRead(
    `${adminBase}/${encodeURIComponent(id)}`,
    "form",
  );
  if (read.loading) return <p role="status">Loading feedback form...</p>;
  if (read.error) return <ReadError error={read.error} retry={read.reload} />;
  if (!read.data) return null;
  if (read.data.state !== "draft")
    return (
      <p role="alert">
        This action is not available in the form&apos;s current state.
      </p>
    );
  return <FeedbackDraftEditor initial={read.data} />;
}

function Responses({ id }: { id: string }) {
  const paths = useFeedbackPaths();
  const analyseLink = paths.analysisForForm(id);
  const [offset, setOffset] = useState(0);
  // A status carried by a response delete is shown once: it is cleared from the history entry so a refresh drops it.
  const location = useLocation();
  const [status] = useState<string>(
    typeof location.state?.status === "string" ? location.state.status : "",
  );
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (!status) return;
    heading.current?.focus();
    window.history.replaceState({ ...window.history.state, usr: null }, "");
  }, [status]);
  const read = useFeedbackRead(
    `${adminBase}/${id}/responses?limit=20&offset=${offset}`,
    "responses",
  );
  return (
    <>
      <PageHeading
        eyebrow="SUBMITTED FEEDBACK"
        title="Responses"
        description="Only submitted responses are available for review."
      />
      <Panel>
        {analyseLink && (
          <p>
            <Link to={paths.responses()}>Choose another form</Link>{" "}
            <Link to={analyseLink}>Analyse this form</Link>
          </p>
        )}
        <h2 ref={heading} tabIndex={-1}>
          Submitted responses
        </h2>
        {status && <p role="status">{status}</p>}
        {read.loading && <p role="status">Loading responses...</p>}
        {read.error && <ReadError error={read.error} retry={read.reload} />}
        {read.data && (
          <>
            {!read.data.items.length && <p>No responses yet.</p>}
            <div className="feedback-list">
              {read.data.items.map((response) => (
                <article
                  key={response.id}
                  className="feedback-list-entry-container"
                >
                  <Link
                    className="feedback-list-entry"
                    to={paths.response(id, response.id)}
                    aria-label={`Response ${response.id} · ${response.respondent.display_name} · ${response.submitted_at}`}
                  >
                    <span className="feedback-list-entry-title">
                      {response.respondent.display_name}
                    </span>
                    <span className="feedback-list-entry-meta">
                      <LocalTime value={response.submitted_at} />
                      <small>Response {response.id}</small>
                    </span>
                  </Link>
                </article>
              ))}
            </div>
            {offset > 0 && (
              <Button onClick={() => setOffset(Math.max(0, offset - 20))}>
                Previous page
              </Button>
            )}
            {read.data.next_offset !== null && (
              <Button onClick={() => setOffset(read.data!.next_offset!)}>
                Next page
              </Button>
            )}
          </>
        )}
      </Panel>
    </>
  );
}

function answerText(q: Question, value: Answer["value"] | undefined) {
  if (value === null || value === undefined) return "No answer";
  if (Array.isArray(value))
    return value
      .map((id) => q.options.find((o) => o.id === id)?.label ?? "")
      .join(", ");
  if (["multiple_choice", "dropdown"].includes(q.type))
    return q.options.find((o) => o.id === value)?.label ?? "";
  return String(value);
}

function Response({ id, responseId }: { id: string; responseId: string }) {
  const paths = useFeedbackPaths();
  const read = useFeedbackRead(
    `${adminBase}/${id}/responses/${responseId}`,
    "response",
  );
  // The form's state tells the delete dialog whether the respondent can submit again.
  const form = useFeedbackRead(`${adminBase}/${id}`, "form");
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  if (read.loading) return <p role="status">Loading response...</p>;
  if (read.error) return <ReadError error={read.error} retry={read.reload} />;
  const response = read.data;
  if (!response) return null;
  return (
    <>
      <PageHeading
        eyebrow="SUBMITTED FEEDBACK"
        title="Feedback response"
        description={response.form_snapshot.title}
      />
      <Panel>
        <p className="admin-metadata">Response {response.id}</p>
        <p>Respondent: {response.respondent.display_name}</p>
        <Button component={Link} to={paths.reply(id, responseId)}>
          Respond to feedback
        </Button>
        <Button ref={trigger} color="error" onClick={() => setDeleting(true)}>
          Delete response
        </Button>
        <p className="admin-metadata">
          <LocalTime value={response.submitted_at} />
        </p>
        <p>{response.form_snapshot.description}</p>
        {response.form_snapshot.questions.map((q) => (
          <section key={q.id} className="feedback-answer">
            <h2>{q.prompt}</h2>
            <p>
              {q.type.replaceAll("_", " ")} ·{" "}
              {q.required ? "Required" : "Optional"}
            </p>
            <p className="feedback-answer-text">
              {answerText(
                q,
                response.answers.find((a) => a.question_id === q.id)?.value,
              )}
            </p>
          </section>
        ))}
      </Panel>
      {deleting && (
        <ConfirmDeleteDialog
          title="Delete this response permanently?"
          run={() => deleteFeedbackResponse(id, responseId)}
          failure={(e) => {
            const message = deleteResponseMessage(e);
            return { message, gone: message === RESPONSE_NOT_FOUND };
          }}
          onClose={() => setDeleting(false)}
          onDeleted={(gone) =>
            navigate(paths.formResponses(id), {
              replace: true,
              state: {
                status: gone ? RESPONSE_NOT_FOUND : RESPONSE_DELETED_STATUS,
              },
            })
          }
        >
          <p>
            Form: {response.form_snapshot.title}. Respondent:{" "}
            {response.respondent.display_name}. Submitted{" "}
            <LocalTime value={response.submitted_at} />.
          </p>
          <p>
            This permanently deletes {response.respondent.display_name}'s
            answers to this form. This cannot be undone.
          </p>
          <p>
            Not deleted: the form, the respondent's account, and stored analyses
            with their statistics and AI summaries.
          </p>
          <p>
            Links in stored analyses that cite this response will stop working
            and will show that the response is no longer available.
          </p>
          {form.data && (
            <p>
              {form.data.state === "open"
                ? `The form is open, so ${response.respondent.display_name} will be able to submit it again.`
                : `The form is closed, so ${response.respondent.display_name} will not be able to submit it again.`}
            </p>
          )}
        </ConfirmDeleteDialog>
      )}
    </>
  );
}

function AdminFeedbackContent({ route }: { route: FeedbackScreenRoute }) {
  const location = useLocation();
  const id = "formId" in route ? route.formId : undefined;
  const generation = getSessionGeneration();
  const creation = useRef<{ form: Form; generation: number } | null>(null);
  const createdForm =
    creation.current?.generation === generation &&
    creation.current.form.id === id
      ? creation.current.form
      : undefined;
  useEffect(() => {
    // The create receipt belongs only to the immediate replacement entry.
    // Detail captures it on mount; subsequent history entries must fetch again.
    if (route.screen !== "form-new") creation.current = null;
  }, [route.screen, id, location.key, generation]);
  if (route.screen === "forms") return <Forms key={location.key} />;
  if (route.screen === "form-new")
    return (
      <FeedbackDraftEditor
        key={location.key}
        created={(form) => {
          creation.current = { form, generation };
        }}
      />
    );
  if (route.screen === "form-edit")
    return <Edit key={`${route.formId}:${location.key}`} id={route.formId} />;
  if (route.screen === "response")
    return (
      <Response
        key={`${route.responseId}:${location.key}`}
        id={route.formId}
        responseId={route.responseId}
      />
    );
  if (route.screen === "response-list")
    return (
      <Responses key={`${route.formId}:${location.key}`} id={route.formId} />
    );
  return (
    <Detail
      key={`${route.formId}:${location.key}:${generation}`}
      id={route.formId}
      initial={createdForm}
    />
  );
}

/** The feedback screens for an already resolved route; the hub and the old page both render this. */
export function AdminFeedbackScreen({ route }: { route: FeedbackScreenRoute }) {
  return (
    <div className="admin-surface admin-feedback">
      <AdminFeedbackContent route={route} />
    </div>
  );
}

/** The old `/admin/feedback/...` page: a thin wrapper that reads the screen from the address. */
export default function AdminFeedback() {
  const location = useLocation();
  return (
    <AdminFeedbackScreen route={parseLegacyFeedbackPath(location.pathname)} />
  );
}

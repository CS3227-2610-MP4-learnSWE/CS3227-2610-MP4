import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router";
import {
  Button,
  Checkbox,
  FormControlLabel,
  Radio,
  RadioGroup,
  TextField,
} from "@mui/material";
import { MessageSquare, Users, Send, CheckCircle2 } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { PageHeading, Panel } from "../components/ui";
import { useMessagingRead } from "../hooks/useMessagingRead";
import { getSessionGeneration } from "../services/client";
import {
  messagingBase,
  messagingCode,
  messagingError,
  messagingWrite,
  type Preview,
  type Receipt,
  type Recipient,
  type RecipientPage,
} from "../services/messagingApi";

type Fields = {
  subject: string;
  body: string;
  role: "student" | "teacher";
  mode: "all_active" | "selected";
  ids: string[];
};
const emptyFields: Fields = {
  subject: "",
  body: "",
  role: "student",
  mode: "all_active",
  ids: [],
};
function fieldsFrom(p: Preview): Fields {
  return {
    subject: p.subject,
    body: p.body,
    role: p.audience_role,
    mode: p.audience_mode ?? "selected",
    ids: p.recipients.map((r) => r.id),
  };
}

function useMutation() {
  const alive = useRef(true);
  const controller = useRef<AbortController | null>(null);
  const navigate = useNavigate();
  const { user } = useAuth();
  const [pending, setPending] = useState(false);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      controller.current?.abort();
    };
  }, []);
  return {
    pending,
    async run<T>(
      path: string,
      body: unknown,
      success: (data: T) => void,
      failure: (error: unknown) => void,
    ) {
      if (pending) return;
      setPending(true);
      const generation = getSessionGeneration();
      controller.current = new AbortController();
      try {
        const result = await messagingWrite<T>(
          path,
          body,
          controller.current.signal,
        );
        if (alive.current && generation === getSessionGeneration())
          success(result);
      } catch (error) {
        if (
          !alive.current ||
          generation !== getSessionGeneration() ||
          messagingCode(error) === "stale_session"
        )
          return;
        if (messagingCode(error) === "forbidden")
          navigate(`/${user?.role}/overview`, { replace: true });
        failure(error);
      } finally {
        if (alive.current && generation === getSessionGeneration())
          setPending(false);
      }
    },
  };
}

function Composer({
  responseId,
  initial,
  notice,
  review,
}: {
  responseId?: string;
  initial?: Fields;
  notice?: string;
  review: (preview: Preview) => void;
}) {
  const [fields, setFields] = useState<Fields>(initial ?? emptyFields);
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState(notice ?? "");
  const mutation = useMutation();
  const subjectRef = useRef<HTMLInputElement>(null);
  const bodyRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    // Only a changed query needs a debounce. An initial no-op timer can reset
    // a fast page change and survive a test clock installed after mounting.
    if (search.trim() === debounced) return;
    const timer = setTimeout(() => {
      setDebounced(search.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search, debounced]);
  const path = responseId
    ? `${messagingBase}/feedback-responses/${encodeURIComponent(responseId)}/recipient`
    : `${messagingBase}/recipients?role=${fields.role}&search=${encodeURIComponent(debounced)}&page=${page}&page_size=50`;
  const read = useMessagingRead<RecipientPage & { recipient?: Recipient }>(
    path,
  );
  const update = (changes: Partial<Fields>) => {
    setFields((f) => ({ ...f, ...changes }));
    setError("");
  };
  const submit = () => {
    const subject = fields.subject.replaceAll("\r\n", "\n").trim();
    const body = fields.body.replaceAll("\r\n", "\n").trim();
    if (![...subject].length || [...subject].length > 120) {
      setError("Enter a subject between 1 and 120 characters.");
      subjectRef.current?.focus();
      return;
    }
    if (![...body].length || [...body].length > 5000) {
      setError("Enter a message between 1 and 5000 characters.");
      bodyRef.current?.focus();
      return;
    }
    if (
      !responseId &&
      fields.mode === "selected" &&
      (!fields.ids.length || fields.ids.length > 500)
    ) {
      setError("Select between 1 and 500 recipients.");
      return;
    }
    setError("");
    const request = responseId
      ? { kind: "feedback_response", response_id: responseId, subject, body }
      : {
          kind: "announcement",
          audience_role: fields.role,
          audience_mode: fields.mode,
          ...(fields.mode === "selected" ? { recipient_ids: fields.ids } : {}),
          subject,
          body,
        };
    void mutation.run<Preview>(
      `${messagingBase}/previews`,
      request,
      review,
      (err) => setError(messagingError(err)),
    );
  };
  return (
    <div className="messaging-page">
      <PageHeading
        eyebrow="LISTEN AND IMPROVE"
        title={responseId ? "Respond to feedback" : "New announcement"}
        description="Write a message, review its recipients and confirm delivery."
      />
      <div className="compose-layout">
        <Panel className="messaging-panel compose-message">
          <div className="compose-section-heading">
            <span className="section-icon">
              <MessageSquare size={21} aria-hidden="true" />
            </span>
            <div>
              <h2>Message details</h2>
              <p>Make your update clear, helpful and personal.</p>
            </div>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            <TextField
              label="Subject"
              variant="outlined"
              size="medium"
              slotProps={{ inputLabel: { shrink: true } }}
              helperText="A clear title. Up to 120 characters."
              inputRef={subjectRef}
              value={fields.subject}
              onChange={(e) => update({ subject: e.target.value })}
              disabled={mutation.pending}
            />
            <TextField
              label="Message"
              variant="outlined"
              slotProps={{ inputLabel: { shrink: true } }}
              helperText="Write your message in plain text. Up to 5000 characters."
              inputRef={bodyRef}
              multiline
              minRows={5}
              value={fields.body}
              onChange={(e) => update({ body: e.target.value })}
              disabled={mutation.pending}
            />
            {error && <p role="alert">{error}</p>}
            {mutation.pending && <p role="status">Preparing review…</p>}
            <div className="compose-actions">
              <span>You can check everything before sending.</span>
              <Button
                type="submit"
                variant="contained"
                disabled={mutation.pending || read.loading || !read.data}
              >
                Review message
              </Button>
            </div>
          </form>
        </Panel>
        <Panel className="messaging-panel compose-audience">
          <div className="compose-section-heading">
            <span className="section-icon">
              <Users size={21} aria-hidden="true" />
            </span>
            <div>
              <h2>Recipients</h2>
              <p>Choose who will receive this message.</p>
            </div>
          </div>

          {read.loading && (
            <p role="status">
              {responseId ? "Loading recipient…" : "Loading recipients…"}
            </p>
          )}
          {read.error && (
            <div>
              <p role="alert">{read.error}</p>
              <Button onClick={read.reload}>Retry</Button>
            </div>
          )}
          {responseId && read.data?.recipient && (
            <p>
              Recipient: {read.data.recipient.display_name} (
              {read.data.recipient.role})
            </p>
          )}
          {!responseId && (
            <>
              <TextField
                label="Search recipients"
                variant="outlined"
                slotProps={{ inputLabel: { shrink: true } }}
                placeholder="Find a person by name"
                disabled={mutation.pending}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <fieldset disabled={mutation.pending}>
                <legend>Audience role</legend>
                <RadioGroup
                  row
                  value={fields.role}
                  onChange={(e) => {
                    update({ role: e.target.value as Fields["role"], ids: [] });
                    setPage(1);
                  }}
                >
                  <FormControlLabel
                    value="student"
                    control={<Radio />}
                    label="Students"
                  />
                  <FormControlLabel
                    value="teacher"
                    control={<Radio />}
                    label="Teachers"
                  />
                </RadioGroup>
              </fieldset>
              <fieldset disabled={mutation.pending}>
                <legend>Audience selection</legend>
                <RadioGroup
                  row
                  value={fields.mode}
                  onChange={(e) =>
                    update({ mode: e.target.value as Fields["mode"] })
                  }
                >
                  <FormControlLabel
                    value="all_active"
                    control={<Radio />}
                    label="All active users"
                  />
                  <FormControlLabel
                    value="selected"
                    control={<Radio />}
                    label="Selected users"
                  />
                </RadioGroup>
              </fieldset>

              {read.data && (
                <>
                  {!read.data.items.length && (
                    <p>
                      {debounced
                        ? "No matching recipients."
                        : "No eligible recipients."}
                    </p>
                  )}
                  <div className="messaging-recipients">
                    {read.data.items.map((r) =>
                      fields.mode === "selected" ? (
                        <FormControlLabel
                          key={r.id}
                          control={
                            <Checkbox
                              inputProps={{
                                "aria-label": `${r.display_name} (${r.id})`,
                              }}
                              checked={fields.ids.includes(r.id)}
                              onChange={(e) =>
                                update({
                                  ids: e.target.checked
                                    ? [...fields.ids, r.id]
                                    : fields.ids.filter((id) => id !== r.id),
                                })
                              }
                            />
                          }
                          label={
                            <span className="recipient-label">
                              <strong>{r.display_name}</strong>
                              <small>{r.id}</small>
                            </span>
                          }
                        />
                      ) : (
                        <p key={r.id}>
                          <strong>{r.display_name}</strong>
                          <small>{r.id}</small>
                        </p>
                      ),
                    )}
                  </div>
                  <p className="selection-summary">
                    {fields.mode === "selected"
                      ? `${fields.ids.length} selected`
                      : `All active ${fields.role === "student" ? "students" : "teachers"} selected`}
                  </p>
                  {fields.mode === "all_active" && debounced && (
                    <p className="muted">
                      {read.data.total} matching recipients · Search only
                      filters this list.
                    </p>
                  )}
                  <div className="form-actions">
                    {page > 1 && (
                      <Button onClick={() => setPage((p) => p - 1)}>
                        Previous page
                      </Button>
                    )}
                    {page * 50 < read.data.total && (
                      <Button onClick={() => setPage((p) => p + 1)}>
                        Next page
                      </Button>
                    )}
                  </div>
                </>
              )}
            </>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Review({
  id,
  initial,
  back,
  edit,
}: {
  id: string;
  initial?: Preview;
  back?: string;
  edit: (fields?: Fields, notice?: string) => void;
}) {
  const first = useRef(initial);
  const read = useMessagingRead<{ preview: Preview; receipt: Receipt | null }>(
    first.current
      ? null
      : `${messagingBase}/previews/${encodeURIComponent(id)}`,
  );
  const preview = first.current ?? read.data?.preview;
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const sent = receipt ?? read.data?.receipt;
  const [error, setError] = useState("");
  const mutation = useMutation();
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (preview) heading.current?.focus();
  }, [preview, sent]);
  const send = () => {
    setError("");
    void mutation.run<Receipt>(
      `${messagingBase}/previews/${encodeURIComponent(id)}/send`,
      {},
      setReceipt,
      (err) => {
        if (
          [
            "PREVIEW_UNAVAILABLE",
            "PREVIEW_EXPIRED",
            "AUDIENCE_CHANGED",
          ].includes(messagingCode(err)) &&
          preview
        )
          edit(fieldsFrom(preview), messagingError(err));
        else setError(messagingError(err));
      },
    );
  };
  if (read.loading) return <p role="status">Preparing review…</p>;
  if (read.error)
    return (
      <Panel>
        <p role="alert">{read.error}</p>
        {["PREVIEW_UNAVAILABLE", "PREVIEW_EXPIRED"].includes(read.code) ? (
          <Button onClick={() => edit()}>Start a new message</Button>
        ) : (
          <Button onClick={read.reload}>Retry</Button>
        )}
      </Panel>
    );
  if (!preview) return null;
  return (
    <Panel className="messaging-panel message-review">
      <span
        className={`section-icon ${sent ? "success" : ""}`}
        aria-hidden="true"
      >
        {sent ? <CheckCircle2 size={24} /> : <Send size={24} />}
      </span>
      <h1 ref={heading} tabIndex={-1}>
        {sent ? "Message sent" : "Review message"}
      </h1>
      {sent ? (
        <>
          <p role="status">Sent to {sent.recipient_count} recipient(s).</p>
          {back ? (
            <Button component={Link} to={back}>
              Back to feedback
            </Button>
          ) : (
            <Button onClick={() => edit()}>New announcement</Button>
          )}
        </>
      ) : (
        <>
          <div className="review-audience">
            <p>
              Audience:{" "}
              {preview.audience_role === "student" ? "Students" : "Teachers"}
            </p>
            <p>Recipients: {preview.recipient_count}</p>
            <ul aria-label="Recipients">
              {preview.recipients.map((r) => (
                <li key={r.id}>
                  {r.display_name} ({r.id})
                </li>
              ))}
            </ul>
          </div>
          <div className="review-content">
            <p className="field-caption">Message preview</p>
            <h2>{preview.subject}</h2>
            <p className="messaging-text">{preview.body}</p>
          </div>
          {error && <p role="alert">{error}</p>}
          {mutation.pending && <p role="status">Sending message…</p>}
          <div className="form-actions">
            <Button
              onClick={() => edit(fieldsFrom(preview))}
              disabled={mutation.pending}
            >
              Edit message
            </Button>
            <Button
              variant="contained"
              onClick={send}
              disabled={mutation.pending}
            >
              Confirm send
            </Button>
          </div>
        </>
      )}
    </Panel>
  );
}

function MessagingRoute() {
  const location = useLocation();
  const navigate = useNavigate();
  const generation = getSessionGeneration();
  const previewId = new URLSearchParams(location.search).get("review");
  const parts = location.pathname.split("/");
  const responseId = location.pathname.endsWith("/reply")
    ? parts[5]
    : undefined;
  const back = responseId ? location.pathname.slice(0, -6) : undefined;
  const seed = useRef<{
    preview?: Preview;
    fields?: Fields;
    notice?: string;
    generation: number;
  } | null>(null);
  const current = seed.current?.generation === generation ? seed.current : null;
  useEffect(() => {
    seed.current = null;
  }, [location.key]);
  return previewId ? (
    <Review
      key={`${location.key}:${generation}`}
      id={previewId}
      initial={current?.preview?.id === previewId ? current.preview : undefined}
      back={back}
      edit={(fields, notice) => {
        seed.current = { fields, notice, generation };
        navigate(location.pathname, { replace: true });
      }}
    />
  ) : (
    <Composer
      key={`${location.key}:${generation}`}
      responseId={responseId}
      initial={current?.fields}
      notice={current?.notice}
      review={(preview) => {
        seed.current = { preview, generation };
        navigate(
          `${location.pathname}?review=${encodeURIComponent(preview.id)}`,
          { replace: true },
        );
      }}
    />
  );
}

export default function AdminMessaging() {
  const { status, user } = useAuth();
  if (status === "loading") return <p role="status">Loading your session…</p>;
  if (status !== "authenticated") return <Navigate to="/login" replace />;
  if (user?.role !== "admin")
    return <Navigate to={`/${user?.role}/overview`} replace />;
  return <MessagingRoute />;
}

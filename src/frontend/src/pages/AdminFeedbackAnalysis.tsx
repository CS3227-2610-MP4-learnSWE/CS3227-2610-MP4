import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import {
  Button,
  Checkbox,
  FormControlLabel,
  MenuItem,
  TextField,
} from "@mui/material";
import { PageHeading, Panel } from "../components/ui";
import DeleteAnalysisDialog from "../components/DeleteAnalysisDialog";
import {
  createAnalysis,
  listAnalyses,
  listForms,
  listResponses,
  responseCount,
  type HistoryItem,
} from "../services/feedbackAnalysisApi";
import {
  DELETE_404,
  DELETED_STATUS,
  generateMessage,
  isTransport,
  loadMessage,
  localTime,
  SELECTION_REQUIRED,
} from "../messages/feedbackAnalysis";

const SELECTION = "/admin/feedback/analysis";

/** One read with its own error and Retry; the same function identity means the same request. */
function useLoader<T>(load: (() => Promise<T>) | null, what: string) {
  const [state, setState] = useState<{
    data: T | null;
    error: string;
    loading: boolean;
  }>({ data: null, error: "", loading: !!load });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!load) {
      setState({ data: null, error: "", loading: false });
      return;
    }
    let current = true;
    setState({ data: null, error: "", loading: true });
    load().then(
      (data) => current && setState({ data, error: "", loading: false }),
      (e) =>
        current &&
        setState({ data: null, error: loadMessage(e, what), loading: false }),
    );
    return () => {
      current = false;
    };
  }, [load, what, attempt]);
  return { ...state, retry: () => setAttempt((n) => n + 1) };
}

function LoadError({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div>
      <p role="alert">{message}</p>
      <Button onClick={retry}>Retry</Button>
    </div>
  );
}

const newRequestId = () => crypto.randomUUID();

export default function AdminFeedbackAnalysis() {
  const navigate = useNavigate();
  const location = useLocation();
  const [formId, setFormId] = useState("");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(false);
  const [pending, setPending] = useState(false);
  const [generateError, setGenerateError] = useState("");
  const requestId = useRef<string | null>(null);

  const forms = useLoader(listForms, "forms");
  // `refresh` re-reads the list and the count when Refresh list is pressed.
  const readResponses = useCallback(
    () => listResponses(formId, offset),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [formId, offset, refresh],
  );
  const readCount = useCallback(
    () => responseCount(formId),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [formId, refresh],
  );
  const responses = useLoader(formId ? readResponses : null, "responses");
  const count = useLoader(formId ? readCount : null, "the response count");

  // History.
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<HistoryItem | null>(null);
  const [status, setStatus] = useState<string>(
    typeof location.state?.status === "string" ? location.state.status : "",
  );
  const heading = useRef<HTMLHeadingElement>(null);
  const loadHistory = useCallback(async (from: number) => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const page = await listAnalyses(from);
      setItems((old) => {
        const base = from === 0 ? [] : old;
        const seen = new Set(base.map((i) => i.id));
        return [...base, ...page.items.filter((i) => !seen.has(i.id))];
      });
      setNextOffset(page.next_offset);
    } catch (e) {
      setHistoryError(loadMessage(e, "previous analyses"));
    } finally {
      setHistoryLoading(false);
    }
  }, []);
  useEffect(() => {
    void loadHistory(0);
  }, [loadHistory]);
  // The status carried by a delete from the result page is shown once and is gone after a refresh.
  useEffect(() => {
    if (location.state?.status) {
      heading.current?.focus();
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location, navigate]);

  const changeSelection = (next: Set<string>, all = false) => {
    requestId.current = null;
    setTicked(next);
    setSelectAll(all);
    setGenerateError("");
  };
  const chooseForm = (id: string) => {
    setFormId(id);
    setOffset(0);
    changeSelection(new Set());
  };
  const total = count.data?.count ?? null;
  const selected = selectAll ? (total ?? 0) : ticked.size;

  const generate = async () => {
    if (pending) return;
    if (!formId || (!selectAll && ticked.size === 0)) {
      setGenerateError(SELECTION_REQUIRED);
      return;
    }
    requestId.current ??= newRequestId();
    const body = {
      form_id: formId,
      request_id: requestId.current,
      ...(selectAll
        ? { select_all: true, expected_count: total }
        : { response_ids: [...ticked] }),
    };
    setPending(true);
    setGenerateError("");
    try {
      const analysis = await createAnalysis(body);
      requestId.current = null;
      navigate(`${SELECTION}/${analysis.id}`, { replace: true });
    } catch (e) {
      // Only a failure that may not have reached the server keeps the same request id.
      if (!isTransport(e)) requestId.current = null;
      setGenerateError(generateMessage(e));
      setPending(false);
    }
  };

  const removed = (id: string, alreadyGone: boolean) => {
    const remaining = items.filter((i) => i.id !== id);
    setItems(remaining);
    setNextOffset(nextOffset === null ? null : Math.max(0, nextOffset - 1));
    setDeleteTarget(null);
    setStatus(alreadyGone ? DELETE_404 : DELETED_STATUS);
    if (!remaining.length && nextOffset !== null) void loadHistory(0);
    // After the dialog has returned focus to its (removed) trigger.
    setTimeout(() => heading.current?.focus(), 100);
  };

  return (
    <div className="feedback-analysis">
      <PageHeading
        title="Feedback analysis"
        description="Select feedback responses to see statistics at once and get an AI summary of recurring issues. Analysis is advisory and changes nothing."
      />
      <div className="feedback-analysis-grid">
        <div>
          <Panel>
            <h2>Select responses</h2>
            {forms.loading && <p role="status">Loading forms...</p>}
            {forms.error && (
              <LoadError message={forms.error} retry={forms.retry} />
            )}
            {forms.data && !forms.data.items.length && (
              <p>No feedback forms yet.</p>
            )}
            {forms.data && forms.data.items.length > 0 && (
              <TextField
                select
                label="Feedback form"
                value={formId}
                onChange={(e) => chooseForm(e.target.value)}
              >
                {forms.data.items.map((form) => (
                  <MenuItem key={form.id} value={form.id}>
                    {form.title}
                  </MenuItem>
                ))}
              </TextField>
            )}
            {formId && (
              <>
                <div className="analysis-actions">
                  {total === null ? <span>Counting responses...</span> : null}
                  {total !== 0 && (
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectAll}
                          disabled={total === null || total === 0}
                          onChange={(e) =>
                            changeSelection(new Set(), e.target.checked)
                          }
                        />
                      }
                      label={
                        selectAll
                          ? `All ${total} responses selected`
                          : total === null
                            ? "Select all responses"
                            : `Select all ${total} responses`
                      }
                    />
                  )}
                  <Button onClick={() => changeSelection(new Set())}>
                    Clear selection
                  </Button>
                  <Button
                    onClick={() => {
                      setRefresh((n) => n + 1);
                    }}
                  >
                    Refresh list
                  </Button>
                </div>
                {count.error && (
                  <LoadError message={count.error} retry={count.retry} />
                )}
                <p>{selected} selected</p>
                {(responses.loading || count.loading) && (
                  <p role="status">Loading responses...</p>
                )}
                {responses.error && (
                  <LoadError
                    message={responses.error}
                    retry={responses.retry}
                  />
                )}
                {responses.data && !responses.data.items.length && (
                  <p>This form has no responses yet.</p>
                )}
                {responses.data && responses.data.items.length > 0 && (
                  <>
                    <div className="analysis-checklist">
                      {responses.data.items.map((item) => (
                        <FormControlLabel
                          key={item.id}
                          control={
                            <Checkbox
                              checked={selectAll || ticked.has(item.id)}
                              disabled={selectAll}
                              onChange={(e) => {
                                const next = new Set(ticked);
                                if (e.target.checked) next.add(item.id);
                                else next.delete(item.id);
                                changeSelection(next);
                              }}
                            />
                          }
                          label={`Select response from ${item.respondent.display_name}, submitted ${localTime(item.submitted_at)}`}
                        />
                      ))}
                    </div>
                    <Button
                      disabled={offset === 0}
                      onClick={() => setOffset(Math.max(0, offset - 100))}
                    >
                      Previous page
                    </Button>
                    <Button
                      disabled={responses.data.next_offset === null}
                      onClick={() => setOffset(responses.data!.next_offset!)}
                    >
                      Next page
                    </Button>
                  </>
                )}
              </>
            )}
          </Panel>
          <Panel>
            <h2>Generate</h2>
            {generateError && <p role="alert">{generateError}</p>}
            <Button variant="contained" onClick={generate} disabled={pending}>
              {pending ? "Starting..." : "Generate analysis"}
            </Button>
          </Panel>
        </div>
        <div>
          <Panel>
            <h2>Limits</h2>
            <p>
              Up to 500 responses. Statistics are computed immediately.
              Free-text answers are summarised by AI in batches; with more than
              about 300 distinct answers a sample is used and the result says
              so.
            </p>
          </Panel>
          <Panel>
            <h2 ref={heading} tabIndex={-1}>
              Previous analyses
            </h2>
            {status && <p role="status">{status}</p>}
            {historyLoading && (
              <p role="status">Loading previous analyses...</p>
            )}
            {historyError && (
              <LoadError
                message={historyError}
                retry={() =>
                  void loadHistory(items.length ? (nextOffset ?? 0) : 0)
                }
              />
            )}
            {!historyLoading && !historyError && !items.length && (
              <p>No analyses yet.</p>
            )}
            <ul className="analysis-history">
              {items.map((item) => (
                <li key={item.id}>
                  <Link to={`${SELECTION}/${item.id}`}>
                    {`${item.form_title}, ${localTime(item.created_at)}, ${item.response_count} responses, AI ${item.ai_status}`}
                  </Link>
                  <Button
                    color="error"
                    onClick={() => setDeleteTarget(item)}
                    aria-label={`Delete analysis, ${item.form_title}, ${localTime(item.created_at)}`}
                  >
                    Delete
                  </Button>
                </li>
              ))}
            </ul>
            {nextOffset !== null && !historyError && (
              <Button
                disabled={historyLoading}
                onClick={() => void loadHistory(nextOffset)}
              >
                Load more analyses
              </Button>
            )}
          </Panel>
        </div>
      </div>
      {deleteTarget && (
        <DeleteAnalysisDialog
          target={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onDeleted={(gone) => removed(deleteTarget.id, gone)}
        />
      )}
    </div>
  );
}

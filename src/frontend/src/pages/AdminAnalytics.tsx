import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Tab,
  Tabs,
  TextField,
} from "@mui/material";
import { useNavigate, useSearchParams } from "react-router";
import LocalTime from "../components/LocalTime";
import { PageHeading, Panel } from "../components/ui";
import { useAnalyticsLoad, type Loaded } from "../hooks/useAnalyticsLoad";
import { ApiError } from "../services/client";
import * as api from "../services/featureAnalytics";

const POLL_MS = 3000;
const NOTICE =
  "Grades are AI assessments, not verified facts. They do not change access or application content.";
const NO_AVERAGE =
  "No average can be calculated: no eligible records in this period.";

const seconds = (ms: number) => (ms / 1000).toFixed(1);

function unavailable(reason: api.Reason | null, recorded: string) {
  const text = reason && api.UNAVAILABLE_REASONS[reason]?.(recorded);
  return `Unavailable: ${text ?? "the value is not available"}`;
}

function PanelFailure({
  message,
  retry,
  label,
}: {
  message: string;
  retry: () => void;
  label: string;
}) {
  return (
    <Alert
      severity="error"
      action={
        <Button color="inherit" size="small" onClick={retry}>
          {label}
        </Button>
      }
    >
      {message}
    </Alert>
  );
}

function Scroll({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div
      className="table-scroll analytics-scroll"
      role="region"
      aria-label={name}
      tabIndex={0}
    >
      {children}
    </div>
  );
}

function GroupRows({
  title,
  total,
  group,
  recorded,
}: {
  title: string;
  total: string;
  group: api.ChatGroup;
  recorded: string;
}) {
  return (
    <>
      <tr>
        <th scope="rowgroup" colSpan={3}>
          {title}
        </th>
      </tr>
      {group.state === "unavailable" ? (
        <tr>
          <td colSpan={3}>{unavailable(group.reason, recorded)}</td>
        </tr>
      ) : group.rows.length === 0 ? (
        <tr>
          <td colSpan={3}>No chatbot requests in this period.</td>
        </tr>
      ) : (
        group.rows.map((row) => (
          <tr key={row.user_id}>
            <th scope="row">{row.name ?? row.user_id}</th>
            <td>{row.successful}</td>
            <td>{row.unsuccessful}</td>
          </tr>
        ))
      )}
      <tr>
        <th scope="row">{total}</th>
        {group.state === "unavailable" ? (
          <td colSpan={2}>{unavailable(group.reason, recorded)}</td>
        ) : (
          <>
            <td>{group.successful}</td>
            <td>{group.unsuccessful}</td>
          </>
        )}
      </tr>
    </>
  );
}

function UsagePanel({
  result,
  retry,
}: {
  result: Loaded<api.Usage> | null;
  retry: () => void;
}) {
  let body;
  if (result === null) body = <p role="status">Loading feature usage...</p>;
  else if (!result.ok)
    body = (
      <PanelFailure
        message={api.loadFailure("Feature usage", result.error)}
        retry={retry}
        label="Retry feature usage"
      />
    );
  else {
    const {
      chatbot,
      practice_completion: done,
      recording_started_on: recorded,
    } = result.data;
    const total = chatbot.total;
    body = (
      <>
        <h3>Chatbot requests</h3>
        <Scroll name="Chatbot requests by user">
          <table aria-label="Chatbot requests by user">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Successful</th>
                <th scope="col">Unsuccessful</th>
              </tr>
            </thead>
            <tbody>
              <GroupRows
                title="Students"
                total="Students total"
                group={chatbot.student}
                recorded={recorded}
              />
              <GroupRows
                title="Teachers"
                total="Teachers total"
                group={chatbot.teacher}
                recorded={recorded}
              />
              <tr>
                <th scope="row">All users total</th>
                {total.state === "available" ? (
                  <>
                    <td>{total.successful}</td>
                    <td>{total.unsuccessful}</td>
                  </>
                ) : (
                  <td colSpan={2}>{unavailable(total.reason, recorded)}</td>
                )}
              </tr>
            </tbody>
          </table>
        </Scroll>
        {(chatbot.student.rows_truncated || chatbot.teacher.rows_truncated) && (
          <p className="muted">
            Showing the first 500 users; totals include all users.
          </p>
        )}
        <h3>Practice-set completion</h3>
        <p>
          {done.state === "available"
            ? `${done.percentage}% (${done.submitted} of ${done.started} attempts submitted by the end of the period)`
            : done.state === "not_applicable"
              ? "Not applicable: no practice attempts were started in this period."
              : unavailable(done.reason, recorded)}
        </p>
      </>
    );
  }
  return (
    <Panel className="analytics-panel" role="region" ariaLabel="Feature usage">
      <h2>Feature usage</h2>
      {body}
    </Panel>
  );
}

function GenerationPanel({
  result,
  retry,
}: {
  result: Loaded<api.Generation> | null;
  retry: () => void;
}) {
  let body;
  if (result === null)
    body = <p role="status">Loading generation reliability...</p>;
  else if (!result.ok)
    body = (
      <PanelFailure
        message={api.loadFailure("Generation reliability", result.error)}
        retry={retry}
        label="Retry generation reliability"
      />
    );
  else {
    const recorded = result.data.recording_started_on;
    body = (
      <Scroll name="Generation success rates">
        <table aria-label="Generation success rates">
          <thead>
            <tr>
              <th scope="col">Workflow</th>
              <th scope="col">Attempts</th>
              <th scope="col">Successful</th>
              <th scope="col">Unsuccessful</th>
              <th scope="col">Success rate</th>
            </tr>
          </thead>
          <tbody>
            {result.data.workflows.map((row) => (
              <tr key={row.workflow}>
                <th scope="row">{row.label}</th>
                {row.state === "unavailable" ? (
                  <td colSpan={4}>{unavailable(row.reason, recorded)}</td>
                ) : (
                  <>
                    <td>{row.attempts}</td>
                    <td>{row.successful}</td>
                    <td>{row.unsuccessful}</td>
                    <td>
                      {row.state === "available"
                        ? `${row.rate_percent}%`
                        : "No rate can be calculated: no generation attempts in this period."}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </Scroll>
    );
  }
  return (
    <Panel
      className="analytics-panel"
      role="region"
      ariaLabel="Generation reliability"
    >
      <h2>Generation reliability</h2>
      {body}
    </Panel>
  );
}

const STATUS_LABELS: Record<api.ItemStatus, string> = {
  pending: "Waiting to be graded",
  graded: "Graded",
  grading_failed: "Could not be graded",
  content_expired: "Content no longer retained; not graded",
};

function ItemsTable({ items }: { items: api.Items }) {
  return (
    <Scroll name="Assessed responses">
      <table aria-label="Assessed responses">
        <thead>
          <tr>
            <th scope="col">Received</th>
            <th scope="col">Response time</th>
            <th scope="col">Status</th>
            {api.DIMENSIONS.map((d) => (
              <th scope="col" key={d.id}>
                {d.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.rows.map((row) => (
            <tr key={row.item_id}>
              <td>
                <LocalTime value={row.received_at} />
              </td>
              <td>
                {row.response_time_ms === null
                  ? "—"
                  : `${seconds(row.response_time_ms)} s`}
              </td>
              <td>{STATUS_LABELS[row.status] ?? row.status}</td>
              {api.DIMENSIONS.map((d) => {
                const grade = row.grades.find((g) => g.dimension === d.id);
                return (
                  <td key={d.id}>
                    {grade ? (
                      <>
                        <strong>
                          {grade.score === null ? "Unassessable" : grade.score}
                        </strong>
                        <small className="analytics-reason">
                          {grade.reason}
                        </small>
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </Scroll>
  );
}

type PageView = {
  key: string;
  items: api.Items | null;
  loading: boolean;
  error: string;
};

function QualityBody({
  data,
  recorded,
  page,
  onPage,
}: {
  data: api.Quality;
  recorded: string;
  page: PageView;
  onPage: (offset: number) => void;
}) {
  const {
    grades,
    response_time: time,
    sessions,
    activity_time: activity,
  } = data;
  const items = page.items ?? data.items;
  const noSessions =
    "Unavailable: no conversation sessions are recorded for this workflow.";
  const from = items.rows.length === 0 ? 0 : items.offset + 1;
  const to = items.offset + items.rows.length;
  return (
    <>
      <section aria-labelledby="analytics-grades-title">
        <h3 id="analytics-grades-title">Quality grades</h3>
        {grades.state === "unavailable" ? (
          <p>{unavailable(grades.reason, recorded)}</p>
        ) : grades.state === "not_applicable" ? (
          <p>No responses have been graded for this period yet.</p>
        ) : (
          <ul className="analytics-list">
            {grades.dimensions.map((d) => {
              const label =
                api.DIMENSIONS.find((x) => x.id === d.dimension)?.label ??
                d.dimension;
              return (
                <li key={d.dimension}>
                  {label}:{" "}
                  {d.average === null
                    ? NO_AVERAGE
                    : `${d.average.toFixed(2)} of 5 (${d.graded_count} graded, ${d.unassessable_count} unassessable)`}
                </li>
              );
            })}
          </ul>
        )}
        {grades.state !== "unavailable" && (
          <p>
            {grades.assessed_count} assessed, {grades.pending_count} waiting to
            be graded, {grades.grading_failed_count} could not be graded,{" "}
            {grades.content_expired_count} content no longer retained.
          </p>
        )}
      </section>
      <section aria-labelledby="analytics-time-title">
        <h3 id="analytics-time-title">Response time</h3>
        <p>
          {time.state === "unavailable"
            ? unavailable(time.reason, recorded)
            : time.state === "not_applicable"
              ? NO_AVERAGE
              : `Mean ${seconds(time.mean_ms ?? 0)} s, median ${seconds(time.median_ms ?? 0)} s (${time.successful_count} successful responses); ${time.failed_or_incomplete_count} failed or incomplete requests (no response time)`}
        </p>
      </section>
      <section aria-labelledby="analytics-sessions-title">
        <h3 id="analytics-sessions-title">Session activity</h3>
        <p>
          {sessions.state === "unavailable"
            ? sessions.reason === "no_source"
              ? noSessions
              : unavailable(sessions.reason, recorded)
            : sessions.state === "not_applicable"
              ? NO_AVERAGE
              : `${sessions.session_count} sessions, ${(sessions.average_messages_per_session ?? 0).toFixed(2)} messages per session (user and AI messages)`}
        </p>
      </section>
      <section aria-labelledby="analytics-activity-title">
        <h3 id="analytics-activity-title">Associated activity time</h3>
        <p>
          {activity.state === "unavailable"
            ? activity.reason === "no_source"
              ? noSessions
              : unavailable(activity.reason, recorded)
            : activity.state === "not_applicable"
              ? NO_AVERAGE
              : `${(activity.average_activity_seconds ?? 0).toFixed(1)} s average elapsed time from Practice attempt started to Practice attempt submitted, ${(activity.average_messages_per_session ?? 0).toFixed(2)} messages per session, ${activity.linked_session_count} linked sessions, ${activity.distinct_activity_count} distinct activities, ${activity.excluded_session_count} sessions excluded (activity has no recorded end). Elapsed time includes idle time.`}
        </p>
      </section>
      <section aria-labelledby="analytics-items-title">
        <h3 id="analytics-items-title">Assessed responses</h3>
        {page.error && <Alert severity="error">{page.error}</Alert>}
        {data.items.total === 0 ? (
          <p>No assessed responses in this period.</p>
        ) : (
          <>
            <ItemsTable items={items} />
            <div className="analytics-pager">
              <Button
                variant="outlined"
                disabled={page.loading || items.offset === 0}
                onClick={() =>
                  onPage(Math.max(0, items.offset - api.PAGE_SIZE))
                }
              >
                Previous page
              </Button>
              <p>{`Showing ${from} to ${to} of ${items.total}`}</p>
              <Button
                variant="outlined"
                disabled={page.loading || to >= items.total}
                onClick={() => onPage(items.offset + api.PAGE_SIZE)}
              >
                Next page
              </Button>
            </div>
          </>
        )}
      </section>
    </>
  );
}

function runMessage(run: api.Run): string {
  if (api.isActive(run))
    return `Grading is running: ${run.items_graded} of ${run.items_total} responses graded.`;
  if (run.status === "completed")
    return run.items_total === 0
      ? "No ungraded responses are available for this period."
      : `Grading finished: ${run.items_graded} graded, ${run.items_failed} could not be graded.`;
  const why =
    (run.failure_code && api.RUN_FAILURES[run.failure_code]) ||
    "an unexpected error occurred";
  return `Grading stopped: ${why}. ${run.items_graded} of ${run.items_total} responses were graded before it stopped.`;
}

export default function AdminAnalytics() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [fallback] = useState(api.defaultPeriod);
  const rawFrom = params.get("from") ?? "";
  const rawTo = params.get("to") ?? "";
  const valid =
    Object.keys(api.checkPeriod({ from: rawFrom, to: rawTo })).length === 0;
  const from = valid ? rawFrom : fallback.from;
  const to = valid ? rawTo : fallback.to;
  const rawWorkflow = params.get("workflow");
  const workflow: api.Workflow =
    api.WORKFLOWS.find((w) => w.id === rawWorkflow)?.id ?? "student_exercise";
  const period = useMemo(() => ({ from, to }), [from, to]);

  // An invalid or missing period or workflow in the URL is replaced by the default, without a message.
  useEffect(() => {
    const wanted = new URLSearchParams({ from, to, workflow }).toString();
    if (wanted !== params.toString())
      navigate({ search: `?${wanted}` }, { replace: true });
  }, [from, to, workflow, params, navigate]);

  // Period fields.
  const [fields, setFields] = useState<api.Period>(period);
  const [errors, setErrors] = useState<api.PeriodErrors>({});
  const fromInput = useRef<HTMLInputElement>(null);
  const toInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    setFields(period);
    setErrors({});
  }, [period]);

  function apply(event: FormEvent) {
    event.preventDefault();
    const trimmed = { from: fields.from.trim(), to: fields.to.trim() };
    const problems = api.checkPeriod(trimmed);
    setErrors(problems);
    if (problems.from || problems.to) {
      (problems.from ? fromInput : toInput).current?.focus();
      return;
    }
    if (trimmed.from === from && trimmed.to === to) return;
    navigate({ search: `?${new URLSearchParams({ ...trimmed, workflow })}` });
  }

  function chooseWorkflow(next: api.Workflow) {
    navigate(
      { search: `?${new URLSearchParams({ from, to, workflow: next })}` },
      { replace: true },
    );
  }

  // The three reads. A key change (period, workflow, retry) starts a new read; the old one is aborted.
  const [usageTry, setUsageTry] = useState(0);
  const [generationTry, setGenerationTry] = useState(0);
  const [qualityTry, setQualityTry] = useState(0);
  const usage = useAnalyticsLoad(`usage|${from}|${to}|${usageTry}`, (s) =>
    api.readUsage(period, s),
  );
  const generation = useAnalyticsLoad(
    `generation|${from}|${to}|${generationTry}`,
    (s) => api.readGeneration(period, s),
  );
  const qualityKey = `quality|${from}|${to}|${workflow}|${qualityTry}`;
  const quality = useAnalyticsLoad(qualityKey, (s) =>
    api.readQuality(period, workflow, 0, s),
  );

  // Pagination: a failed page keeps the current one.
  const [page, setPage] = useState<PageView>({
    key: "",
    items: null,
    loading: false,
    error: "",
  });
  const pageAbort = useRef<AbortController | null>(null);
  useEffect(() => () => pageAbort.current?.abort(), [qualityKey]);
  const currentPage: PageView =
    page.key === qualityKey
      ? page
      : { key: qualityKey, items: null, loading: false, error: "" };

  async function goToPage(offset: number) {
    pageAbort.current?.abort();
    const controller = new AbortController();
    pageAbort.current = controller;
    setPage({ ...currentPage, loading: true, error: "" });
    try {
      const next = await api.readQuality(
        period,
        workflow,
        offset,
        controller.signal,
      );
      setPage({
        key: qualityKey,
        items: next.items,
        loading: false,
        error: "",
      });
    } catch (error) {
      if (api.isAborted(error)) return;
      setPage({
        ...currentPage,
        loading: false,
        error: api.loadFailure("Assessed responses", error),
      });
    }
  }

  // Grading run: start, poll about every 3 seconds while queued or running, then reload the quality results once.
  const [run, setRun] = useState<api.Run | null>(null);
  const [startPending, setStartPending] = useState(false);
  const [startError, setStartError] = useState("");
  const [pollError, setPollError] = useState("");
  const [pollTick, setPollTick] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const startAbort = useRef<AbortController | null>(null);
  useEffect(() => () => startAbort.current?.abort(), []);

  const active = quality?.ok ? quality.data.active_run : null;
  useEffect(() => {
    if (active && api.isActive(active))
      setRun((current) => (api.isActive(current) ? current : active));
  }, [active]);

  const runId = run?.run_id;
  const running = api.isActive(run);
  useEffect(() => {
    if (runId === undefined || !running || pollError) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api.readRun(runId, controller.signal).then(
        (next) => {
          setRun(next);
          setPollTick((n) => n + 1);
          if (!api.isActive(next)) setQualityTry((n) => n + 1);
        },
        (error: unknown) => {
          if (!api.isAborted(error)) setPollError(api.pollFailure(error));
        },
      );
    }, POLL_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [runId, running, pollError, pollTick]);

  async function startRun() {
    setConfirming(false);
    setStartPending(true);
    setStartError("");
    setPollError("");
    const controller = new AbortController();
    startAbort.current = controller;
    try {
      setRun(await api.startGradingRun(period, workflow, controller.signal));
    } catch (error) {
      if (api.isAborted(error)) return;
      setStartError(api.startFailure(error));
      // A run is already active: reload so its progress line shows.
      if (error instanceof ApiError && error.status === 409)
        setQualityTry((n) => n + 1);
    } finally {
      setStartPending(false);
    }
  }

  async function checkProgress() {
    if (runId === undefined) return;
    try {
      const next = await api.readRun(runId);
      setPollError("");
      setRun(next);
      if (!api.isActive(next)) setQualityTry((n) => n + 1);
    } catch (error) {
      if (!api.isAborted(error)) setPollError(api.pollFailure(error));
    }
  }

  const recorded = quality?.ok ? quality.data.recording_started_on : "";
  let qualityBody;
  if (quality === null)
    qualityBody = <p role="status">Loading quality results...</p>;
  else if (!quality.ok)
    qualityBody = (
      <PanelFailure
        message={api.loadFailure("Quality results", quality.error)}
        retry={() => setQualityTry((n) => n + 1)}
        label="Retry quality results"
      />
    );
  else
    qualityBody = (
      <QualityBody
        data={quality.data}
        recorded={recorded}
        page={currentPage}
        onPage={(o) => void goToPage(o)}
      />
    );
  return (
    <>
      <PageHeading
        title="Feature analytics"
        description="Review how chatbot, practice and AI generation features are used. Periods use UTC dates."
      />
      <Panel
        className="analytics-panel"
        role="region"
        ariaLabel="Reporting period"
      >
        <h2>Reporting period</h2>
        <form onSubmit={apply} noValidate className="analytics-period">
          <TextField
            id="analytics-from"
            label="From date"
            type="date"
            value={fields.from}
            error={!!errors.from}
            helperText={errors.from}
            inputRef={fromInput}
            slotProps={{ inputLabel: { shrink: true } }}
            onChange={(event) =>
              setFields({ ...fields, from: event.target.value })
            }
          />
          <TextField
            id="analytics-to"
            label="To date"
            type="date"
            value={fields.to}
            error={!!errors.to}
            helperText={errors.to}
            inputRef={toInput}
            slotProps={{ inputLabel: { shrink: true } }}
            onChange={(event) =>
              setFields({ ...fields, to: event.target.value })
            }
          />
          <Button type="submit" variant="contained">
            Apply period
          </Button>
        </form>
        <p className="muted">Periods use UTC dates. Maximum 366 days.</p>
      </Panel>
      <UsagePanel result={usage} retry={() => setUsageTry((n) => n + 1)} />
      <GenerationPanel
        result={generation}
        retry={() => setGenerationTry((n) => n + 1)}
      />
      <Panel
        className="analytics-panel"
        role="region"
        ariaLabel="AI quality and session activity"
      >
        <h2>AI quality and session activity</h2>
        <p className="muted">{NOTICE}</p>
        <p className="muted">
          Timing and message counts are descriptive measurements, not quality
          grades.
        </p>
        <Tabs
          value={workflow}
          onChange={(_, next: api.Workflow) => chooseWorkflow(next)}
          aria-label="Assessment workflow"
          variant="scrollable"
          scrollButtons={false}
        >
          {api.WORKFLOWS.map((w) => (
            <Tab
              key={w.id}
              value={w.id}
              label={w.label}
              id={`analytics-tab-${w.id}`}
              aria-controls="analytics-tabpanel"
            />
          ))}
        </Tabs>
        <div
          role="tabpanel"
          id="analytics-tabpanel"
          aria-labelledby={`analytics-tab-${workflow}`}
          className="analytics-tabpanel"
        >
          <div className="analytics-grading">
            <Button
              variant="outlined"
              onClick={() => setConfirming(true)}
              disabled={startPending || running}
            >
              Grade ungraded responses
            </Button>
            {startError && <Alert severity="error">{startError}</Alert>}
            {run && (
              <p role="status" className="analytics-run">
                {runMessage(run)}
              </p>
            )}
            {pollError && (
              <>
                <Alert severity="warning">{pollError}</Alert>
                <Button variant="outlined" onClick={() => void checkProgress()}>
                  Check progress
                </Button>
              </>
            )}
          </div>
          {qualityBody}
        </div>
        <Dialog
          open={confirming}
          onClose={() => setConfirming(false)}
          aria-labelledby="analytics-grade-title"
        >
          <DialogTitle id="analytics-grade-title">
            Grade responses with AI?
          </DialogTitle>
          <DialogContent>
            <DialogContentText>
              Up to 20 ungraded responses from this workflow and period will be
              sent to the SoC LLM service for grading. Grades are advisory.
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setConfirming(false)}>Cancel</Button>
            <Button variant="contained" onClick={() => void startRun()}>
              Start grading
            </Button>
          </DialogActions>
        </Dialog>
      </Panel>
    </>
  );
}

import { useEffect, useRef, useState, type ReactNode } from "react";
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
} from "@mui/material";
import { useAnalyticsBlock } from "../../hooks/useAnalyticsBlock";
import { ApiError } from "../../services/client";
import * as api from "../../services/featureAnalytics";
import LocalTime from "../LocalTime";
import BlockState from "./BlockState";
import { startsNote, unavailableText } from "./copy";

const POLL_MS = 3000;
const NOTICE =
  "Grades are AI assessments, not verified facts. They do not change access or application content.";
const NO_AVERAGE =
  "No average can be calculated: no eligible records in this period.";
const NO_SESSIONS =
  "Unavailable: no conversation sessions are recorded for this workflow.";
const seconds = (ms: number) => (ms / 1000).toFixed(1);

const STATUS_LABELS: Record<api.ItemStatus, string> = {
  pending: "Waiting to be graded",
  graded: "Graded",
  grading_failed: "Could not be graded",
  content_expired: "Content no longer retained; not graded",
  privacy_blocked: "Excluded by privacy protection",
};

function Scroll({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div
      className="table-scroll analytics-scroll"
      role="region"
      aria-label={`${name}, scrollable`}
      tabIndex={0}
    >
      {children}
    </div>
  );
}

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
  base: api.Quality | null;
  items: api.Items | null;
  loading: boolean;
  error: string;
};

function QualityBody({
  data,
  page,
  onPage,
}: {
  data: api.Quality;
  page: PageView;
  onPage: (offset: number) => void;
}) {
  const { grades, response_time: time, sessions, activity_time: act } = data;
  const recorded = data.recording_started_on;
  const items = page.items ?? data.items;
  const from = items.rows.length === 0 ? 0 : items.offset + 1;
  const to = items.offset + items.rows.length;
  const na = <p>{NO_AVERAGE}</p>;
  return (
    <>
      {data.data_starts_on && (
        <p className="muted">{startsNote(data.data_starts_on)}</p>
      )}
      <div className="analytics-quality-grid">
        <section aria-labelledby="analytics-hub-grades-title">
          <h3 id="analytics-hub-grades-title">Quality grades</h3>
          {grades.state === "unavailable" ? (
            <p>{unavailableText(grades.reason, recorded)}</p>
          ) : grades.state === "not_applicable" ? (
            <p>No responses have been graded for this period yet.</p>
          ) : (
            <ul className="analytics-list">
              {grades.dimensions.map((d) => (
                <li key={d.dimension}>
                  {api.DIMENSIONS.find((x) => x.id === d.dimension)?.label ??
                    d.dimension}
                  :{" "}
                  {d.average === null
                    ? NO_AVERAGE
                    : `${d.average.toFixed(2)} of 5 (${d.graded_count} graded, ${d.unassessable_count} unassessable)`}
                </li>
              ))}
            </ul>
          )}
          {grades.state !== "unavailable" && (
            <p>
              {grades.assessed_count} assessed, {grades.pending_count} waiting
              to be graded, {grades.grading_failed_count} could not be graded,{" "}
              {grades.content_expired_count} content no longer retained.
            </p>
          )}
        </section>
        <section aria-labelledby="analytics-hub-time-title">
          <h3 id="analytics-hub-time-title">Response time</h3>
          {time.state === "unavailable" ? (
            <p>{unavailableText(time.reason, recorded)}</p>
          ) : time.state === "not_applicable" ? (
            na
          ) : (
            <p>
              <span className="analytics-line">
                Mean <strong>{seconds(time.mean_ms ?? 0)} s</strong>,
              </span>{" "}
              <span className="analytics-line">
                median <strong>{seconds(time.median_ms ?? 0)} s</strong>
              </span>{" "}
              <span className="analytics-line-note">
                ({time.successful_count} successful responses);{" "}
                {time.failed_or_incomplete_count} failed or incomplete requests
                (no response time)
              </span>
            </p>
          )}
        </section>
        <section aria-labelledby="analytics-hub-sessions-title">
          <h3 id="analytics-hub-sessions-title">Session activity</h3>
          {sessions.state === "unavailable" ? (
            <p>
              {sessions.reason === "no_source"
                ? NO_SESSIONS
                : unavailableText(sessions.reason, recorded)}
            </p>
          ) : sessions.state === "not_applicable" ? (
            na
          ) : (
            <p>
              <strong>{sessions.session_count} sessions</strong>,{" "}
              {(sessions.average_messages_per_session ?? 0).toFixed(2)} messages
              per session (user and AI messages)
            </p>
          )}
        </section>
        <section aria-labelledby="analytics-hub-activity-title">
          <h3 id="analytics-hub-activity-title">Associated activity time</h3>
          {act.state === "unavailable" ? (
            <p>
              {act.reason === "no_source"
                ? NO_SESSIONS
                : unavailableText(act.reason, recorded)}
            </p>
          ) : act.state === "not_applicable" ? (
            na
          ) : (
            <p>{`${(act.average_activity_seconds ?? 0).toFixed(1)} s average elapsed time from Practice attempt started to Practice attempt submitted, ${(act.average_messages_per_session ?? 0).toFixed(2)} messages per session, ${act.linked_session_count} linked sessions, ${act.distinct_activity_count} distinct activities, ${act.excluded_session_count} sessions excluded (activity has no recorded end). Elapsed time includes idle time.`}</p>
          )}
        </section>
      </div>
      <section aria-labelledby="analytics-hub-items-title">
        <h3 id="analytics-hub-items-title">Assessed responses</h3>
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
  if (run.failure_code === "privacy_scanner_unavailable")
    return api.PRIVACY_UNAVAILABLE;
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

/** Section 4: ADM-01 quality results and the admin-started grading run, moved into the hub with the same behaviour. */
export default function QualitySection({
  period,
  workflow,
  onWorkflow,
  report,
}: {
  period: api.Period;
  workflow: api.Workflow;
  onWorkflow: (next: api.Workflow) => void;
  report: (status: string) => void;
}) {
  const block = useAnalyticsBlock(
    `quality|${period.from}|${period.to}|${workflow}`,
    (signal) => api.readQuality(period, workflow, 0, signal),
  );
  const { reload } = block;
  useEffect(() => report(block.status), [block.status, report]);
  const quality = block.data;

  // Pagination: a failed page keeps the current one.
  const [page, setPage] = useState<PageView>({
    base: null,
    items: null,
    loading: false,
    error: "",
  });
  const pageAbort = useRef<AbortController | null>(null);
  useEffect(() => () => pageAbort.current?.abort(), [quality]);
  const currentPage: PageView =
    page.base === quality && quality !== null
      ? page
      : { base: quality, items: null, loading: false, error: "" };

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
      setPage({ base: quality, items: next.items, loading: false, error: "" });
    } catch (error) {
      if (api.isAborted(error)) return;
      setPage({
        ...currentPage,
        loading: false,
        error: api.loadFailure("Assessed responses", error),
      });
    }
  }

  // Grading run: start, poll about every 3 seconds while queued or running, then reload the results once.
  const [run, setRun] = useState<api.Run | null>(null);
  const [startPending, setStartPending] = useState(false);
  const [startError, setStartError] = useState("");
  const [pollError, setPollError] = useState("");
  const [pollTick, setPollTick] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const startAbort = useRef<AbortController | null>(null);
  useEffect(() => () => startAbort.current?.abort(), []);

  const active = quality?.active_run ?? null;
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
          if (!api.isActive(next)) reload();
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
  }, [runId, running, pollError, pollTick, reload]);

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
      if (error instanceof ApiError && error.status === 409) reload();
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
      if (!api.isActive(next)) reload();
    } catch (error) {
      if (!api.isAborted(error)) setPollError(api.pollFailure(error));
    }
  }

  const strict = quality?.grades.privacy_mode === "strict";
  return (
    <>
      <p className="muted">{NOTICE}</p>
      <p className="muted">
        Timing and message counts are descriptive measurements, not quality
        grades.
      </p>
      <Tabs
        value={workflow}
        onChange={(_, next: api.Workflow) => onWorkflow(next)}
        aria-label="Assessment workflow"
        variant="scrollable"
        scrollButtons={false}
      >
        {api.WORKFLOWS.map((w) => (
          <Tab
            key={w.id}
            value={w.id}
            label={w.label}
            id={`analytics-hub-tab-${w.id}`}
            aria-controls="analytics-hub-tabpanel"
          />
        ))}
      </Tabs>
      <div
        role="tabpanel"
        id="analytics-hub-tabpanel"
        aria-labelledby={`analytics-hub-tab-${workflow}`}
        className="analytics-tabpanel"
      >
        {strict && (
          <p role="status">
            AI grading is disabled until free-text privacy protection is
            approved. Counts and timings remain available.
          </p>
        )}
        {quality && quality.grades.privacy_blocked_count !== null && (
          <p>
            {quality.grades.privacy_blocked_count} responses excluded by privacy
            protection.
          </p>
        )}
        <div className="analytics-grading">
          <Button
            variant="outlined"
            onClick={() => setConfirming(true)}
            disabled={startPending || running || strict}
          >
            Grade ungraded responses
          </Button>
          {startError && <Alert severity="error">{startError}</Alert>}
          {run && (
            <p
              role={
                run.failure_code === "privacy_scanner_unavailable"
                  ? "alert"
                  : "status"
              }
              className="analytics-run"
            >
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
        <BlockState
          block={block}
          loading="Loading quality results..."
          subject="Quality results"
          retryLabel="Retry quality results"
        >
          {(data) => (
            <QualityBody
              data={data}
              page={currentPage}
              onPage={(o) => void goToPage(o)}
            />
          )}
        </BlockState>
      </div>
      <Dialog
        open={confirming}
        onClose={() => setConfirming(false)}
        aria-labelledby="analytics-hub-grade-title"
      >
        <DialogTitle id="analytics-hub-grade-title">
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
    </>
  );
}

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Alert, Button, MenuItem, TextField } from "@mui/material";
import { useLocation } from "react-router";
import { useAuth } from "../auth/AuthContext";
import SignInNotice from "../auth/SignInNotice";
import { PageHeading, Panel } from "../components/ui";
import { ApiError, getSessionGeneration } from "../services/client";
import * as api from "../services/aiUsage";

type View = {
  report: api.UsageReport | null;
  error: string;
  loading: boolean;
  retry: boolean;
};

function MetricCell({ metric }: { metric: api.Metric }) {
  return (
    <td>
      {metric.value === null ? (
        <>
          <span>Unavailable</span>
          <small className="ai-usage-reason">
            {api.REASONS[metric.reason!]}
          </small>
        </>
      ) : (
        metric.value
      )}
    </td>
  );
}

function UsageReport() {
  const [filters, setFilters] = useState(api.defaultFilters);
  const applied = useRef(filters);
  const initial = useRef<Promise<api.UsageReport> | null>(null);
  const serial = useRef(0);
  const [view, setView] = useState<View>({
    report: null,
    error: "",
    loading: true,
    retry: false,
  });

  function load(next: api.Filters, pending?: Promise<api.UsageReport>) {
    const current = ++serial.current;
    const generation = getSessionGeneration();
    applied.current = next;
    setView({ report: null, error: "", loading: true, retry: false });
    void (pending ?? api.readUsage(next))
      .then((report) => {
        if (current === serial.current && generation === getSessionGeneration())
          setView({ report, error: "", loading: false, retry: false });
      })
      .catch((error: unknown) => {
        if (current === serial.current && generation === getSessionGeneration())
          setView({
            report: null,
            error: api.usageError(error),
            loading: false,
            retry: !(
              error instanceof ApiError &&
              [401, 403, 422].includes(error.status)
            ),
          });
      });
  }

  useEffect(() => {
    // StrictMode reattaches to this one activation read; no private cross-page cache.
    initial.current ??= api.readUsage(applied.current);
    load(applied.current, initial.current);
    return () => {
      serial.current += 1;
    };
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (view.loading) return;
    if (!api.validFilters(filters)) {
      serial.current += 1;
      setView({
        report: null,
        error: api.INVALID_FILTERS,
        loading: false,
        retry: false,
      });
      return;
    }
    load({ ...filters });
  }

  const { report } = view;
  return (
    <>
      <PageHeading
        title="AI usage"
        description="Inspect service-call attempts and recorded resource measurements."
      />
      <Panel className="ai-usage-panel">
        <form onSubmit={submit} noValidate className="ai-usage-filters">
          <TextField
            select
            label="Feature"
            value={filters.feature}
            slotProps={{
              select: {
                SelectDisplayProps: {
                  "aria-label": "Feature",
                  "aria-labelledby": undefined,
                },
              },
            }}
            onChange={(event) =>
              setFilters({
                ...filters,
                feature: event.target.value as api.Filters["feature"],
              })
            }
          >
            <MenuItem value="all">All features</MenuItem>
            {Object.entries(api.FEATURE_LABELS).map(([key, label]) => (
              <MenuItem key={key} value={key}>
                {label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Start date (UTC)"
            type="date"
            value={filters.start_date}
            slotProps={{
              inputLabel: { shrink: true },
              htmlInput: { "aria-label": "Start date (UTC)" },
            }}
            onChange={(event) =>
              setFilters({ ...filters, start_date: event.target.value })
            }
          />
          <TextField
            label="End date (UTC)"
            type="date"
            value={filters.end_date}
            slotProps={{
              inputLabel: { shrink: true },
              htmlInput: { "aria-label": "End date (UTC)" },
            }}
            onChange={(event) =>
              setFilters({ ...filters, end_date: event.target.value })
            }
          />
          <Button type="submit" variant="contained" disabled={view.loading}>
            Apply filters
          </Button>
        </form>
        {view.loading && <p role="status">Loading AI usage…</p>}
        {view.error && (
          <Alert
            severity="error"
            action={
              view.retry ? (
                <Button
                  disabled={view.loading}
                  onClick={() => load(applied.current)}
                >
                  Retry
                </Button>
              ) : undefined
            }
          >
            {view.error}
          </Alert>
        )}
        {report && (
          <>
            <p>
              Period: {report.start_date} to {report.end_date} (UTC)
            </p>
            <p className="muted">
              A successful service call may still produce content rejected by
              the feature. Local validation and quota rejections do not dispatch
              a call.
            </p>
            {report.rows.every((row) => row.requests.value === 0) && (
              <p role="status">No AI service calls in this period.</p>
            )}
            <div
              className="table-scroll ai-usage-results"
              role="region"
              aria-label="AI usage results"
              tabIndex={0}
            >
              <table aria-label="AI usage by feature">
                <caption>
                  Service-call attempts, including retries. Dates are UTC. Local
                  quota rejections are excluded.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Feature</th>
                    {Object.entries(api.METRIC_LABELS).map(([key, label]) => (
                      <th scope="col" key={key}>
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {report.rows.map((row) => (
                    <tr key={row.feature}>
                      <th scope="row">
                        {api.FEATURE_LABELS[row.feature]}
                        <small className="ai-usage-reason">
                          {row.coverage_start
                            ? `Collection started: ${row.coverage_start}`
                            : "Collection is not enabled for this feature."}
                        </small>
                      </th>
                      {(Object.keys(api.METRIC_LABELS) as api.MetricKey[]).map(
                        (key) => (
                          <MetricCell key={key} metric={row[key]} />
                        ),
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Panel>
    </>
  );
}

export default function AdminAiUsage() {
  const { status, user } = useAuth();
  const location = useLocation();
  if (status === "loading") return <p role="status">Loading AI usage…</p>;
  if (status !== "authenticated")
    return <SignInNotice message="Sign in to view AI usage." />;
  return (
    <UsageReport
      key={`${user?.id}:${getSessionGeneration()}:${location.key}`}
    />
  );
}

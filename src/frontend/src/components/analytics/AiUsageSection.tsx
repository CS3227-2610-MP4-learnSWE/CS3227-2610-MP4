import { useEffect, useState } from "react";
import { TextField } from "@mui/material";
import { useAnalyticsBlock } from "../../hooks/useAnalyticsBlock";
import { todayUtc } from "../../lib/period";
import * as usage from "../../services/aiUsage";
import { ApiError } from "../../services/client";
import { loadFailure, type Period } from "../../services/featureAnalytics";
import LocalTime from "../LocalTime";
import BlockState from "./BlockState";

const LIMIT_NOTE =
  "Service limits: Unavailable. The SoC LLM service does not report quotas or remaining limits.";
const TOO_LONG =
  "AI usage covers at most 31 days ending today or earlier. Choose a shorter period to see AI usage.";

/** AI usage covers at most 31 days ending today or earlier (ADM-06 rule); otherwise no request is sent. */
export const aiUsageApplies = (period: Period) =>
  usage.validFilters({
    feature: "all",
    start_date: period.from,
    end_date: period.to,
  }) && period.to <= todayUtc();

function aiUsageFailure(subject: string, error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return "You do not have access to AI usage.";
    if (error.status === 422) return usage.INVALID_FILTERS;
    if (error.status === 429)
      return "Too many report requests. Try again shortly.";
    if (error.status === 503)
      return "AI usage data is temporarily unavailable. Try again.";
    if (error.status === 0 && error.code === "bad_response")
      return "The server returned an invalid AI usage report. Try again.";
  }
  return loadFailure(subject, error);
}

function MetricCell({ metric }: { metric: usage.Metric }) {
  return (
    <td>
      {metric.value === null ? (
        <>
          <span>Unavailable</span>
          <small className="analytics-reason">
            {usage.REASONS[metric.reason!]}
          </small>
        </>
      ) : (
        metric.value
      )}
    </td>
  );
}

export default function AiUsageSection({
  period,
  report,
}: {
  period: Period;
  report: (status: string) => void;
}) {
  const [feature, setFeature] = useState<usage.Filters["feature"]>("all");
  const applies = aiUsageApplies(period);
  const block = useAnalyticsBlock(
    `ai|${period.from}|${period.to}|${feature}|${applies}`,
    (signal) =>
      applies
        ? usage.readUsage(
            { feature, start_date: period.from, end_date: period.to },
            signal,
          )
        : Promise.resolve(null),
  );
  useEffect(() => report(block.status), [block.status, report]);
  return (
    <>
      <TextField
        select
        label="Feature"
        value={feature}
        slotProps={{ select: { native: true } }}
        onChange={(e) => setFeature(e.target.value as usage.Filters["feature"])}
        className="analytics-hub-feature"
      >
        <option value="all">All features</option>
        {Object.entries(usage.FEATURE_LABELS).map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </TextField>
      {!applies ? (
        <p role="status">{TOO_LONG}</p>
      ) : (
        <BlockState
          block={block}
          loading="Loading AI usage..."
          subject="AI usage"
          retryLabel="Retry AI usage"
          failure={aiUsageFailure}
        >
          {(data) =>
            data === null ? null : (
              <>
                <p>
                  Period: {data.start_date} to {data.end_date} (UTC)
                </p>
                {data.rows.every((row) => row.requests.value === 0) && (
                  <p role="status">No AI service calls in this period.</p>
                )}
                <div
                  className="table-scroll analytics-scroll"
                  role="region"
                  aria-label="AI usage results"
                  tabIndex={0}
                >
                  <table aria-label="AI usage by feature">
                    <caption>
                      Service-call attempts, including retries. Dates are UTC.
                      Local quota rejections are excluded.
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Feature</th>
                        {Object.values(usage.METRIC_LABELS).map((label) => (
                          <th scope="col" key={label}>
                            {label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data.rows.map((row) => (
                        <tr key={row.feature}>
                          <th scope="row">
                            {usage.FEATURE_LABELS[row.feature]}
                            <small className="analytics-reason">
                              {row.coverage_start ? (
                                <>
                                  Collection started:{" "}
                                  <LocalTime value={row.coverage_start} />
                                </>
                              ) : (
                                "Collection is not enabled for this feature."
                              )}
                            </small>
                          </th>
                          {(
                            Object.keys(
                              usage.METRIC_LABELS,
                            ) as usage.MetricKey[]
                          ).map((key) => (
                            <MetricCell key={key} metric={row[key]} />
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )
          }
        </BlockState>
      )}
      <p className="muted">{LIMIT_NOTE}</p>
    </>
  );
}

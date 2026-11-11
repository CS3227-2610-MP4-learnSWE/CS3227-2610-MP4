import { useMemo, useState } from "react";
import { WEEKDAYS, buildHeatmap, toLocalBucket } from "../../lib/analyticsTime";
import { buildCsv } from "../../lib/csv";
import {
  CATEGORIES,
  type Hourly,
  type Period,
} from "../../services/featureAnalytics";
import ChartCard from "./ChartCard";
import ChartModal, { type TableData } from "./ChartModal";
import {
  FailureRateChart,
  PeakHoursHeatmap,
  RequestsPerHourChart,
} from "./charts";
import { percent1, startsNote, unavailableText } from "./copy";

type ChartId = "requests" | "failure" | "peak";
const TITLES: Record<ChartId, string> = {
  requests: "Requests per hour",
  failure: "Failure rate per hour",
  peak: "Peak hours",
};
const CATEGORY_HEAD = [
  "Timeout",
  "Rate-limited",
  "Invalid output",
  "Upstream",
  "Unclassified",
];
const NO_REQUESTS = "No requests";
const hh = (hour: number) => `${String(hour).padStart(2, "0")}:00`;

/** The three hourly chart cards, their modals and CSV text. All data comes from the one /hourly response. */
export default function HourlyCharts({
  hourly,
  period,
  timeZone,
}: {
  hourly: Hourly;
  period: Period;
  timeZone: string;
}) {
  const [open, setOpen] = useState<ChartId | null>(null);
  const zone = timeZone || "UTC";
  const rows = useMemo(
    () =>
      hourly.buckets.map((bucket) => ({
        bucket,
        local: toLocalBucket(bucket.hour_start, zone),
      })),
    [hourly.buckets, zone],
  );
  const cells = useMemo(
    () => buildHeatmap(hourly.buckets, zone),
    [hourly.buckets, zone],
  );

  if (hourly.state === "unavailable")
    return (
      <div className="analytics-hub-cards">
        {(Object.keys(TITLES) as ChartId[]).map((id) => (
          <ChartCard key={id} title={TITLES[id]} disabled onExpand={() => {}}>
            <p>{unavailableText(hourly.reason, hourly.recording_started_on)}</p>
          </ChartCard>
        ))}
      </div>
    );

  const totals = hourly.totals ?? { successful: 0, failed: 0, total: 0 };
  const empty = totals.total === 0;
  const breakdown = hourly.category_breakdown.state === "available";
  const busiest = cells.reduce((a, b) => (b.total > a.total ? b : a), cells[0]);
  const withRequests = rows.filter((r) => r.bucket.total > 0).length;
  const labels: Record<ChartId, string> = {
    requests: `Requests per hour chart: ${totals.total} requests, ${totals.failed} failed over ${rows.length} hours`,
    failure: `Failure rate per hour chart: ${withRequests} hours with requests, 5% reference line`,
    peak: `Peak hours heatmap: busiest hour ${WEEKDAYS[busiest.weekday]} ${hh(busiest.hour)} with ${busiest.total} requests`,
  };
  const name = (base: string) => `${base}_${period.from}_${period.to}.csv`;
  const rate = (value: number | null) =>
    value === null ? NO_REQUESTS : percent1(value);

  const charts = (large: boolean) => ({
    requests: (
      <RequestsPerHourChart rows={rows} label={labels.requests} large={large} />
    ),
    failure: (
      <FailureRateChart rows={rows} label={labels.failure} large={large} />
    ),
    peak: <PeakHoursHeatmap cells={cells} label={labels.peak} large={large} />,
  });

  const exports: Record<
    ChartId,
    { table: TableData; csv: string; file: string }
  > = {
    requests: {
      file: name("requests-per-hour"),
      table: {
        head: [
          "Hour (local)",
          "Successful",
          "Failed",
          "Total",
          "Failure rate",
          ...CATEGORY_HEAD,
        ],
        rows: rows.map(({ bucket: b, local }) => [
          local.label,
          b.successful,
          b.failed,
          b.total,
          rate(b.failure_rate_percent),
          ...CATEGORIES.map((c) =>
            breakdown ? b.failed_by_category[c] : "Unavailable",
          ),
        ]),
      },
      csv: buildCsv(
        [
          "hour_utc",
          "hour_local",
          "successful",
          "failed",
          "total",
          "failure_rate_percent",
          ...CATEGORIES,
        ],
        rows.map(({ bucket: b, local }) => [
          b.hour_start,
          local.iso,
          b.successful,
          b.failed,
          b.total,
          b.failure_rate_percent,
          ...CATEGORIES.map((c) =>
            breakdown ? b.failed_by_category[c] : null,
          ),
        ]),
      ),
    },
    failure: {
      file: name("failure-rate-per-hour"),
      table: {
        head: ["Hour (local)", "Requests", "Failed", "Failure rate"],
        rows: rows.map(({ bucket: b, local }) => [
          local.label,
          b.total,
          b.failed,
          rate(b.failure_rate_percent),
        ]),
      },
      csv: buildCsv(
        [
          "hour_utc",
          "hour_local",
          "requests",
          "failed",
          "failure_rate_percent",
        ],
        rows.map(({ bucket: b, local }) => [
          b.hour_start,
          local.iso,
          b.total,
          b.failed,
          b.failure_rate_percent,
        ]),
      ),
    },
    peak: {
      file: name("peak-hours"),
      table: {
        head: ["Weekday", "Hour (local)", "Requests", "Failed"],
        rows: cells.map((c) => [
          WEEKDAYS[c.weekday],
          hh(c.hour),
          c.total,
          c.failed,
        ]),
      },
      csv: buildCsv(
        ["weekday", "hour_local", "requests", "failed"],
        cells.map((c) => [WEEKDAYS[c.weekday], c.hour, c.total, c.failed]),
      ),
    },
  };

  return (
    <>
      <div className="analytics-hub-cards">
        {(Object.keys(TITLES) as ChartId[]).map((id) => (
          <ChartCard
            key={id}
            title={TITLES[id]}
            disabled={empty}
            onExpand={() => setOpen(id)}
          >
            {empty ? <p>No requests in this period.</p> : charts(false)[id]}
          </ChartCard>
        ))}
      </div>
      <p className="muted">Times shown in {zone}</p>
      {hourly.in_progress ? (
        <p className="muted">{hourly.in_progress} in progress</p>
      ) : null}
      {hourly.data_starts_on && (
        <p className="muted">{startsNote(hourly.data_starts_on)}</p>
      )}
      {open && (
        <ChartModal
          title={TITLES[open]}
          chart={charts(true)[open]}
          table={exports[open].table}
          csvName={exports[open].file}
          csv={exports[open].csv}
          onClose={() => setOpen(null)}
        />
      )}
    </>
  );
}

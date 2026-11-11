import { useId, useState, type ReactNode } from "react";
import { Button } from "@mui/material";
import type { Daily, DailySeries } from "../../services/featureAnalytics";
import type { TableData } from "./ChartModal";
import { startsNote, unavailableText } from "./copy";

type Series = {
  name: string;
  values: number[];
  kind: "bar" | "line";
  cls: string;
};

const W = 520;
const H = 160;
const LEFT = 34;
const TOP = 8;
const BOTTOM = 22;

/** Small dependency-free bar and line chart; the same data is always available in the card's table. */
function MiniChart({
  label,
  days,
  series,
  stacked,
}: {
  label: string;
  days: string[];
  series: Series[];
  stacked: boolean;
}) {
  const bars = series.filter((s) => s.kind === "bar");
  const lines = series.filter((s) => s.kind === "line");
  const sums = days.map((_, i) =>
    stacked
      ? bars.reduce((t, s) => t + s.values[i], 0)
      : Math.max(0, ...bars.map((s) => s.values[i])),
  );
  const max = Math.max(1, ...sums, ...lines.flatMap((s) => s.values));
  const plotH = H - TOP - BOTTOM;
  const slot = (W - LEFT - 4) / days.length;
  const y = (v: number) => TOP + plotH * (1 - v / max);
  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={label}
        className="analytics-hub-svg"
      >
        <g className="analytics-hub-axes" aria-hidden="true">
          <line x1={LEFT} x2={W - 4} y1={TOP + plotH} y2={TOP + plotH} />
          <text x={LEFT - 4} y={TOP + 10} textAnchor="end">
            {max}
          </text>
          <text x={LEFT - 4} y={TOP + plotH} textAnchor="end">
            0
          </text>
          <text x={LEFT} y={H - 6}>
            {days[0]}
          </text>
          <text x={W - 4} y={H - 6} textAnchor="end">
            {days[days.length - 1]}
          </text>
        </g>
        {days.map((day, i) => {
          let base = 0;
          return bars.map((s, k) => {
            const v = s.values[i];
            const width = stacked ? slot * 0.7 : (slot * 0.8) / bars.length;
            const x = stacked
              ? LEFT + i * slot + slot * 0.15
              : LEFT + i * slot + slot * 0.1 + k * width;
            const from = stacked ? base : 0;
            if (stacked) base += v;
            return (
              <rect
                key={`${day}-${s.name}`}
                x={x}
                y={y(from + v)}
                width={width}
                height={y(from) - y(from + v)}
                className={s.cls}
              />
            );
          });
        })}
        {lines.map((s) => (
          <polyline
            key={s.name}
            className={s.cls}
            points={days
              .map((_, i) => `${LEFT + (i + 0.5) * slot},${y(s.values[i])}`)
              .join(" ")}
          />
        ))}
      </svg>
      <ul className="analytics-hub-legend" aria-label="Legend">
        {series.map((s) => (
          <li key={s.name}>
            <span className={`analytics-hub-swatch ${s.cls}`} />
            {s.name}
          </li>
        ))}
      </ul>
    </div>
  );
}

function DailyCard({
  title,
  table,
  notes = [],
  children,
}: {
  title: string;
  table?: TableData;
  notes?: ReactNode[];
  children: ReactNode;
}) {
  const [shown, setShown] = useState(false);
  const id = useId();
  return (
    <div role="group" aria-label={title} className="analytics-hub-card">
      <h3>{title}</h3>
      {children}
      {notes.map((note, i) => (
        <p key={i} className="muted">
          {note}
        </p>
      ))}
      {table && (
        <>
          <Button
            variant="outlined"
            size="small"
            aria-expanded={shown}
            aria-controls={id}
            onClick={() => setShown(!shown)}
          >
            {shown ? "Hide data table" : "Show data table"}
          </Button>
          <div id={id} hidden={!shown}>
            {shown && (
              <div
                className="table-scroll analytics-scroll"
                role="region"
                aria-label={`${title} data, scrollable`}
                tabIndex={0}
              >
                <table aria-label={`${title} data`}>
                  <thead>
                    <tr>
                      {table.head.map((h) => (
                        <th scope="col" key={h}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((row, i) => (
                      <tr key={i}>
                        {row.map((v, j) =>
                          j === 0 ? (
                            <th scope="row" key={j}>
                              {v}
                            </th>
                          ) : (
                            <td key={j}>{v}</td>
                          ),
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

const num = (row: Record<string, string | number>, key: string) =>
  Number(row[key]);

/** A per-day series card (logins, drafts started, published) with its unavailable, empty and partial states. */
function SeriesCard({
  title,
  data,
  recorded,
  empty,
  total,
  chart,
  head,
  keys,
  notes,
}: {
  title: string;
  data: DailySeries;
  recorded: string;
  empty: string;
  total: number | null | undefined;
  chart: (days: string[]) => Series[];
  head: string[];
  keys: string[];
  notes: string[];
}) {
  if (data.state === "unavailable")
    return (
      <DailyCard title={title}>
        <p>{unavailableText(data.reason, recorded)}</p>
      </DailyCard>
    );
  const days = data.per_day.map((d) => String(d.date));
  const table = {
    head,
    rows: data.per_day.map((d) => keys.map((k) => d[k])),
  };
  const shown = [
    ...notes,
    ...(data.data_starts_on ? [startsNote(data.data_starts_on)] : []),
  ];
  return (
    <DailyCard title={title} table={table} notes={shown}>
      {total === 0 ? (
        <p>{empty}</p>
      ) : (
        <MiniChart
          label={`${title} chart`}
          days={days}
          series={chart(days)}
          stacked
        />
      )}
    </DailyCard>
  );
}

/** Five daily cards from the one /daily response. */
export default function DailyActivity({ daily }: { daily: Daily }) {
  const recorded = daily.recording_started_on;
  const col = (rows: Record<string, string | number>[], key: string) =>
    rows.map((r) => num(r, key));
  const {
    logins,
    practice_drafts_started: drafts,
    practice_published: pub,
  } = daily;
  const funnel = daily.attempts_funnel;
  const perStudent = daily.attempts_per_student;

  return (
    <div className="analytics-hub-cards analytics-hub-daily">
      <SeriesCard
        title="Logins per day"
        data={logins}
        recorded={recorded}
        empty="No logins in this period."
        total={logins.total_logins}
        head={[
          "Date",
          "Student logins",
          "Teacher logins",
          "Total logins",
          "Active students",
          "Active teachers",
          "Active users total",
        ]}
        keys={[
          "date",
          "student_logins",
          "teacher_logins",
          "total_logins",
          "active_students",
          "active_teachers",
          "active_users_total",
        ]}
        notes={["Admin sign-ins are not counted.", "Days are UTC dates."]}
        chart={() => [
          {
            name: "Students",
            values: col(logins.per_day, "student_logins"),
            kind: "bar",
            cls: "analytics-hub-ok",
          },
          {
            name: "Teachers",
            values: col(logins.per_day, "teacher_logins"),
            kind: "bar",
            cls: "analytics-hub-alt",
          },
          {
            name: "Active students",
            values: col(logins.per_day, "active_students"),
            kind: "line",
            cls: "analytics-hub-line",
          },
          {
            name: "Active teachers",
            values: col(logins.per_day, "active_teachers"),
            kind: "line",
            cls: "analytics-hub-line-alt",
          },
        ]}
      />
      <SeriesCard
        title="Practice drafts started per day"
        data={drafts}
        recorded={recorded}
        empty="No practice drafts were started in this period."
        total={drafts.total}
        head={["Date", "Drafts started"]}
        keys={["date", "drafts_started"]}
        notes={["A set is counted once, on the day its first draft was saved."]}
        chart={() => [
          {
            name: "Drafts started",
            values: col(drafts.per_day, "drafts_started"),
            kind: "bar",
            cls: "analytics-hub-ok",
          },
        ]}
      />
      <SeriesCard
        title="Practice sets published per day"
        data={pub}
        recorded={recorded}
        empty="No practice sets were published in this period."
        total={pub.total}
        head={["Date", "Published"]}
        keys={["date", "published"]}
        notes={[
          "A set is counted once, on the day it was first published. Unpublishing and republishing do not change the count.",
        ]}
        chart={() => [
          {
            name: "Published",
            values: col(pub.per_day, "published"),
            kind: "bar",
            cls: "analytics-hub-ok",
          },
        ]}
      />
      <DailyCard
        title="Attempts started and submitted per day"
        table={
          funnel.state === "unavailable"
            ? undefined
            : {
                head: ["Date", "Started", "Submitted"],
                rows: funnel.per_day.map((d) => [
                  d.date,
                  d.started,
                  d.submitted,
                ]),
              }
        }
        notes={
          funnel.state === "unavailable"
            ? []
            : [
                `In this period: ${funnel.started_total} attempts started; ${funnel.submitted_by_period_end} of them submitted by the end of the period.`,
                "Submitted counts use the day of submission, so they can include attempts started earlier.",
                ...(funnel.data_starts_on
                  ? [startsNote(funnel.data_starts_on)]
                  : []),
              ]
        }
      >
        {funnel.state === "unavailable" ? (
          <p>{unavailableText(funnel.reason, recorded)}</p>
        ) : funnel.state === "not_applicable" ? (
          <p>
            Not applicable: no practice attempts were started in this period.
          </p>
        ) : (
          <MiniChart
            label="Attempts started and submitted per day chart"
            days={funnel.per_day.map((d) => d.date)}
            stacked={false}
            series={[
              {
                name: "Started",
                values: funnel.per_day.map((d) => d.started),
                kind: "bar",
                cls: "analytics-hub-ok",
              },
              {
                name: "Submitted",
                values: funnel.per_day.map((d) => d.submitted),
                kind: "bar",
                cls: "analytics-hub-alt",
              },
            ]}
          />
        )}
      </DailyCard>
      <DailyCard
        title="Attempts per student per day"
        table={
          perStudent.state === "unavailable"
            ? undefined
            : {
                head: [
                  "Date",
                  "Students",
                  "Median attempts",
                  "1 attempt",
                  "2 attempts",
                  "3 attempts",
                  "4 attempts",
                  "5 or more",
                ],
                rows: perStudent.per_day.map((d) => [
                  d.date,
                  d.active_students,
                  d.median_attempts ?? "None",
                  d.distribution["1"],
                  d.distribution["2"],
                  d.distribution["3"],
                  d.distribution["4"],
                  d.distribution["5_plus"],
                ]),
              }
        }
        notes={[
          "Days are UTC dates.",
          ...(perStudent.data_starts_on
            ? [startsNote(perStudent.data_starts_on)]
            : []),
        ]}
      >
        {perStudent.state === "unavailable" ? (
          <p>{unavailableText(perStudent.reason, recorded)}</p>
        ) : perStudent.state === "not_applicable" ? (
          <p>No students started attempts in this period.</p>
        ) : (
          <MiniChart
            label="Attempts per student per day chart"
            days={perStudent.per_day.map((d) => d.date)}
            stacked
            series={(["1", "2", "3", "4", "5_plus"] as const).map((k, i) => ({
              name:
                k === "5_plus"
                  ? "5 or more"
                  : `${k} attempt${k === "1" ? "" : "s"}`,
              values: perStudent.per_day.map((d) => d.distribution[k]),
              kind: "bar" as const,
              cls: `analytics-hub-step-${i}`,
            }))}
          />
        )}
      </DailyCard>
    </div>
  );
}

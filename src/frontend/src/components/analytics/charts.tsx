import { useState, type ReactNode } from "react";
import {
  WEEKDAYS,
  type HeatmapCell,
  type LocalBucket,
} from "../../lib/analyticsTime";
import type { HourlyBucket } from "../../services/featureAnalytics";
import { percent1 } from "./copy";

export type HourRow = { bucket: HourlyBucket; local: LocalBucket };

const W = 720;
const LEFT = 44;
const RIGHT = 8;
const TOP = 10;
const BOTTOM = 26;

type Size = { large?: boolean };
const heightOf = ({ large }: Size) => (large ? 340 : 200);

function Tooltip({ text }: { text: string | null }) {
  return (
    <div className="analytics-hub-tooltip-slot">
      {text && <span role="tooltip">{text}</span>}
    </div>
  );
}

function Axes({
  h,
  max,
  title,
  first,
  last,
}: {
  h: number;
  max: number;
  title: string;
  first: string;
  last: string;
}) {
  const plotH = h - TOP - BOTTOM;
  return (
    <g className="analytics-hub-axes" aria-hidden="true">
      <line x1={LEFT} x2={W - RIGHT} y1={TOP + plotH} y2={TOP + plotH} />
      <line x1={LEFT} x2={LEFT} y1={TOP} y2={TOP + plotH} />
      <text x={LEFT - 6} y={TOP + 10} textAnchor="end">
        {max}
      </text>
      <text x={LEFT - 6} y={TOP + plotH} textAnchor="end">
        0
      </text>
      <text x={LEFT} y={h - 8}>
        {first}
      </text>
      <text x={W - RIGHT} y={h - 8} textAnchor="end">
        {last}
      </text>
      <text x={4} y={TOP + plotH / 2} className="analytics-hub-axis-title">
        {title}
      </text>
    </g>
  );
}

function Frame({
  label,
  h,
  children,
}: {
  label: string;
  h: number;
  children: ReactNode;
}) {
  return (
    <svg
      viewBox={`0 0 ${W} ${h}`}
      role="img"
      aria-label={label}
      className="analytics-hub-svg"
    >
      {children}
    </svg>
  );
}

const hourText = (row: HourRow) => row.local.label;

export function RequestsPerHourChart({
  rows,
  label,
  large,
}: { rows: HourRow[]; label: string } & Size) {
  const [hover, setHover] = useState<string | null>(null);
  const h = heightOf({ large });
  const plotH = h - TOP - BOTTOM;
  const bw = (W - LEFT - RIGHT) / rows.length;
  const max = Math.max(1, ...rows.map((r) => r.bucket.total));
  const y = (v: number) => TOP + plotH * (1 - v / max);
  return (
    <div>
      <Frame label={label} h={h}>
        <Axes
          h={h}
          max={max}
          title="Requests"
          first={hourText(rows[0])}
          last={hourText(rows[rows.length - 1])}
        />
        {rows.map(({ bucket: b, local }, i) => {
          const x = LEFT + i * bw;
          const text =
            b.total === 0
              ? `${local.label}: no requests`
              : `${local.label}: ${b.total} requests (${b.successful} successful, ${b.failed} failed, ${percent1(b.failure_rate_percent ?? 0)} failed)`;
          return (
            <g
              key={b.hour_start}
              data-testid={`bar-${b.hour_start}`}
              onMouseEnter={() => setHover(text)}
              onMouseLeave={() => setHover(null)}
            >
              <rect
                x={x}
                y={TOP}
                width={bw}
                height={plotH}
                fill="transparent"
              />
              <rect
                x={x}
                y={y(b.successful)}
                width={Math.max(bw - 0.4, 0.4)}
                height={TOP + plotH - y(b.successful)}
                className="analytics-hub-ok"
              />
              <rect
                x={x}
                y={y(b.total)}
                width={Math.max(bw - 0.4, 0.4)}
                height={y(b.successful) - y(b.total)}
                className="analytics-hub-bad"
              />
            </g>
          );
        })}
      </Frame>
      <ul className="analytics-hub-legend" aria-label="Legend">
        <li>
          <span className="analytics-hub-swatch analytics-hub-ok" />
          Successful
        </li>
        <li>
          <span className="analytics-hub-swatch analytics-hub-bad" />
          Failed
        </li>
      </ul>
      <Tooltip text={hover} />
    </div>
  );
}

export function FailureRateChart({
  rows,
  label,
  large,
}: { rows: HourRow[]; label: string } & Size) {
  const [hover, setHover] = useState<string | null>(null);
  const h = heightOf({ large });
  const plotH = h - TOP - BOTTOM;
  const bw = (W - LEFT - RIGHT) / rows.length;
  const rates = rows.map((r) => r.bucket.failure_rate_percent ?? 0);
  const max = Math.max(10, Math.ceil(Math.max(...rates) / 10) * 10);
  const y = (v: number) => TOP + plotH * (1 - v / max);
  const cx = (i: number) => LEFT + (i + 0.5) * bw;
  const runs: string[] = [];
  let current: string[] = [];
  rows.forEach((r, i) => {
    if (r.bucket.total > 0)
      current.push(`${cx(i)},${y(r.bucket.failure_rate_percent ?? 0)}`);
    else if (current.length) {
      runs.push(current.join(" "));
      current = [];
    }
  });
  if (current.length) runs.push(current.join(" "));
  return (
    <div>
      <Frame label={label} h={h}>
        <Axes
          h={h}
          max={max}
          title="Failure rate (%)"
          first={hourText(rows[0])}
          last={hourText(rows[rows.length - 1])}
        />
        <line
          data-testid="reference-5"
          className="analytics-hub-reference"
          x1={LEFT}
          x2={W - RIGHT}
          y1={y(5)}
          y2={y(5)}
          strokeDasharray="6 4"
        />
        <text
          x={W - RIGHT}
          y={y(5) - 4}
          textAnchor="end"
          className="analytics-hub-axes"
        >
          5%
        </text>
        {runs.map((points) => (
          <polyline
            key={points}
            points={points}
            className="analytics-hub-line"
          />
        ))}
        {rows.map(({ bucket: b, local }, i) => {
          const text =
            b.total === 0
              ? `${local.label}: no requests`
              : `${local.label}: ${percent1(b.failure_rate_percent ?? 0)} failed (${b.failed} of ${b.total} requests)`;
          return (
            <g
              key={b.hour_start}
              data-testid={`point-${b.hour_start}`}
              onMouseEnter={() => setHover(text)}
              onMouseLeave={() => setHover(null)}
            >
              <rect
                x={LEFT + i * bw}
                y={TOP}
                width={bw}
                height={plotH}
                fill="transparent"
              />
              {b.total > 0 && (
                <circle
                  cx={cx(i)}
                  cy={y(b.failure_rate_percent ?? 0)}
                  r={large ? 3 : 2}
                  className="analytics-hub-dot"
                />
              )}
            </g>
          );
        })}
      </Frame>
      <Tooltip text={hover} />
    </div>
  );
}

export function PeakHoursHeatmap({
  cells,
  label,
  large,
}: { cells: HeatmapCell[]; label: string } & Size) {
  const [hover, setHover] = useState<string | null>(null);
  const cw = (W - LEFT - RIGHT) / 24;
  const ch = large ? 34 : 22;
  const h = TOP + 7 * ch + BOTTOM;
  const max = Math.max(1, ...cells.map((c) => c.total));
  return (
    <div>
      <Frame label={label} h={h}>
        <g className="analytics-hub-axes" aria-hidden="true">
          {WEEKDAYS.map((d, i) => (
            <text
              key={d}
              x={LEFT - 6}
              y={TOP + i * ch + ch * 0.65}
              textAnchor="end"
            >
              {d.slice(0, 3)}
            </text>
          ))}
          {[0, 3, 6, 9, 12, 15, 18, 21].map((hour) => (
            <text key={hour} x={LEFT + hour * cw} y={h - 8}>
              {String(hour).padStart(2, "0")}
            </text>
          ))}
        </g>
        {cells.map((c) => {
          const text = `${WEEKDAYS[c.weekday]} ${String(c.hour).padStart(2, "0")}:00: ${c.total} requests, ${c.failed} failed`;
          return (
            <rect
              key={`${c.weekday}-${c.hour}`}
              data-testid={`cell-${c.weekday}-${c.hour}`}
              x={LEFT + c.hour * cw}
              y={TOP + c.weekday * ch}
              width={cw - 1}
              height={ch - 1}
              className="analytics-hub-cell"
              fillOpacity={c.total === 0 ? 0.06 : 0.2 + (0.8 * c.total) / max}
              onMouseEnter={() => setHover(text)}
              onMouseLeave={() => setHover(null)}
            />
          );
        })}
      </Frame>
      <p className="analytics-hub-legend-note">
        Fewer requests{" "}
        <span className="analytics-hub-ramp" aria-hidden="true" /> More requests
      </p>
      <Tooltip text={hover} />
    </div>
  );
}

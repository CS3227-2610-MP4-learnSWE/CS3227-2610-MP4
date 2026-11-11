import type { ReactNode } from "react";
import type { Severity } from "../../services/featureAnalytics";

/** One KPI: label, value, detail lines and optional notes, as a named group. */
export default function KpiTile({
  label,
  value,
  lines = [],
  severity,
  chip,
  valueTestId,
  children,
}: {
  label: string;
  value?: ReactNode;
  lines?: ReactNode[];
  severity?: Severity | null;
  chip?: ReactNode;
  valueTestId?: string;
  children?: ReactNode;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className="analytics-hub-tile"
      data-severity={severity ?? undefined}
    >
      <p className="analytics-hub-tile-label" aria-hidden="true">
        {label}
      </p>
      {value !== undefined && (
        <p className="analytics-hub-tile-value" data-testid={valueTestId}>
          {value}
        </p>
      )}
      {lines.map((line, i) => (
        <p key={i} className="analytics-hub-tile-detail">
          {line}
        </p>
      ))}
      {chip}
      {children}
    </div>
  );
}

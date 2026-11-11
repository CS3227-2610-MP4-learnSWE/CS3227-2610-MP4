import type { ReactNode } from "react";
import { Button } from "@mui/material";

export default function ChartCard({
  title,
  onExpand,
  disabled,
  children,
}: {
  title: string;
  onExpand: () => void;
  disabled: boolean;
  children: ReactNode;
}) {
  return (
    // The whole card opens the chart; the Expand button stays for keyboard and screen-reader users.
    <div
      role="group"
      aria-label={title}
      className={`analytics-hub-card${disabled ? "" : " analytics-hub-card-open"}`}
      title={disabled ? undefined : "Click to expand"}
      onClick={disabled ? undefined : onExpand}
    >
      <div className="analytics-hub-card-head">
        <h3>{title}</h3>
        <Button
          variant="outlined"
          size="small"
          disabled={disabled}
          onClick={(event) => {
            event.stopPropagation();
            onExpand();
          }}
          aria-label={`Expand ${title}`}
        >
          Expand
        </Button>
      </div>
      {children}
    </div>
  );
}

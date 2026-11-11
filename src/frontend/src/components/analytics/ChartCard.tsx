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
    <div role="group" aria-label={title} className="analytics-hub-card">
      <div className="analytics-hub-card-head">
        <h3>{title}</h3>
        <Button
          variant="outlined"
          size="small"
          disabled={disabled}
          onClick={onExpand}
          aria-label={`Expand ${title}`}
        >
          Expand
        </Button>
      </div>
      {children}
    </div>
  );
}

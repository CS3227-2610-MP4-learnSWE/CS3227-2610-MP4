import type { ReactNode } from "react";
import { Alert, Button } from "@mui/material";
import type { Block } from "../../hooks/useAnalyticsBlock";
import { loadFailure } from "../../services/featureAnalytics";

/** Loading, failure with its own Retry button, or the content of one independent block. */
export default function BlockState<T>({
  block,
  loading,
  subject,
  retryLabel,
  failure = loadFailure,
  children,
}: {
  block: Block<T>;
  loading: string;
  subject: string;
  retryLabel: string;
  failure?: (subject: string, error: unknown) => string;
  children: (data: T) => ReactNode;
}) {
  if (block.status === "error")
    return (
      <Alert
        severity="error"
        action={
          <Button color="inherit" size="small" onClick={block.reload}>
            {retryLabel}
          </Button>
        }
      >
        {failure(subject, block.error)}
      </Alert>
    );
  if (block.status !== "success" || block.data === null)
    return <p role="status">{loading}</p>;
  return <>{children(block.data)}</>;
}

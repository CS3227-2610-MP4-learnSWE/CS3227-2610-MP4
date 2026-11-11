import { useCallback, useState } from "react";
import { useAnalyticsLoad } from "./useAnalyticsLoad";

export type BlockStatus = "idle" | "loading" | "success" | "error";
export type Block<T> = {
  status: BlockStatus;
  data: T | null;
  error: unknown;
  reload: () => void;
};

/**
 * One independent block of the hub. The key (plus `deps`) identifies the read; changing it, or calling `reload`,
 * aborts the old read and starts one new request. The shared API layer applies the 15-second timeout and classifies
 * failures (`network`, `timeout`, or an HTTP status); `useAnalyticsLoad` aborts on unmount and ignores stale replies.
 * Nothing is stored.
 */
export function useAnalyticsBlock<T>(
  key: string,
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[] = [],
): Block<T> {
  const [tries, setTries] = useState(0);
  const result = useAnalyticsLoad([key, ...deps, tries].join("|"), fetcher);
  const reload = useCallback(() => setTries((n) => n + 1), []);
  if (result === null)
    return { status: "loading", data: null, error: null, reload };
  return result.ok
    ? { status: "success", data: result.data, error: null, reload }
    : { status: "error", data: null, error: result.error, reload };
}

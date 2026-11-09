import { useEffect, useRef, useState } from "react";
import { isAborted } from "../services/featureAnalytics";

type Entry<T> = {
  controller: AbortController;
  promise: Promise<T>;
  owners: number;
};
export type Loaded<T> = { ok: true; data: T } | { ok: false; error: unknown };

/**
 * One read per `key`: `null` while loading, then the data or the error. The read is aborted when the key changes
 * or the page unmounts. React StrictMode's simulated remount re-attaches to the same read, so a load is never
 * sent twice. To read again, change the key.
 */
export function useAnalyticsLoad<T>(
  key: string,
  fetcher: (signal: AbortSignal) => Promise<T>,
): Loaded<T> | null {
  const [done, setDone] = useState<{ key: string; result: Loaded<T> } | null>(
    null,
  );
  const inflight = useRef(new Map<string, Entry<T>>());
  const latest = useRef(fetcher);
  latest.current = fetcher;

  useEffect(() => {
    let entry = inflight.current.get(key);
    if (!entry) {
      const controller = new AbortController();
      entry = {
        controller,
        owners: 0,
        promise: latest.current(controller.signal),
      };
      inflight.current.set(key, entry);
    }
    const mine = entry;
    mine.owners += 1;
    let active = true;
    setDone(null);
    mine.promise.then(
      (data) => {
        if (active) setDone({ key, result: { ok: true, data } });
      },
      (error: unknown) => {
        if (active && !isAborted(error))
          setDone({ key, result: { ok: false, error } });
      },
    );
    const map = inflight.current;
    return () => {
      active = false;
      mine.owners -= 1;
      // Deferred so the immediate StrictMode re-run can claim the read before it is aborted.
      setTimeout(() => {
        if (mine.owners > 0) return;
        mine.controller.abort();
        if (map.get(key) === mine) map.delete(key);
      }, 0);
    };
  }, [key]);

  return done !== null && done.key === key ? done.result : null;
}

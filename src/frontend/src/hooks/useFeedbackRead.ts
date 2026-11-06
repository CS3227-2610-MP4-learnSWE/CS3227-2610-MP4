import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import {
  feedbackError,
  feedbackRead,
  type Results,
} from "../services/feedbackApi";

/** Each route owns its private result; only pending requests may be shared. */
export function useFeedbackRead<K extends Parameters<typeof feedbackRead>[1]>(
  path: string | null,
  kind: K,
  initialData?: Results[K],
) {
  const location = useLocation();
  const [retry, setRetry] = useState(0);
  const [state, setState] = useState<{
    data: Results[K] | null;
    error: string;
    loading: boolean;
  }>({
    data: initialData ?? null,
    error: "",
    loading: !!path && initialData === undefined,
  });
  const serial = useRef(0);
  const revision = useRef(0);
  const initial = useRef({ data: initialData, path, key: location.key });
  useEffect(() => {
    const current = ++serial.current;
    if (!path) {
      setState({ data: null, error: "", loading: false });
      return;
    }
    // A validated mutation receipt may seed this one mounted history entry.
    // Keep the seed through StrictMode replay; retries and later entries read.
    if (
      retry === 0 &&
      initial.current.data !== undefined &&
      initial.current.path === path &&
      initial.current.key === location.key
    )
      return;
    setState((old) => ({ ...old, error: "", loading: true }));
    const read = feedbackRead(path, kind);
    read.promise
      .then((data) => {
        if (current === serial.current) {
          revision.current++;
          setState({ data, error: "", loading: false });
        }
      })
      .catch((error) => {
        if (current === serial.current)
          setState((old) => ({
            ...old,
            error: feedbackError(error),
            loading: false,
          }));
      });
    return () => {
      serial.current = current + 1;
      read.release();
    };
  }, [path, kind, retry, location.key]);
  // A path change must not flash another form's private response while effects run.
  const previousPath = useRef(path);
  const changed = previousPath.current !== path;
  useEffect(() => {
    previousPath.current = path;
  }, [path]);
  return {
    ...state,
    revision: revision.current,
    data: changed ? null : state.data,
    loading: changed || state.loading,
    reload: () => setRetry((v) => v + 1),
    replace: (data: NonNullable<typeof state.data>) => {
      serial.current++;
      revision.current++;
      setState({ data, error: "", loading: false });
    },
  };
}

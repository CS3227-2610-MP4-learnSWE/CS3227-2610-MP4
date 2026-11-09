import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { getAnalysis, type Analysis } from "../services/feedbackAnalysisApi";
import { ApiError } from "../services/client";
import {
  loadMessage,
  NETWORK_PROGRESS,
  STOPPED_WAITING,
  unreadableStatus,
} from "../messages/feedbackAnalysis";

const INTERVAL_MS = 2000;
const GIVE_UP_MS = 810_000;
const MAX_NETWORK_FAILURES = 3;

/**
 * One GET at mount; while the AI step is running and the tab is visible, one more GET 2 s after the previous
 * reply (never two in flight). Stops on complete or failed, after 3 network failures, on an unreadable reply,
 * after 810 s, and on 401.
 */
export function useAnalysisPolling(analysisId: string) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loadError, setLoadError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [pollError, setPollError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const shown = useRef<Analysis | null>(null);

  useEffect(() => {
    shown.current = null;
    setAnalysis(null);
    setNotFound(false);
  }, [analysisId]);

  // Layout effect: the GET leaves as soon as the page mounts.
  useLayoutEffect(() => {
    let cancelled = false;
    let inflight = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let networkFailures = 0;
    let stopped = false;
    const stop = (message: string) => {
      stopped = true;
      setPollError(message);
    };
    const startedAt = Date.now();
    setLoadError("");
    setPollError("");

    const schedule = () => {
      clearTimeout(timer);
      timer = undefined;
      if (
        cancelled ||
        shown.current?.ai.status !== "running" ||
        document.visibilityState !== "visible"
      )
        return;
      timer = setTimeout(poll, INTERVAL_MS);
    };

    async function poll() {
      timer = undefined;
      if (cancelled || inflight) return;
      if (Date.now() - startedAt >= GIVE_UP_MS) {
        stop(STOPPED_WAITING);
        return;
      }
      inflight = true;
      try {
        const next = await getAnalysis(analysisId);
        if (cancelled) return;
        networkFailures = 0;
        const old = shown.current;
        // An older reply never overwrites newer progress.
        if (!(
          old &&
          next.ai.status === "running" &&
          next.ai.progress.done < old.ai.progress.done
        )) {
          shown.current = next;
          setAnalysis(next);
        }
        setLoadError("");
        setPollError("");
      } catch (error) {
        if (cancelled) return;
        handleFailure(error);
        return;
      } finally {
        inflight = false;
        setLoading(false);
      }
      schedule();
    }

    function handleFailure(error: unknown) {
      const e = error instanceof ApiError ? error : new ApiError(0, "network");
      if (e.status === 401) {
        stopped = true;
        shown.current = null;
        setAnalysis(null);
        setLoadError(loadMessage(e, "the analysis"));
        return;
      }
      if (!shown.current) {
        setNotFound(e.code === "analysis_not_found");
        setLoadError(loadMessage(e, "the analysis"));
        return;
      }
      if (e.status === 0 && (e.code === "network" || e.code === "timeout")) {
        networkFailures += 1;
        if (networkFailures >= MAX_NETWORK_FAILURES) stop(NETWORK_PROGRESS);
        else schedule();
        return;
      }
      if (e.status >= 500 || e.code === "bad_response")
        stop(unreadableStatus(e.status || 200));
      else stop(loadMessage(e, "the analysis"));
    }

    const onVisible = () => {
      if (
        document.visibilityState === "visible" &&
        !timer &&
        !inflight &&
        shown.current?.ai.status === "running" &&
        !stopped
      )
        void poll();
      else if (document.visibilityState !== "visible") {
        clearTimeout(timer);
        timer = undefined;
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [analysisId, attempt]);

  const retry = useCallback(() => {
    setLoading(true);
    setAttempt((n) => n + 1);
  }, []);
  return { analysis, loadError, notFound, pollError, loading, retry };
}

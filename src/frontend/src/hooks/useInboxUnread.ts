import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { getSessionGeneration } from "../services/client";
import { messagingRead } from "../services/messagingApi";

type Source = "messages" | "requests";
type Summary = {
  unread_count: number;
  unread_messages: number;
  unread_requests: number;
};
const changed = "learnswe:inbox-count";
const refresh = "learnswe:inbox-refresh";
export function publishInboxCount(source: Source, count: number) {
  window.dispatchEvent(
    new CustomEvent(changed, {
      detail: { source, count, generation: getSessionGeneration() },
    }),
  );
}
export function refreshInboxUnread() {
  window.dispatchEvent(new Event(refresh));
}

/** Navigation loads counts only; message bodies remain in the inbox. */
export function useInboxUnread() {
  const { status, user } = useAuth();
  const generation = getSessionGeneration();
  const role = user?.role;
  const [state, setState] = useState<{
    generation: number;
    messages: number | null;
    requests: number | null;
  }>({ generation, messages: null, requests: null });
  useEffect(() => {
    setState({ generation, messages: null, requests: null });
    if (status !== "authenticated" || !role || role === "admin") return;
    let alive = true;
    let active: ReturnType<typeof messagingRead<Summary>> | null = null;
    let queued = false;
    let started = 0;
    const revisions = { messages: 0, requests: 0 };
    const load = (force = false) => {
      if (!alive || document.visibilityState === "hidden") return;
      if (active) {
        if (force) queued = true;
        return;
      }
      if (!force && started && Date.now() - started < 5000) return;
      started = Date.now();
      const before = { ...revisions };
      const request = messagingRead<Summary>("/api/messaging/unread-count");
      active = request;
      request.promise
        .then((data) => {
          if (!alive || generation !== getSessionGeneration()) return;
          setState((old) => ({
            generation,
            messages:
              revisions.messages === before.messages
                ? data.unread_messages
                : old.messages,
            requests:
              revisions.requests === before.requests
                ? data.unread_requests
                : old.requests,
          }));
        })
        .catch(() => {
          // Background failure must not invent a zero or interrupt the current task.
        })
        .finally(() => {
          if (!alive) return;
          request.release();
          active = null;
          if (queued) {
            queued = false;
            load(true);
          }
        });
    };
    const onCount = (event: Event) => {
      const detail = (
        event as CustomEvent<{
          generation: number;
          source: Source;
          count: number;
        }>
      ).detail;
      if (detail.generation !== generation) return;
      revisions[detail.source]++;
      setState((old) => ({
        ...old,
        generation,
        [detail.source]: detail.count,
      }));
    };
    const onFocus = () => load();
    const onRefresh = () => load(true);
    window.addEventListener(changed, onCount);
    window.addEventListener(refresh, onRefresh);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    const timer = window.setInterval(onFocus, 60000);
    load();
    return () => {
      alive = false;
      active?.release();
      window.clearInterval(timer);
      window.removeEventListener(changed, onCount);
      window.removeEventListener(refresh, onRefresh);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
    };
  }, [status, user?.id, role, generation]);
  return status === "authenticated" &&
    state.generation === generation &&
    state.messages !== null &&
    state.requests !== null
    ? state.messages + state.requests
    : null;
}

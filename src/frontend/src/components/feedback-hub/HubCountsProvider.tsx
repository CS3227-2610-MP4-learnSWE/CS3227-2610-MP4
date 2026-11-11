import { useEffect, useState, type ReactNode } from "react";
import { getSessionGeneration } from "../../services/client";
import {
  fetchAnalysesCount,
  fetchFollowUpCount,
  fetchFormsCounts,
  type CountSource,
} from "../../services/hubCountsApi";
import {
  subscribeHubCountChange,
  type HubCountTopic,
} from "../../lib/hubCountEvents";
import {
  HubCountsContext,
  initialCounts,
  type Count,
  type HubCounts,
} from "./hubCounts";

const ready = (value: number, truncated = false): Count => ({
  state: "ready",
  value,
  truncated,
});
const sourceOf: Record<HubCountTopic, CountSource> = {
  "forms-changed": "forms",
  "analyses-changed": "analyses",
  "followup-changed": "followup",
};
const countsOf: Record<
  CountSource,
  ("forms" | "responses" | "analysis" | "followUp")[]
> = {
  forms: ["forms", "responses"],
  analyses: ["analysis"],
  followup: ["followUp"],
};

/** Resolves one source to the state update it implies. */
async function fetchSource(
  source: CountSource,
  signal: AbortSignal,
): Promise<(old: HubCounts) => HubCounts> {
  if (source === "forms") {
    const r = await fetchFormsCounts(signal);
    return (old) => ({
      ...old,
      forms: ready(r.open, r.truncated),
      responses: ready(r.submitted, r.truncated),
      drafts: r.drafts,
    });
  }
  if (source === "analyses") {
    const r = await fetchAnalysesCount(signal);
    return (old) => ({ ...old, analysis: ready(r.value, r.truncated) });
  }
  const value = await fetchFollowUpCount(signal);
  return (old) => ({ ...old, followUp: ready(value) });
}

type Update = (old: HubCounts) => HubCounts;
type Shared = {
  promise: Promise<Update>;
  controller: AbortController;
  users: number;
  timer?: ReturnType<typeof setTimeout>;
};
// Count requests in flight, keyed by session and source. Own namespace: never merged with the Responses chooser's request.
const inflight = new Map<string, Shared>();

/** Joins the request in flight for a source (or starts one). Release aborts it only if nobody re-joins in the same tick. */
function join(source: CountSource, fresh: boolean) {
  const key = `${getSessionGeneration()}:hub-count:${source}`;
  let entry = inflight.get(key);
  if (entry && fresh) {
    entry.controller.abort();
    inflight.delete(key);
    entry = undefined;
  }
  if (!entry) {
    const controller = new AbortController();
    const created: Shared = {
      controller,
      users: 0,
      promise: fetchSource(source, controller.signal).finally(() => {
        if (inflight.get(key) === created) inflight.delete(key);
      }),
    };
    entry = created;
    inflight.set(key, entry);
  }
  entry.users++;
  clearTimeout(entry.timer);
  const owned = entry;
  return {
    promise: owned.promise,
    signal: owned.controller.signal,
    release: () => {
      owned.users--;
      if (!owned.users)
        owned.timer = setTimeout(() => {
          if (!owned.users) owned.controller.abort();
        }, 0);
    },
  };
}

/**
 * Loads the three tab counts once per hub mount and refetches one source after a count-changing mutation
 * (latest wins). Failures are silent: a count that never loaded stays hidden, a loaded one keeps its value.
 * A 401 is handled by the shared request layer. Nothing is stored.
 */
export default function HubCountsProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [counts, setCounts] = useState<HubCounts>(initialCounts);
  useEffect(() => {
    const generation = getSessionGeneration();
    const holds: Partial<Record<CountSource, ReturnType<typeof join>>> = {};
    let alive = true;
    const load = (source: CountSource, fresh: boolean) => {
      holds[source]?.release();
      const hold = join(source, fresh);
      holds[source] = hold;
      const current = () =>
        alive &&
        holds[source] === hold &&
        !hold.signal.aborted &&
        generation === getSessionGeneration();
      hold.promise.then(
        (apply) => current() && setCounts(apply),
        () => {
          if (!current()) return;
          // Never loaded: stays hidden as unavailable; already loaded: the last good value is kept.
          setCounts((old) => {
            const next = { ...old };
            for (const key of countsOf[source])
              if (old[key].state === "loading")
                next[key] = { ...old[key], state: "unavailable" };
            return next;
          });
        },
      );
    };
    (["forms", "analyses", "followup"] as CountSource[]).forEach((source) =>
      load(source, false),
    );
    const unsubscribe = subscribeHubCountChange((topic) =>
      load(sourceOf[topic], true),
    );
    return () => {
      alive = false;
      unsubscribe();
      Object.values(holds).forEach((hold) => hold?.release());
    };
  }, []);
  return (
    <HubCountsContext.Provider value={counts}>
      {children}
    </HubCountsContext.Provider>
  );
}

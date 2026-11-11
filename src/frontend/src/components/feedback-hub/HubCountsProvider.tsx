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
    const controllers: Partial<Record<CountSource, AbortController>> = {};
    let alive = true;
    const load = (source: CountSource) => {
      controllers[source]?.abort();
      const controller = new AbortController();
      controllers[source] = controller;
      const current = () =>
        alive &&
        !controller.signal.aborted &&
        generation === getSessionGeneration();
      fetchSource(source, controller.signal).then(
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
    (["forms", "analyses", "followup"] as CountSource[]).forEach(load);
    const unsubscribe = subscribeHubCountChange((topic) =>
      load(sourceOf[topic]),
    );
    return () => {
      alive = false;
      unsubscribe();
      Object.values(controllers).forEach((c) => c?.abort());
    };
  }, []);
  return (
    <HubCountsContext.Provider value={counts}>
      {children}
    </HubCountsContext.Provider>
  );
}

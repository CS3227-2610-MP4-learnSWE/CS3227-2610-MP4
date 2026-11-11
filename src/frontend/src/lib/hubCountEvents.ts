/** Payload-free, in-memory notifications that a mutation changed a Feedback hub tab count. Never persisted. */
export type HubCountTopic =
  "forms-changed" | "analyses-changed" | "followup-changed";

const listeners = new Set<(topic: HubCountTopic) => void>();

export function emitHubCountChange(topic: HubCountTopic): void {
  for (const listener of [...listeners]) {
    try {
      listener(topic);
    } catch {
      // One failing listener must not stop the others.
    }
  }
}

export function subscribeHubCountChange(
  listener: (topic: HubCountTopic) => void,
): () => void {
  // A wrapper keeps each subscription separate even if the same function is passed twice.
  const entry = (topic: HubCountTopic) => listener(topic);
  listeners.add(entry);
  return () => {
    listeners.delete(entry);
  };
}

import { getSessionGeneration, request } from "./client";

// Identical GETs already in flight share one request (React StrictMode runs
// effects twice in development); a finished request is never reused, and a
// request started before a sign-in/out or a write is never shared with a page
// opened after it.
const inFlight = new Map<string, Promise<unknown>>();
let writes = 0;

export function readOnce(path: string): Promise<unknown> {
  const key = `${getSessionGeneration()}:${writes}:${path}`;
  const pending = inFlight.get(key);
  if (pending) return pending;
  const started = request("GET", path).finally(() => inFlight.delete(key));
  inFlight.set(key, started);
  return started;
}

/** Call before and after a write so reads started around it are not shared. */
export function markWrite(): void {
  writes += 1;
}

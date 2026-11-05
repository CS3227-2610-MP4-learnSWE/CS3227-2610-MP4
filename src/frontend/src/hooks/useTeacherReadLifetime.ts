import { useLayoutEffect, useRef } from "react";
import { invalidateTeacherReads } from "../services/client";

/** A new selection must not join reads started for an abandoned selection.
 * Layout timing precedes new read effects; the unchanged ref preserves StrictMode replay.
 */
export function useTeacherReadLifetime(selection: string) {
  const previous = useRef<string | null>(null);
  useLayoutEffect(() => {
    if (previous.current !== selection) invalidateTeacherReads();
    previous.current = selection;
  }, [selection]);
}

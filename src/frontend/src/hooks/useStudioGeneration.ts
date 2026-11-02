import { useLayoutEffect, useRef, useState } from "react";
import { useLocation } from "react-router";

export function useStudioGeneration(selection: string) {
  const location = useLocation();
  const epoch = useRef(0);
  const mounted = useRef(false);
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);

  useLayoutEffect(() => {
    // Returning to an earlier URL or selection must never revive its request.
    epoch.current += 1;
  }, [location, selection]);
  useLayoutEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const start = () => {
    if (pending.current) return null;
    pending.current = true;
    setBusy(true);
    const startedEpoch = epoch.current;
    return {
      isCurrent: () => mounted.current && epoch.current === startedEpoch,
      finish: () => {
        pending.current = false;
        if (mounted.current) setBusy(false);
      },
    };
  };

  return { busy, start };
}

import { useCallback, useEffect, useRef } from "react";
import {
  useBeforeUnload,
  useBlocker,
  type BlockerFunction,
} from "react-router";

export function useDraftNavigationGuard(dirty: boolean, saving: boolean) {
  const blocker = useBlocker(
    useCallback<BlockerFunction>(
      ({ currentLocation, nextLocation }) =>
        (dirty || saving) &&
        (currentLocation.pathname !== nextLocation.pathname ||
          currentLocation.search !== nextLocation.search ||
          currentLocation.hash !== nextLocation.hash),
      [dirty, saving],
    ),
  );
  useBeforeUnload(
    useCallback(
      (event) => {
        if (dirty || saving) {
          event.preventDefault();
          event.returnValue = "";
        }
      },
      [dirty, saving],
    ),
  );
  const wasSaving = useRef(false);
  useEffect(() => {
    if (wasSaving.current && !saving && blocker.state === "blocked")
      blocker.reset();
    wasSaving.current = saving;
  }, [saving, blocker]);
  return blocker;
}

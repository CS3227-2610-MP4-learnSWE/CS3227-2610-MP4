import { useEffect, useState } from "react";
import {
  listPublications,
  publicationError,
  type Publication,
} from "../services/publications";

export function usePublications(courseId: string) {
  const [state, setState] = useState<{ course: string; items: Publication[] }>({
    course: "",
    items: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [completed, setCompleted] = useState(0);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    setError("");
    if (!courseId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    listPublications(courseId)
      .then((items) => {
        if (active) {
          setState({ course: courseId, items });
          setCompleted((value) => value + 1);
        }
      })
      .catch((reason) => {
        if (active)
          setError(
            publicationError(
              reason,
              "Could not load publication status. Please try again.",
            ),
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [courseId, reload]);
  return {
    completed,
    items: state.course === courseId ? state.items : [],
    loading,
    ready: state.course === courseId && !loading && !error,
    error,
    retry: () => setReload((value) => value + 1),
    update: (item: Publication) =>
      setState((previous) => ({
        course: courseId,
        items: [
          item,
          ...previous.items.filter(
            (p) => p.id !== item.id || p.kind !== item.kind,
          ),
        ],
      })),
  };
}

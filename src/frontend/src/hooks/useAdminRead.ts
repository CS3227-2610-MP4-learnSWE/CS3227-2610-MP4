import { useCallback, useEffect, useRef, useState } from "react";
import { adminError } from "../services/adminAccess";

/** Each view owns its result; stale reads cannot overwrite a newer selection. */
export function useAdminRead<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const serial = useRef(0);
  const reload = useCallback(async () => {
    const current = ++serial.current;
    setLoading(true);
    setError("");
    try {
      const next = await load();
      if (current === serial.current) setData(next);
    } catch (failure) {
      if (current === serial.current) {
        setError(adminError(failure));
        setData(null);
      }
    } finally {
      if (current === serial.current) setLoading(false);
    }
  }, [load]);
  useEffect(() => {
    setData(null);
    void reload();
    return () => {
      serial.current += 1;
    };
  }, [reload]);
  const replaceData = useCallback((value: T) => {
    serial.current += 1;
    setData(value);
    setError("");
    setLoading(false);
  }, []);
  return { data, setData: replaceData, error, loading, reload };
}

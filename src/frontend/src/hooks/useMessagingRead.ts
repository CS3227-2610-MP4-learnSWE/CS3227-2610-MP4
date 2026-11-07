import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";
import {
  messagingCode,
  messagingError,
  messagingRead,
} from "../services/messagingApi";

export function useMessagingRead<T>(path: string | null) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [retry, setRetry] = useState(0);
  const [state, setState] = useState<{
    path: string | null;
    key: string;
    data: T | null;
    error: string;
    code: string;
    loading: boolean;
  }>({
    path,
    key: location.key,
    data: null,
    error: "",
    code: "",
    loading: !!path,
  });
  useEffect(() => {
    let alive = true;
    setState({
      path,
      key: location.key,
      data: null,
      error: "",
      code: "",
      loading: !!path,
    });
    if (!path) return;
    const read = messagingRead<T>(path);
    read.promise
      .then((data) => {
        if (alive)
          setState({
            path,
            key: location.key,
            data,
            error: "",
            code: "",
            loading: false,
          });
      })
      .catch((error) => {
        if (!alive || messagingCode(error) === "stale_session") return;
        if (messagingCode(error) === "forbidden")
          navigate(`/${user?.role}/overview`, { replace: true });
        setState({
          path,
          key: location.key,
          data: null,
          error: messagingError(error),
          code: messagingCode(error),
          loading: false,
        });
      });
    return () => {
      alive = false;
      read.release();
    };
  }, [path, retry, location.key, navigate, user?.role]);
  const changed = path !== state.path || location.key !== state.key;
  return {
    ...state,
    data: changed ? null : state.data,
    error: changed ? "" : state.error,
    loading: changed ? !!path : state.loading,
    reload: () => setRetry((n) => n + 1),
  };
}

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router";
import {
  login as loginRequest,
  logout as logoutRequest,
  me,
  signup as signupRequest,
  type AuthUser,
} from "../services/auth";
import { setCsrfToken, setUnauthenticatedHandler } from "../services/client";

type Status = "loading" | "anonymous" | "authenticated";
type Auth = {
  status: Status;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<AuthUser>;
  signup: (
    displayName: string,
    email: string,
    password: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
};
const Context = createContext<Auth | null>(null);

/** Session state from the server. Nothing is written to browser storage; the CSRF token stays in memory. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [state, setState] = useState<{ status: Status; user: AuthUser | null }>(
    {
      status: "loading",
      user: null,
    },
  );
  const status = useRef<Status>("loading");
  status.current = state.status;

  const clear = () => {
    setCsrfToken(null);
    setState({ status: "anonymous", user: null });
  };

  useEffect(() => {
    let cancelled = false;
    // A 401, or any failure, means anonymous here: not an error, and demo mode keeps working.
    me()
      .then((session) => {
        if (cancelled) return;
        setCsrfToken(session.csrf_token);
        setState({ status: "authenticated", user: session.user });
      })
      .catch(() => {
        if (!cancelled) clear();
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // A session that expired or was revoked: leave only when the client believed it was signed in.
  useEffect(() => {
    setUnauthenticatedHandler(() => {
      if (status.current !== "authenticated") return;
      clear();
      navigate("/login", { replace: true });
    });
    return () => setUnauthenticatedHandler(null);
  }, [navigate]);

  const value: Auth = {
    ...state,
    login: async (email, password) => {
      const session = await loginRequest(email, password);
      setCsrfToken(session.csrf_token);
      setState({ status: "authenticated", user: session.user });
      return session.user;
    },
    signup: signupRequest,
    logout: async () => {
      try {
        await logoutRequest();
      } catch {
        /* the cookie may already be gone; the local state is cleared either way */
      }
      clear();
      navigate("/login", { replace: true });
    },
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}

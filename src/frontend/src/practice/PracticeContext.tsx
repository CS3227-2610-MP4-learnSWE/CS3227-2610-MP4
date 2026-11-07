import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ApiError } from "../services/client";
import {
  getResults,
  getSet,
  saveAnswers,
  startAttempt,
  submitAttempt,
  type PracticeSet,
  type Results,
} from "../services/practice";
import { isSignInNeeded } from "../auth/SignInNotice";

type Phase = "editing" | "submitting" | "submitted";
type Message = "incomplete" | "retry" | null;
// Steps of one submission; a retry repeats only the step that failed.
type Step = "save" | "submit" | "results";

type PracticeState = {
  // The set the state belongs to; a different set id resets everything.
  setId: string | null;
  load: "idle" | "loading" | "ready" | "error";
  set: PracticeSet | null;
  choices: Record<string, string>;
  phase: Phase;
  results: Results | null;
  message: Message;
  missing: string[];
  // Set when a failed submission cannot be edited any more (the server already holds the answers).
  locked: boolean;
  // The attempt id while the results are shown, for the study companion. Null otherwise.
  submittedAttemptId: string | null;
  // The last failure was 401: the page shows the sign-in notice when the visitor is in demo mode.
  signInNeeded: boolean;
  // "load": the set could not be opened (404/422); "later": a later step answered 404 set_not_found.
  unavailable: "load" | "later" | null;
  // The set load answered 403.
  forbidden: boolean;
};

type Practice = PracticeState & {
  submitted: boolean;
  loadSet: (setId: string) => void;
  choose: (questionId: string, choiceId: string) => void;
  submit: () => void;
  startAnother: () => void;
};

const initial: PracticeState = {
  setId: null,
  load: "idle",
  set: null,
  choices: {},
  phase: "editing",
  results: null,
  message: null,
  missing: [],
  locked: false,
  submittedAttemptId: null,
  signInNeeded: false,
  unavailable: null,
  forbidden: false,
};
const Context = createContext<Practice | null>(null);

export function PracticeProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PracticeState>(initial);
  const patch = (changes: Partial<PracticeState>) =>
    setState((s) => ({ ...s, ...changes }));
  // Flow data that must not trigger renders. The attempt id lives in memory only.
  const attemptId = useRef<string | null>(null);
  const step = useRef<Step>("save");
  const busy = useRef(false);
  const loadToken = useRef(0);
  // Bumped when a different set is opened; work started for an older one is dropped.
  const epoch = useRef(0);
  const live = useRef(state);
  live.current = state;

  const loadSet = useCallback((setId: string) => {
    const held = live.current;
    if (
      held.setId === setId &&
      (held.load === "ready" || held.load === "loading")
    )
      return;
    if (held.setId !== setId) {
      epoch.current += 1;
      attemptId.current = null;
      step.current = "save";
      busy.current = false;
    }
    const mine = epoch.current;
    const token = ++loadToken.current;
    const current = () => mine === epoch.current && token === loadToken.current;
    setState((s) =>
      s.setId === setId
        ? {
            ...s,
            load: "loading",
            unavailable: null,
            forbidden: false,
            signInNeeded: false,
          }
        : { ...initial, setId, load: "loading" },
    );
    live.current = { ...live.current, setId, load: "loading" };
    getSet(setId)
      .then(
        (set) => current() && setState((s) => ({ ...s, load: "ready", set })),
      )
      .catch((error) => {
        if (!current()) return;
        const status = error instanceof ApiError ? error.status : 0;
        setState((s) => ({
          ...s,
          load: "error",
          signInNeeded: isSignInNeeded(error),
          unavailable: status === 404 || status === 422 ? "load" : null,
          forbidden: status === 403,
        }));
      });
  }, []);

  const finish = async (mine: number) => {
    const results = await getResults(attemptId.current!);
    if (mine !== epoch.current) return;
    patch({
      results,
      phase: "submitted",
      message: null,
      missing: [],
      submittedAttemptId: attemptId.current,
    });
  };

  // Runs the submission from the current step. Returns normally on success or a handled failure.
  const run = async () => {
    const mine = epoch.current;
    const { set, choices } = live.current;
    const missing = set!.questions
      .filter((q) => !choices[q.id])
      .map((q) => q.id);
    if (step.current === "save" && missing.length > 0) {
      patch({ message: "incomplete", missing });
      return;
    }
    let renewed = false;
    patch({ phase: "submitting", message: null, missing: [] });
    try {
      for (;;) {
        try {
          if (step.current === "save") {
            if (!attemptId.current) {
              const started = await startAttempt(set!.id);
              if (mine !== epoch.current) return;
              attemptId.current = started;
            }
            await saveAnswers(attemptId.current, choices);
            if (mine !== epoch.current) return;
            step.current = "submit";
          }
          if (step.current === "submit") {
            await submitAttempt(attemptId.current!);
            if (mine !== epoch.current) return;
            step.current = "results";
          }
          await finish(mine);
          return;
        } catch (error) {
          if (mine !== epoch.current) return;
          if (!(error instanceof ApiError)) throw error;
          if (error.status === 404 && error.code === "set_not_found") {
            patch({
              unavailable: "later",
              phase: "editing",
              set: null,
              choices: {},
              results: null,
              submittedAttemptId: null,
              message: null,
              missing: [],
              locked: false,
            });
            return;
          }
          if (error.status === 409 && step.current !== "results") {
            step.current = "results";
          } else if (
            error.status === 404 &&
            error.code === "attempt_not_found" &&
            !renewed
          ) {
            renewed = true;
            attemptId.current = null;
            step.current = "save";
          } else if (error.status === 422 && error.code === "incomplete") {
            step.current = "save";
            patch({
              phase: "editing",
              message: "incomplete",
              missing: error.missing,
              locked: false,
            });
            return;
          } else throw error;
        }
      }
    } catch (error) {
      if (mine !== epoch.current) return;
      patch({
        phase: "editing",
        message: "retry",
        locked: step.current !== "save",
        signInNeeded: isSignInNeeded(error),
      });
    }
  };

  const submit = () => {
    if (busy.current || live.current.phase !== "editing" || !live.current.set)
      return;
    busy.current = true;
    const mine = epoch.current;
    run().finally(() => {
      if (mine === epoch.current) busy.current = false;
    });
  };

  const value: Practice = {
    ...state,
    submitted: state.phase === "submitted",
    loadSet,
    choose: (questionId, choiceId) =>
      setState((s) =>
        s.phase === "editing" && step.current === "save"
          ? { ...s, choices: { ...s.choices, [questionId]: choiceId } }
          : s,
      ),
    submit,
    startAnother: () => {
      attemptId.current = null;
      step.current = "save";
      setState((s) => ({
        ...initial,
        setId: s.setId,
        load: s.load,
        set: s.set,
      }));
    },
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function usePractice() {
  const state = useContext(Context);
  if (!state) throw new Error("PracticeProvider is required");
  return state;
}

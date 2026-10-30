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
import { PRACTICE_SET_ID } from "../config";

type Phase = "editing" | "submitting" | "submitted";
type Message = "incomplete" | "retry" | null;
// Steps of one submission; a retry repeats only the step that failed.
type Step = "save" | "submit" | "results";

type PracticeState = {
  load: "idle" | "loading" | "ready" | "error";
  set: PracticeSet | null;
  choices: Record<string, string>;
  phase: Phase;
  results: Results | null;
  message: Message;
  missing: string[];
  // Set when a failed submission cannot be edited any more (the server already holds the answers).
  locked: boolean;
};

type Practice = PracticeState & {
  submitted: boolean;
  loadSet: () => void;
  choose: (questionId: string, choiceId: string) => void;
  submit: () => void;
  startAnother: () => void;
};

const initial: PracticeState = {
  load: "idle",
  set: null,
  choices: {},
  phase: "editing",
  results: null,
  message: null,
  missing: [],
  locked: false,
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
  const loading = useRef(false);
  const live = useRef(state);
  live.current = state;

  const loadSet = useCallback(() => {
    if (loading.current) return;
    loading.current = true;
    setState((s) => ({ ...s, load: "loading" }));
    getSet(PRACTICE_SET_ID)
      .then((set) => setState((s) => ({ ...s, load: "ready", set })))
      .catch(() => setState((s) => ({ ...s, load: "error" })))
      .finally(() => {
        loading.current = false;
      });
  }, []);

  const finish = async () => {
    const results = await getResults(attemptId.current!);
    patch({ results, phase: "submitted", message: null, missing: [] });
  };

  // Runs the submission from the current step. Returns normally on success or a handled failure.
  const run = async () => {
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
            if (!attemptId.current)
              attemptId.current = await startAttempt(set!.id);
            await saveAnswers(attemptId.current, choices);
            step.current = "submit";
          }
          if (step.current === "submit") {
            await submitAttempt(attemptId.current!);
            step.current = "results";
          }
          await finish();
          return;
        } catch (error) {
          if (!(error instanceof ApiError)) throw error;
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
            });
            return;
          } else throw error;
        }
      }
    } catch {
      patch({
        phase: "editing",
        message: "retry",
        locked: step.current !== "save",
      });
    }
  };

  const submit = () => {
    if (busy.current || live.current.phase !== "editing" || !live.current.set)
      return;
    busy.current = true;
    run().finally(() => {
      busy.current = false;
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
      setState((s) => ({ ...initial, load: s.load, set: s.set }));
    },
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function usePractice() {
  const state = useContext(Context);
  if (!state) throw new Error("PracticeProvider is required");
  return state;
}

import { useCallback, useEffect, useRef, useState } from "react";
import {
  useBeforeUnload,
  useBlocker,
  type BlockerFunction,
} from "react-router";
import {
  feedbackCode,
  feedbackError,
  feedbackRead,
  feedbackWrite,
  recipientBase,
  uncertain,
  type Answer,
  type RecipientForm,
} from "../services/feedbackApi";

function restored(form: RecipientForm): Answer[] {
  const saved = new Map(
    form.draft?.answers.map((a) => [a.question_id, a.value]),
  );
  return form.questions.map((q) => ({
    question_id: q.id,
    value: saved.get(q.id) ?? null,
  }));
}

/** Owns only one recipient's private editing lifecycle; no answers enter storage. */
export function useResponseDraft(initial: RecipientForm) {
  const [form, setForm] = useState(initial);
  const [answers, setAnswers] = useState<Answer[]>(() => restored(initial));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [saved, setSaved] = useState(!!initial.draft?.version);
  const [error, setError] = useState("");
  const [code, setCode] = useState("");
  const [reloadDialog, setReloadDialog] = useState(false);
  const [completedNow, setCompletedNow] = useState(false);
  const [checking, setChecking] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const values = useRef(answers);
  const version = useRef(initial.draft?.version ?? 0);
  const changed = useRef(false);
  const paused = useRef(false);
  const accessLost = useRef(false);
  const alive = useRef(true);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inFlight = useRef<Promise<boolean> | null>(null);
  const controller = useRef<AbortController | null>(null);
  const formRef = useRef(form);
  const afterCheck = useRef<RecipientForm | null>(null);
  const saveRef = useRef<() => Promise<boolean>>(async () => false);
  const pause = useCallback((value: boolean) => {
    paused.current = value;
    setBlocked(value);
  }, []);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      clearTimeout(timer.current);
      controller.current?.abort();
    };
  }, []);

  const terminal = useCallback(
    (failure: unknown) => {
      const reason = feedbackCode(failure);
      if (
        [
          "feedback_closed",
          "feedback_already_submitted",
          "feedback_not_found",
          "forbidden",
          "unauthenticated",
        ].includes(reason)
      ) {
        clearTimeout(timer.current);
        pause(true);
        values.current = [];
        changed.current = false;
        afterCheck.current = null;
        setReloadDialog(false);
        setAnswers([]);
        setDirty(false);
        setSaved(false);
        if (reason === "feedback_closed") {
          const next = {
            ...formRef.current,
            state: "closed" as const,
            questions: [],
            draft: null,
          };
          formRef.current = next;
          setForm(next);
        } else if (reason === "feedback_already_submitted") {
          const next = {
            ...formRef.current,
            submitted: true,
            questions: [],
            draft: null,
          };
          formRef.current = next;
          setForm(next);
        } else {
          // Loss of record/role access is terminal for this mounted editor.
          // Retry, delayed autosave and unchanged-save paths must all respect it.
          accessLost.current = true;
          setUnavailable(true);
          const next = { ...formRef.current, questions: [], draft: null };
          formRef.current = next;
          setForm(next);
        }
      }
    },
    [pause],
  );

  const save = useCallback(async (): Promise<boolean> => {
    clearTimeout(timer.current);
    if (accessLost.current || !alive.current) return false;
    if (inFlight.current) {
      const success = await inFlight.current;
      return success && changed.current ? saveRef.current() : success;
    }
    if (!changed.current) return true;
    if (
      paused.current ||
      !alive.current ||
      formRef.current.submitted ||
      formRef.current.state !== "open"
    )
      return false;
    const snapshot = values.current.map((a) => ({ ...a }));
    const hash = JSON.stringify(snapshot);
    const requestController = new AbortController();
    controller.current = requestController;
    setSaving(true);
    setError("");
    setCode("");
    const operation = (async () => {
      try {
        const draft = await feedbackWrite(
          "PUT",
          `${recipientBase}/${initial.id}/draft`,
          "draft",
          { version: version.current, answers: snapshot },
          requestController.signal,
        );
        if (!alive.current) return false;
        version.current = draft.version;
        changed.current = JSON.stringify(values.current) !== hash;
        setDirty(changed.current);
        setSaved(true);
        return true;
      } catch (failure) {
        if (!alive.current) return false;
        pause(true);
        setError(feedbackError(failure));
        setCode(feedbackCode(failure));
        terminal(failure);
        return false;
      } finally {
        inFlight.current = null;
        if (alive.current) {
          setSaving(false);
          if (changed.current && !paused.current)
            timer.current = setTimeout(() => {
              void saveRef.current();
            }, 1000);
        }
      }
    })();
    inFlight.current = operation;
    return operation;
  }, [initial.id, terminal, pause]);
  useEffect(() => {
    saveRef.current = save;
  }, [save]);

  function change(questionId: string, value: Answer["value"]) {
    if (
      accessLost.current ||
      form.submitted ||
      form.state !== "open" ||
      submitting ||
      leaving ||
      checking ||
      code === "feedback_draft_version_conflict"
    )
      return;
    const next = values.current.map((a) =>
      a.question_id === questionId ? { question_id: questionId, value } : a,
    );
    values.current = next;
    changed.current = true;
    setAnswers(next);
    setDirty(true);
    setSaved(false);
    clearTimeout(timer.current);
    if (!paused.current)
      timer.current = setTimeout(() => {
        void saveRef.current();
      }, 1000);
  }

  const blocker = useBlocker(
    useCallback<BlockerFunction>(
      ({ currentLocation, nextLocation }) =>
        (dirty || saving) && currentLocation.key !== nextLocation.key,
      [dirty, saving],
    ),
  );
  const handledBlock = useRef(false);
  useEffect(() => {
    if (blocker.state !== "blocked") {
      handledBlock.current = false;
      return;
    }
    if (handledBlock.current) return;
    handledBlock.current = true;
    setLeaving(true);
    void saveRef.current().then((success) => {
      if (!alive.current) return;
      setLeaving(false);
      if (blocker.state === "blocked") {
        if (success) blocker.proceed();
        else blocker.reset();
      }
    });
  }, [blocker]);
  useBeforeUnload(
    useCallback((event) => {
      if (changed.current || inFlight.current) {
        event.preventDefault();
        event.returnValue = "";
      }
    }, []),
  );

  async function submit() {
    if (
      accessLost.current ||
      submitting ||
      paused.current ||
      form.submitted ||
      form.state !== "open"
    )
      return;
    clearTimeout(timer.current);
    setSubmitting(true);
    setError("");
    setCode("");
    const pending = inFlight.current;
    if (pending && !(await pending)) {
      if (alive.current) setSubmitting(false);
      return;
    }
    if (!alive.current) return;
    // The final POST includes current edits; no redundant autosave is needed.
    clearTimeout(timer.current);
    pause(true);
    const requestController = new AbortController();
    controller.current = requestController;
    try {
      await feedbackWrite(
        "POST",
        `${recipientBase}/${initial.id}/responses`,
        "receipt",
        { draft_version: version.current, answers: values.current },
        requestController.signal,
      );
      if (!alive.current) return;
      const next = {
        ...formRef.current,
        submitted: true,
        draft: null,
        questions: [],
      };
      formRef.current = next;
      setForm(next);
      values.current = [];
      changed.current = false;
      setAnswers([]);
      setDirty(false);
      setCompletedNow(true);
    } catch (failure) {
      if (!alive.current) return;
      const reason = feedbackCode(failure);
      setError(feedbackError(failure));
      setCode(uncertain(failure) ? "uncertain_submission" : reason);
      terminal(failure);
      if (
        reason === "invalid_feedback_answers" ||
        reason === "invalid_feedback_input"
      )
        pause(false);
    } finally {
      if (alive.current) setSubmitting(false);
    }
  }

  function retry() {
    if (
      accessLost.current ||
      formRef.current.submitted ||
      formRef.current.state !== "open" ||
      code === "feedback_draft_version_conflict" ||
      code === "uncertain_submission"
    )
      return;
    pause(false);
    setError("");
    setCode("");
    void save();
  }
  function applyReload(next: RecipientForm) {
    formRef.current = next;
    setForm(next);
    const nextAnswers = restored(next);
    values.current = nextAnswers;
    setAnswers(nextAnswers);
    version.current = next.draft?.version ?? 0;
    changed.current = false;
    pause(false);
    setDirty(false);
    setSaved(!!next.draft?.version);
    setError("");
    setCode("");
  }
  async function loadCurrent(confirm = false) {
    if (checking || accessLost.current) return;
    setChecking(true);
    const read = feedbackRead(`${recipientBase}/${initial.id}`, "recipient");
    try {
      const next = await read.promise;
      if (!alive.current) return;
      if (next.submitted || next.state === "closed" || confirm)
        applyReload(next);
      else {
        afterCheck.current = next;
        setReloadDialog(true);
      }
    } catch (failure) {
      if (alive.current) {
        setError(feedbackError(failure));
        terminal(failure);
      }
    } finally {
      read.release();
      if (alive.current) setChecking(false);
    }
  }
  async function confirmReload() {
    if (accessLost.current) return;
    setReloadDialog(false);
    if (afterCheck.current) {
      applyReload(afterCheck.current);
      afterCheck.current = null;
    } else await loadCurrent(true);
  }
  return {
    form,
    answers,
    change,
    dirty,
    saving,
    submitting,
    leaving,
    saved,
    error,
    code,
    submit,
    retry,
    completedNow,
    checking,
    reloadDialog,
    openReload: () => {
      afterCheck.current = null;
      setReloadDialog(true);
    },
    cancelReload: () => {
      afterCheck.current = null;
      setReloadDialog(false);
    },
    confirmReload,
    checkStatus: () => void loadCurrent(),
    blocked,
    unavailable,
  };
}

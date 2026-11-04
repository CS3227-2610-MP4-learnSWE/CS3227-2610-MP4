import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormLabel,
  Radio,
  RadioGroup,
  TextField,
} from "@mui/material";
import { ApiError } from "../services/client";
import {
  getMcqDraft,
  saveMcqDraft,
  type McqDraft,
  type McqDraftQuestion,
} from "../services/teacherMcqs";
import { teacherMutationError } from "../services/teacherMutations";
import { normalise, count, invalidText } from "../services/draftText";
import { useDraftNavigationGuard } from "../hooks/useDraftNavigationGuard";

type Props = {
  draft: McqDraft;
  onSaved: (draft: McqDraft) => void;
  onEditingChange: (value: boolean) => void;
  onSavingChange: (value: boolean) => void;
  deleteControl: ReactNode;
};
const copy = (questions: McqDraftQuestion[]) =>
  questions.map((q) => ({ ...q, choices: [...q.choices] }));
const clean = (questions: McqDraftQuestion[]) =>
  questions.map((q) => ({
    ...q,
    question: normalise(q.question),
    explanation: normalise(q.explanation),
    choices: q.choices.map(normalise),
  }));
const textValid = (text: string, max: number) =>
  count(normalise(text)) >= 1 &&
  count(normalise(text)) <= max &&
  !invalidText(text);
const duplicates = (items: string[]) =>
  new Set(items.map((v) => normalise(v).toLocaleLowerCase())).size !==
  items.length;

export default function McqDraftEditor({
  draft,
  onSaved,
  onEditingChange,
  onSavingChange,
  deleteControl,
}: Props) {
  const [baseline, setBaseline] = useState(draft);
  const [questions, setQuestions] = useState(() => copy(draft.questions));
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [notice, setNotice] = useState("");
  const [intent, setIntent] = useState<"cancel" | "latest" | null>(null);
  const operation = useRef(0);
  const mounted = useRef(true);
  const pending = useRef(false);
  const canonical = clean(questions);
  const dirty =
    editing && JSON.stringify(questions) !== JSON.stringify(baseline.questions);
  const changed =
    JSON.stringify(canonical) !== JSON.stringify(clean(baseline.questions));
  const stemDuplicate = duplicates(questions.map((q) => q.question));
  const valid =
    !stemDuplicate &&
    questions.every(
      (q) =>
        textValid(q.question, 200) &&
        textValid(q.explanation, 200) &&
        q.choices.every((v) => textValid(v, 80)) &&
        !duplicates(q.choices),
    );
  const blocker = useDraftNavigationGuard(dirty, saving);
  const blocked = blocker.state === "blocked";
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      operation.current += 1;
    };
  }, []);
  useEffect(() => {
    onEditingChange(editing);
    return () => onEditingChange(false);
  }, [editing, onEditingChange]);
  useEffect(() => {
    onSavingChange(saving);
    return () => onSavingChange(false);
  }, [saving, onSavingChange]);
  const start = () => {
    setBaseline(draft);
    setQuestions(copy(draft.questions));
    setEditing(true);
    setError("");
    setConflict(false);
    setNotice("");
  };
  const cancel = () => {
    if (saving) return;
    operation.current += 1;
    pending.current = false;
    setLoading(false);
    setEditing(false);
    setError("");
    setConflict(false);
    setIntent(null);
  };
  const matches = (saved: McqDraft) =>
    saved.id === baseline.id &&
    saved.course_id === baseline.course_id &&
    saved.source_material_id === baseline.source_material_id &&
    saved.source_title === baseline.source_title &&
    saved.created_by === baseline.created_by &&
    saved.created_at === baseline.created_at &&
    saved.questions.every(
      (q, i) =>
        q.id === baseline.questions[i].id &&
        q.position === baseline.questions[i].position,
    );
  const save = async () => {
    if (pending.current || !valid || !changed || conflict) return;
    pending.current = true;
    setSaving(true);
    setError("");
    const token = ++operation.current;
    try {
      const saved = await saveMcqDraft(baseline.id, {
        version: baseline.version,
        questions: canonical.map((q) => ({
          id: q.id,
          question: q.question,
          choices: q.choices,
          correct_choice_index: q.correct_choice_index,
          explanation: q.explanation,
        })),
      });
      if (!mounted.current || token !== operation.current) return;
      if (
        !matches(saved) ||
        saved.version !== baseline.version + 1 ||
        JSON.stringify(clean(saved.questions)) !== JSON.stringify(canonical)
      )
        throw new Error("Invalid saved MCQs");
      onSaved(saved);
      setBaseline(saved);
      setEditing(false);
      setNotice("Question changes saved.");
    } catch (reason) {
      if (mounted.current && token === operation.current) {
        setConflict(
          reason instanceof ApiError && reason.code === "draft_conflict",
        );
        setError(teacherMutationError(reason, "save"));
      }
    } finally {
      if (mounted.current && token === operation.current) {
        pending.current = false;
        setSaving(false);
      }
    }
  };
  const loadLatest = async () => {
    if (pending.current) return;
    pending.current = true;
    setLoading(true);
    setIntent(null);
    setError("");
    const token = ++operation.current;
    try {
      const latest = await getMcqDraft(baseline.id);
      if (!mounted.current || token !== operation.current) return;
      if (!matches(latest) || latest.version < baseline.version)
        throw new Error("Invalid latest MCQs");
      setBaseline(latest);
      setQuestions(copy(latest.questions));
      setConflict(false);
      onSaved(latest);
    } catch {
      if (mounted.current && token === operation.current)
        setError(
          "Could not load the latest saved version. Your edits are still here.",
        );
    } finally {
      if (mounted.current && token === operation.current) {
        pending.current = false;
        setLoading(false);
      }
    }
  };
  const keep = () => {
    setIntent(null);
    if (blocker.state === "blocked") blocker.reset();
  };
  const discard = () => {
    if (saving) return;
    if (blocker.state === "blocked") {
      cancel();
      blocker.proceed();
    } else if (intent === "latest") void loadLatest();
    else cancel();
  };
  const update = (index: number, values: Partial<McqDraftQuestion>) =>
    setQuestions((items) =>
      items.map((q, i) => (i === index ? { ...q, ...values } : q)),
    );
  const fieldHelp = (value: string, maximum: number) =>
    textValid(value, maximum)
      ? `${count(normalise(value))} / ${maximum} characters`
      : `Enter 1–${maximum} characters.`;
  return (
    <>
      <h2>{draft.source_title}</h2>
      <p className="muted">
        Source: {draft.source_title}
        <br />
        Created by: {draft.created_by}
        <br />
        Created: {new Date(draft.created_at).toLocaleString()}
        <br />
        Last edited by: {draft.updated_by}
        <br />
        Last edited: {new Date(draft.updated_at).toLocaleString()}
      </p>
      {editing ? (
        <div className="note-editor">
          {questions.map((q, i) => (
            <section key={q.id} className="mcq-editor-question">
              <TextField
                label={`Question ${i + 1}`}
                value={q.question}
                onChange={(event) =>
                  update(i, { question: event.target.value })
                }
                disabled={saving || loading}
                error={!textValid(q.question, 200) || stemDuplicate}
                helperText={
                  stemDuplicate
                    ? "Questions must be distinct."
                    : fieldHelp(q.question, 200)
                }
                multiline
              />
              {q.choices.map((choice, c) => (
                <TextField
                  key={c}
                  label={`Question ${i + 1} choice ${String.fromCharCode(65 + c)}`}
                  value={choice}
                  onChange={(event) =>
                    update(i, {
                      choices: q.choices.map((v, n) =>
                        n === c ? event.target.value : v,
                      ),
                    })
                  }
                  disabled={saving || loading}
                  error={!textValid(choice, 80) || duplicates(q.choices)}
                  helperText={
                    duplicates(q.choices)
                      ? "Choices must be distinct."
                      : fieldHelp(choice, 80)
                  }
                />
              ))}
              <FormControl disabled={saving || loading}>
                <FormLabel id={`correct-${q.id}`}>
                  Question {i + 1} correct answer
                </FormLabel>
                <RadioGroup
                  aria-labelledby={`correct-${q.id}`}
                  value={q.correct_choice_index}
                  onChange={(event) =>
                    update(i, {
                      correct_choice_index: Number(event.target.value),
                    })
                  }
                >
                  {q.choices.map((_, c) => (
                    <FormControlLabel
                      key={c}
                      value={c}
                      control={<Radio />}
                      label={`Choice ${String.fromCharCode(65 + c)}`}
                    />
                  ))}
                </RadioGroup>
              </FormControl>
              <TextField
                label={`Question ${i + 1} explanation`}
                value={q.explanation}
                onChange={(event) =>
                  update(i, { explanation: event.target.value })
                }
                disabled={saving || loading}
                error={!textValid(q.explanation, 200)}
                helperText={fieldHelp(q.explanation, 200)}
                multiline
              />
            </section>
          ))}
          {error && <p role="alert">{error}</p>}
          {conflict && (
            <Button
              disabled={saving || loading}
              onClick={() => setIntent("latest")}
            >
              Load latest saved version
            </Button>
          )}
          <div className="note-editor-actions">
            <Button
              variant="contained"
              onClick={save}
              disabled={saving || loading || !valid || !changed || conflict}
            >
              {saving
                ? "Saving…"
                : error && !conflict
                  ? "Retry save"
                  : "Save changes"}
            </Button>
            <Button
              disabled={saving || loading}
              onClick={() => (dirty ? setIntent("cancel") : cancel())}
            >
              Cancel
            </Button>
          </div>
          {saving && <p role="status">Saving changes…</p>}
          {loading && <p role="status">Loading latest saved version…</p>}
        </div>
      ) : (
        <>
          <ol className="mcq-questions">
            {draft.questions.map((q) => (
              <li key={q.id}>
                <h3>{q.question}</h3>
                <ol type="A" aria-label={`Choices for question ${q.position}`}>
                  {q.choices.map((choice, i) => (
                    <li key={i}>{choice}</li>
                  ))}
                </ol>
                <p>
                  <strong>Correct answer:</strong>{" "}
                  {String.fromCharCode(65 + q.correct_choice_index)}.{" "}
                  {q.choices[q.correct_choice_index]}
                </p>
                <p>
                  <strong>Explanation:</strong> {q.explanation}
                </p>
              </li>
            ))}
          </ol>
          <Button variant="outlined" onClick={start}>
            Edit questions
          </Button>
          {deleteControl}
        </>
      )}
      {notice && <p role="status">{notice}</p>}
      <Dialog
        open={blocked || intent !== null}
        onClose={saving ? undefined : keep}
        aria-labelledby="mcq-guard-heading"
      >
        <DialogTitle id="mcq-guard-heading">
          {saving
            ? "Saving changes"
            : intent === "latest" && !blocked
              ? "Load latest saved version?"
              : "Unsaved changes"}
        </DialogTitle>
        <DialogContent>
          {saving
            ? "Wait for the save to finish before leaving."
            : intent === "latest" && !blocked
              ? "Loading the latest saved version will discard your local changes."
              : "Discard your unsaved question changes?"}
        </DialogContent>
        <DialogActions>
          <Button onClick={keep}>
            {saving ? "Stay here" : "Keep editing"}
          </Button>
          {!saving && <Button onClick={discard}>Discard changes</Button>}
        </DialogActions>
      </Dialog>
    </>
  );
}

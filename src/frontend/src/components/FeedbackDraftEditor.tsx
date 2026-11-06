import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  TextField,
} from "@mui/material";
import { PageHeading, Panel } from "./ui";
import { useDraftNavigationGuard } from "../hooks/useDraftNavigationGuard";
import { useFeedbackRead } from "../hooks/useFeedbackRead";
import {
  adminBase,
  feedbackCode,
  feedbackError,
  feedbackWrite,
  uncertain,
  type Definition,
  type Form,
  type Question,
  type QuestionType,
} from "../services/feedbackApi";

const typeLabels: [QuestionType, string][] = [
  ["short_answer", "Short answer"],
  ["paragraph", "Paragraph"],
  ["multiple_choice", "Multiple choice"],
  ["dropdown", "Dropdown"],
  ["checkbox", "Checkboxes"],
  ["linear_scale", "Linear scale"],
];
const choice = (type: string) =>
  ["multiple_choice", "dropdown", "checkbox"].includes(type);
const freshOption = () => ({ id: crypto.randomUUID(), label: "" });

function Questions({
  questions,
  change,
}: {
  questions: Question[];
  change: (questions: Question[]) => void;
}) {
  function update(index: number, patch: Partial<Question>) {
    change(questions.map((q, i) => (i === index ? { ...q, ...patch } : q)));
  }
  return (
    <>
      {!questions.length && <p>Add a question to get started.</p>}
      {questions.map((q, i) => (
        <fieldset className="feedback-question" key={q.id}>
          <legend>Question {i + 1}</legend>
          <TextField
            select
            label={`Question ${i + 1} type`}
            value={q.type}
            slotProps={{
              select: { native: true },
              inputLabel: { shrink: true },
            }}
            onChange={(e) => {
              const type = e.target.value as QuestionType;
              update(i, {
                type,
                options: choice(type)
                  ? choice(q.type)
                    ? q.options
                    : [freshOption(), freshOption()]
                  : [],
                scale:
                  type === "linear_scale"
                    ? { min: 1, max: 5, min_label: "", max_label: "" }
                    : null,
              });
            }}
          >
            {typeLabels.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </TextField>
          <TextField
            label={`Question ${i + 1} prompt`}
            value={q.prompt}
            onChange={(e) => update(i, { prompt: e.target.value })}
          />
          <FormControlLabel
            label={`Question ${i + 1} required`}
            control={
              <Checkbox
                checked={q.required}
                onChange={(e) => update(i, { required: e.target.checked })}
              />
            }
          />
          {choice(q.type) && (
            <>
              {q.options.map((o, j) => (
                <div className="feedback-option" key={o.id}>
                  <TextField
                    label={`Question ${i + 1} option ${j + 1}`}
                    value={o.label}
                    onChange={(e) =>
                      update(i, {
                        options: q.options.map((item, k) =>
                          k === j ? { ...item, label: e.target.value } : item,
                        ),
                      })
                    }
                  />
                  <Button
                    onClick={() =>
                      update(i, {
                        options: q.options.filter((_, k) => k !== j),
                      })
                    }
                  >
                    Remove question {i + 1} option {j + 1}
                  </Button>
                </div>
              ))}
              <Button
                disabled={q.options.length >= 20}
                onClick={() =>
                  update(i, { options: [...q.options, freshOption()] })
                }
              >
                Add option to question {i + 1}
              </Button>
            </>
          )}
          {q.scale && (
            <div className="feedback-scale-fields">
              {(["min", "max"] as const).map((field) => (
                <TextField
                  key={field}
                  type="number"
                  label={`Question ${i + 1} ${field === "min" ? "minimum" : "maximum"}`}
                  value={q.scale![field]}
                  onChange={(e) =>
                    update(i, {
                      scale: { ...q.scale!, [field]: Number(e.target.value) },
                    })
                  }
                />
              ))}
              {(["min_label", "max_label"] as const).map((field) => (
                <TextField
                  key={field}
                  label={`Question ${i + 1} ${field === "min_label" ? "minimum" : "maximum"} label`}
                  value={q.scale![field]}
                  onChange={(e) =>
                    update(i, {
                      scale: { ...q.scale!, [field]: e.target.value },
                    })
                  }
                />
              ))}
            </div>
          )}
          <Button onClick={() => change(questions.filter((_, j) => j !== i))}>
            Remove question {i + 1}
          </Button>
        </fieldset>
      ))}
      <Button
        disabled={questions.length >= 30}
        onClick={() =>
          change([
            ...questions,
            {
              id: crypto.randomUUID(),
              type: "short_answer",
              prompt: "",
              required: false,
              options: [],
              scale: null,
            },
          ])
        }
      >
        Add question
      </Button>
    </>
  );
}

export default function FeedbackDraftEditor({ initial }: { initial?: Form }) {
  const navigate = useNavigate();
  const associations = useFeedbackRead(
    "/api/admin/feedback/associations",
    "associations",
  );
  const [data, setData] = useState<Definition>(() =>
    initial
      ? {
          title: initial.title,
          description: initial.description,
          association: initial.association,
          questions: initial.questions,
        }
      : { title: "", description: "", association: null, questions: [] },
  );
  const [version, setVersion] = useState(initial?.version ?? 0);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [code, setCode] = useState("");
  const [success, setSuccess] = useState("");
  const [destination, setDestination] = useState<string | null>(null);
  const controls = useRef<HTMLFormElement>(null);
  const alive = useRef(true);
  const controller = useRef<AbortController | null>(null);
  const blocker = useDraftNavigationGuard(dirty, saving);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (destination && !dirty)
      navigate(destination, {
        replace: true,
        state: { notice: "Draft saved." },
      });
  }, [destination, dirty, navigate]);
  function change(patch: Partial<Definition>) {
    setData((old) => ({ ...old, ...patch }));
    setDirty(true);
    setSuccess("");
    setError("");
  }
  useEffect(() => {
    if (!error || saving) return;
    let label = "Form title";
    if (code === "invalid_feedback_text") label = "Description";
    if (code === "invalid_feedback_association")
      label = data.association?.kind === "lesson" ? "Lesson" : "Feature";
    if (code === "invalid_feedback_questions") {
      const index = data.questions.findIndex(
        (q) => !q.prompt.trim() || [...q.prompt.trim()].length > 500,
      );
      label = index >= 0 ? `Question ${index + 1} prompt` : "";
    }
    if (code === "invalid_feedback_options") {
      const index = data.questions.findIndex(
        (q) =>
          choice(q.type) &&
          (q.options.length < 2 ||
            q.options.length > 20 ||
            q.options.some(
              (o, i) =>
                !o.label.trim() ||
                [...o.label.trim()].length > 200 ||
                q.options.some(
                  (other, j) =>
                    j < i &&
                    other.label.trim().toLocaleLowerCase() ===
                      o.label.trim().toLocaleLowerCase(),
                ),
            )),
      );
      if (index >= 0) label = `Question ${index + 1} option 1`;
    }
    if (code === "invalid_feedback_scale") {
      const index = data.questions.findIndex(
        (q) =>
          q.scale &&
          (!Number.isInteger(q.scale.min) ||
            !Number.isInteger(q.scale.max) ||
            q.scale.min < 0 ||
            q.scale.max > 10 ||
            q.scale.min >= q.scale.max),
      );
      if (index >= 0) label = `Question ${index + 1} minimum`;
    }
    const target = Array.from(
      controls.current?.querySelectorAll("label") ?? [],
    ).find((item) => item.textContent === label);
    if (target?.htmlFor) document.getElementById(target.htmlFor)?.focus();
    else if (!label)
      controls.current?.querySelector<HTMLButtonElement>("button")?.focus();
  }, [error, saving, code, data]);
  async function save() {
    if (saving || code === "uncertain_mutation") return;
    setSaving(true);
    setError("");
    setCode("");
    setSuccess("");
    const pending = new AbortController();
    controller.current = pending;
    try {
      const row = await feedbackWrite(
        initial ? "PUT" : "POST",
        initial ? `${adminBase}/${initial.id}` : adminBase,
        "form",
        initial ? { ...data, version } : data,
        pending.signal,
      );
      if (!alive.current) return;
      setData({
        title: row.title,
        description: row.description,
        association: row.association,
        questions: row.questions,
      });
      setVersion(row.version);
      setDirty(false);
      setSuccess("Draft saved.");
      if (!initial) setDestination(`/admin/feedback/${row.id}`);
    } catch (failure) {
      if (alive.current) {
        setError(feedbackError(failure));
        setCode(
          uncertain(failure) ? "uncertain_mutation" : feedbackCode(failure),
        );
      }
    } finally {
      if (alive.current) setSaving(false);
    }
  }
  return (
    <>
      <PageHeading
        eyebrow="FEEDBACK"
        title={initial ? "Edit feedback form" : "New feedback form"}
        description="Prepare your questions before selecting an audience."
      />
      <Panel>
        <p>Unsaved changes are lost when you leave or refresh.</p>
        {associations.loading && <p role="status">Loading associations...</p>}
        {associations.error && (
          <div>
            <p role="alert">{associations.error}</p>
            <Button onClick={associations.reload}>Retry</Button>
          </div>
        )}
        {error && <p role="alert">{error}</p>}
        {success && <p role="status">{success}</p>}
        {(code === "feedback_version_conflict" ||
          code === "uncertain_mutation") && (
          <Button
            onClick={() =>
              initial ? window.location.reload() : navigate("/admin/feedback")
            }
          >
            Reload saved form
          </Button>
        )}
        <form
          ref={controls}
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <fieldset disabled={saving} className="feedback-editor-fields">
            <TextField
              label="Form title"
              value={data.title}
              onChange={(e) => change({ title: e.target.value })}
            />
            <TextField
              label="Description"
              multiline
              minRows={3}
              value={data.description}
              onChange={(e) => change({ description: e.target.value })}
            />
            <TextField
              select
              label="Association type"
              value={data.association?.kind ?? "none"}
              slotProps={{
                select: { native: true },
                inputLabel: { shrink: true },
              }}
              onChange={(e) =>
                change({
                  association:
                    e.target.value === "none"
                      ? null
                      : {
                          kind: e.target.value as "feature" | "lesson",
                          id: "",
                        },
                })
              }
            >
              <option value="none">None</option>
              <option value="feature">Feature</option>
              <option value="lesson">Lesson</option>
            </TextField>
            {data.association?.kind === "feature" && (
              <TextField
                select
                label="Feature"
                value={data.association.id}
                slotProps={{
                  select: { native: true },
                  inputLabel: { shrink: true },
                }}
                onChange={(e) =>
                  change({
                    association: { kind: "feature", id: e.target.value },
                  })
                }
              >
                <option value="">Choose a feature</option>
                {associations.data?.features.map((f) => (
                  <option value={f.id} key={f.id}>
                    {f.label}
                  </option>
                ))}
              </TextField>
            )}
            {data.association?.kind === "lesson" && (
              <TextField
                select
                label="Lesson"
                value={data.association.id}
                slotProps={{
                  select: { native: true },
                  inputLabel: { shrink: true },
                }}
                onChange={(e) =>
                  change({
                    association: { kind: "lesson", id: e.target.value },
                  })
                }
              >
                <option value="">Choose a lesson</option>
                {associations.data?.lessons.map((f) => (
                  <option value={f.id} key={f.id}>
                    {f.title}
                  </option>
                ))}
              </TextField>
            )}
            {associations.data?.truncated && (
              <p>
                More associations exist. Use a feature association or leave this
                form unassociated.
              </p>
            )}
            <Questions
              questions={data.questions}
              change={(questions) => change({ questions })}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={
                code === "feedback_version_conflict" ||
                code === "uncertain_mutation"
              }
            >
              {saving ? "Saving draft..." : "Save draft"}
            </Button>
            {saving && <p role="status">Saving draft...</p>}
          </fieldset>
        </form>
      </Panel>
      <Dialog
        open={blocker.state === "blocked"}
        onClose={() => blocker.state === "blocked" && blocker.reset()}
        aria-labelledby="feedback-discard-title"
      >
        <DialogTitle id="feedback-discard-title">
          Discard unsaved changes?
        </DialogTitle>
        <DialogContent>Your unsaved form edits will be lost.</DialogContent>
        <DialogActions>
          <Button
            onClick={() => blocker.state === "blocked" && blocker.reset()}
          >
            Keep editing
          </Button>
          <Button
            onClick={() => blocker.state === "blocked" && blocker.proceed()}
          >
            Discard changes
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

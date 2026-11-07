import {
  Checkbox,
  FormControlLabel,
  Radio,
  RadioGroup,
  TextField,
} from "@mui/material";
import { type Answer, type Question } from "../services/feedbackApi";

export default function FeedbackQuestion({
  question: q,
  index,
  value,
  disabled,
  marked,
  change,
}: {
  question: Question;
  index: number;
  value: Answer["value"];
  disabled: boolean;
  marked: boolean;
  change: (value: Answer["value"]) => void;
}) {
  const promptId = `feedback-q-${q.id}-prompt`;
  const errorId = `feedback-q-${q.id}-error`;
  const labelled = {
    "aria-labelledby": promptId,
    "aria-describedby": marked ? errorId : undefined,
    "aria-invalid": marked ? true : undefined,
  } as const;
  const groupClass = marked ? "feedback-control-invalid" : undefined;
  return (
    <fieldset
      className="feedback-question"
      data-feedback-question=""
      data-invalid={marked ? "" : undefined}
      aria-labelledby={promptId}
      disabled={disabled}
    >
      <div className="feedback-question-head">
        <span className="feedback-question-prompt" id={promptId}>
          {index + 1}. {q.prompt}
        </span>
        <span className="feedback-question-tag">
          {q.required ? "Required" : "Optional"}
        </span>
      </div>
      {(q.type === "short_answer" || q.type === "paragraph") && (
        <TextField
          value={typeof value === "string" ? value : ""}
          onChange={(e) => change(e.target.value)}
          multiline={q.type === "paragraph"}
          minRows={q.type === "paragraph" ? 4 : undefined}
          slotProps={{
            htmlInput: {
              maxLength: q.type === "paragraph" ? 5000 : 500,
              ...labelled,
            },
          }}
          disabled={disabled}
        />
      )}
      {q.type === "dropdown" && (
        <TextField
          select
          value={typeof value === "string" ? value : ""}
          onChange={(e) => change(e.target.value || null)}
          slotProps={{
            select: { native: true },
            htmlInput: labelled,
          }}
          disabled={disabled}
        >
          <option value="">Choose an option</option>
          {q.options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </TextField>
      )}
      {q.type === "multiple_choice" && (
        <RadioGroup
          {...labelled}
          className={groupClass}
          value={value ?? ""}
          onChange={(e) => change(e.target.value)}
        >
          {q.options.map((o) => (
            <FormControlLabel
              key={o.id}
              value={o.id}
              control={<Radio disabled={disabled} />}
              label={o.label}
            />
          ))}
        </RadioGroup>
      )}
      {q.type === "checkbox" && (
        <div role="group" className={groupClass} {...labelled}>
          {q.options.map((o) => (
            <FormControlLabel
              key={o.id}
              label={o.label}
              control={
                <Checkbox
                  disabled={disabled}
                  checked={Array.isArray(value) && value.includes(o.id)}
                  onChange={(e) =>
                    change(
                      e.target.checked
                        ? [...(Array.isArray(value) ? value : []), o.id]
                        : (Array.isArray(value) ? value : []).filter(
                            (id) => id !== o.id,
                          ),
                    )
                  }
                />
              }
            />
          ))}
        </div>
      )}
      {q.type === "linear_scale" && q.scale && (
        <div className="feedback-scale">
          <span className="feedback-scale-min">{q.scale.min_label}</span>
          <RadioGroup
            {...labelled}
            className={groupClass}
            value={value ?? ""}
            onChange={(e) => change(Number(e.target.value))}
            row
          >
            {Array.from(
              { length: q.scale.max - q.scale.min + 1 },
              (_, i) => i + q.scale!.min,
            ).map((n) => (
              <FormControlLabel
                key={n}
                value={n}
                control={<Radio disabled={disabled} />}
                label={String(n)}
              />
            ))}
          </RadioGroup>
          <span className="feedback-scale-max">{q.scale.max_label}</span>
        </div>
      )}
      {marked && (
        <p className="feedback-question-error" id={errorId}>
          This question is required.
        </p>
      )}
    </fieldset>
  );
}

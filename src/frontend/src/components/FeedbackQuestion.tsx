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
  change,
}: {
  question: Question;
  index: number;
  value: Answer["value"];
  disabled: boolean;
  change: (value: Answer["value"]) => void;
}) {
  const label = `${index + 1}. ${q.prompt}`;
  return (
    <fieldset className="feedback-question" disabled={disabled}>
      <legend>{label}</legend>
      <p className="muted">{q.required ? "Required" : "Optional"}</p>
      {(q.type === "short_answer" || q.type === "paragraph") && (
        <TextField
          label={label}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => change(e.target.value)}
          multiline={q.type === "paragraph"}
          minRows={q.type === "paragraph" ? 4 : undefined}
          slotProps={{
            htmlInput: { maxLength: q.type === "paragraph" ? 5000 : 500 },
          }}
          disabled={disabled}
        />
      )}
      {q.type === "dropdown" && (
        <TextField
          select
          label={label}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => change(e.target.value || null)}
          slotProps={{ select: { native: true } }}
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
          aria-label={label}
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
        <div role="group" aria-label={label}>
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
        <>
          <p>
            {q.scale.min_label} {q.scale.max_label && `— ${q.scale.max_label}`}
          </p>
          <RadioGroup
            aria-label={label}
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
        </>
      )}
    </fieldset>
  );
}

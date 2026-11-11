import { useRef, useState, type FormEvent } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
} from "@mui/material";
import {
  RANGES,
  customPeriodErrors,
  type PeriodChoice,
  type Range,
} from "../../lib/period";
import type { PeriodErrors } from "../../services/featureAnalytics";

/** Compact "Reporting period" select plus the "Custom range" dialog. Picking a period never sends a request itself. */
export default function PeriodSelector({
  choice,
  today,
  onRange,
  onCustom,
}: {
  choice: PeriodChoice;
  today: string;
  onRange: (range: Range) => void;
  onCustom: (from: string, to: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [errors, setErrors] = useState<PeriodErrors>({});
  const fromInput = useRef<HTMLInputElement>(null);
  const toInput = useRef<HTMLInputElement>(null);

  function show() {
    setFrom(choice.kind === "custom" ? choice.from : "");
    setTo(choice.kind === "custom" ? choice.to : "");
    setErrors({});
    setOpen(true);
  }

  function apply(event: FormEvent) {
    event.preventDefault();
    const trimmed = { from: from.trim(), to: to.trim() };
    const problems = customPeriodErrors(trimmed.from, trimmed.to, today);
    setErrors(problems);
    if (problems.from || problems.to) {
      (problems.from ? fromInput : toInput).current?.focus();
      return;
    }
    setOpen(false);
    if (
      choice.kind !== "custom" ||
      choice.from !== trimmed.from ||
      choice.to !== trimmed.to
    )
      onCustom(trimmed.from, trimmed.to);
  }

  const value = choice.kind === "range" ? choice.range : "applied";
  return (
    <>
      <TextField
        select
        id="analytics-hub-period"
        label="Reporting period"
        size="small"
        value={value}
        slotProps={{ select: { native: true } }}
        onChange={(event) => {
          const next = event.target.value;
          if (next === "custom") show();
          else if (next !== "applied" && next !== value) onRange(next as Range);
        }}
      >
        {RANGES.map((r) => (
          <option key={r.id} value={r.id}>
            {r.label}
          </option>
        ))}
        {choice.kind === "custom" && (
          <option value="applied">{`${choice.from} to ${choice.to}`}</option>
        )}
        <option value="custom">Custom range</option>
      </TextField>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        aria-labelledby="analytics-hub-custom-title"
      >
        <form onSubmit={apply} noValidate>
          <DialogTitle id="analytics-hub-custom-title">
            Custom range
          </DialogTitle>
          <DialogContent className="analytics-hub-custom">
            <DialogContentText>
              Dates are UTC. Maximum 366 days. The end date cannot be in the
              future.
            </DialogContentText>
            <TextField
              id="analytics-hub-from"
              label="From date"
              value={from}
              placeholder="YYYY-MM-DD"
              error={!!errors.from}
              helperText={errors.from}
              inputRef={fromInput}
              onChange={(event) => setFrom(event.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              id="analytics-hub-to"
              label="To date"
              value={to}
              placeholder="YYYY-MM-DD"
              error={!!errors.to}
              helperText={errors.to}
              inputRef={toInput}
              onChange={(event) => setTo(event.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              Apply period
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
}

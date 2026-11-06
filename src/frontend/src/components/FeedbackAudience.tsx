import { useEffect, useRef, useState } from "react";
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
import { useFeedbackRead } from "../hooks/useFeedbackRead";
import {
  adminBase,
  feedbackCode,
  feedbackError,
  feedbackWrite,
  uncertain,
  type Audience,
  type Form,
} from "../services/feedbackApi";

export default function FeedbackAudience({
  form,
  close,
  published,
  reload,
}: {
  form: Form;
  close: () => void;
  published: (form: Form) => void;
  reload: () => void;
}) {
  const [role, setRole] = useState<"student" | "teacher">("student");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Map<string, Audience>>(new Map());
  const [review, setReview] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [reconcile, setReconcile] = useState(false);
  const read = useFeedbackRead(
    `${adminBase}/${form.id}/audience?role=${role}&search=${encodeURIComponent(query)}&limit=20&offset=${offset}`,
    "audience",
  );
  const alive = useRef(true);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      controller.current?.abort();
    };
  }, []);
  async function publish() {
    if (pending || reconcile || !review || !selected.size) return;
    setPending(true);
    setError("");
    const operation = new AbortController();
    controller.current = operation;
    try {
      const result = await feedbackWrite(
        "POST",
        `${adminBase}/${form.id}/publish`,
        "form",
        {
          version: form.version,
          audience_role: role,
          recipient_ids: [...selected.keys()],
        },
        operation.signal,
      );
      if (alive.current) published(result);
    } catch (failure) {
      if (!alive.current) return;
      setError(feedbackError(failure));
      if (
        uncertain(failure) ||
        ["feedback_version_conflict", "feedback_state_conflict"].includes(
          feedbackCode(failure),
        )
      )
        setReconcile(true);
      if (feedbackCode(failure) === "feedback_audience_changed") {
        setReview(false);
        setSelected(new Map());
        read.reload();
      }
    } finally {
      if (alive.current) setPending(false);
    }
  }
  return (
    <Dialog
      open
      onClose={pending ? undefined : close}
      aria-labelledby="feedback-audience-title"
      fullWidth
      maxWidth="sm"
    >
      <DialogTitle id="feedback-audience-title">Review audience</DialogTitle>
      <DialogContent>
        {error && <p role="alert">{error}</p>}
        {reconcile && <Button onClick={reload}>Reload saved form</Button>}
        {pending && <p role="status">Publishing form...</p>}
        {review ? (
          <>
            <h2>
              {role === "student" ? "Selected students" : "Selected teachers"}
            </h2>
            <p>{selected.size} recipients</p>
            <ul>
              {[...selected.values()].map((person) => (
                <li key={person.id}>
                  {person.display_name} ({person.id})
                </li>
              ))}
            </ul>
          </>
        ) : (
          <>
            <TextField
              select
              label="Audience role"
              value={role}
              slotProps={{ select: { native: true } }}
              onChange={(e) => {
                setRole(e.target.value as "student" | "teacher");
                setSelected(new Map());
                setOffset(0);
                setError("");
              }}
            >
              <option value="student">Students</option>
              <option value="teacher">Teachers</option>
            </TextField>
            <TextField
              label="Search recipients"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Button
              onClick={() => {
                if (query === search.trim() && offset === 0) read.reload();
                else {
                  setQuery(search.trim());
                  setOffset(0);
                }
              }}
            >
              Search
            </Button>
            {read.loading && <p role="status">Loading audience...</p>}
            {read.error && (
              <div>
                <p role="alert">{read.error}</p>
                <Button onClick={read.reload}>Retry</Button>
              </div>
            )}
            {!read.loading && read.data && (
              <>
                {!read.data.items.length && (
                  <p>No eligible recipients found.</p>
                )}
                <div className="feedback-audience-options">
                  {read.data.items.map((person) => (
                    <FormControlLabel
                      key={person.id}
                      label={`${person.display_name} (${person.id})`}
                      control={
                        <Checkbox
                          checked={selected.has(person.id)}
                          onChange={(e) =>
                            setSelected((old) => {
                              const next = new Map(old);
                              if (e.target.checked) next.set(person.id, person);
                              else next.delete(person.id);
                              return next;
                            })
                          }
                        />
                      }
                    />
                  ))}
                </div>
                {offset > 0 && (
                  <Button onClick={() => setOffset(Math.max(0, offset - 20))}>
                    Previous page
                  </Button>
                )}
                {read.data.next_offset !== null && (
                  <Button onClick={() => setOffset(read.data!.next_offset!)}>
                    Next page
                  </Button>
                )}
              </>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={close} disabled={pending}>
          Cancel
        </Button>
        {review ? (
          <>
            <Button onClick={() => setReview(false)} disabled={pending}>
              Back to selection
            </Button>
            <Button
              variant="contained"
              onClick={() => void publish()}
              disabled={pending || reconcile}
            >
              Publish form
            </Button>
          </>
        ) : (
          <Button
            onClick={() => {
              if (selected.size > 500)
                setError(
                  "Select 1 to 500 different recipients from one audience role.",
                );
              else setReview(true);
            }}
            disabled={!selected.size}
          >
            Review selected recipients
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

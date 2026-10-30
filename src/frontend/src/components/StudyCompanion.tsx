import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type Dispatch,
  type SetStateAction,
} from "react";
import { useLocation } from "react-router";
import {
  Button,
  Fab,
  IconButton,
  Paper,
  TextField,
  Tooltip,
} from "@mui/material";
import { MessageCircle, RotateCcw, Send, Sparkles, X } from "lucide-react";
import { lessons, navigation } from "../data";
import { usePractice } from "../practice/PracticeContext";
import { ApiError } from "../services/client";
import { sendCompanionMessage } from "../services/companion";

type Message = {
  from: "you" | "companion";
  text: string;
  failed?: boolean;
};
const HISTORY_ITEMS = 4;

// Fixed wording per failure; the raw server body is never shown.
function failureMessage(error: unknown): string {
  const e = error instanceof ApiError ? error : null;
  const wait = e?.retryAfterSeconds;
  if (e?.status === 429 && e.code === "rate_limited")
    return wait
      ? `You have sent a lot of messages. Please wait ${wait} seconds and try again.`
      : "You have sent a lot of messages. Please wait a little and try again.";
  if (e?.status === 429)
    return wait
      ? `The study companion is busy. Please try again in ${wait} seconds.`
      : "The study companion is busy. Please try again shortly.";
  if (e?.status === 401)
    return "The study companion could not tell who you are. Please sign in again.";
  if (e?.status === 404)
    return "I could not find this practice page or attempt. Reload the page and try again.";
  if (e?.status === 422)
    return "That message could not be sent. Shorten it or clear the chat, then try again.";
  if (e?.status === 502)
    return "The study companion could not answer that. Please try again.";
  if (e?.status === 503)
    return "The study companion is unavailable right now. Please try again later.";
  return "I could not reach the study companion. Check your connection and try again.";
}
type CompanionState = {
  open: boolean;
  setOpen: Dispatch<SetStateAction<boolean>>;
};
const Context = createContext<CompanionState | null>(null);

// Mounted once per student demo session; leaving that role or returning to login
// unmounts the provider and widget, discarding their temporary conversation.
export function CompanionProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <Context.Provider value={{ open, setOpen }}>{children}</Context.Provider>
  );
}
export function useCompanion() {
  const value = useContext(Context);
  if (!value) throw new Error("CompanionProvider is required");
  return value;
}
export function CompanionTrigger({
  children,
  className,
  onOpen,
}: {
  children: ReactNode;
  className?: string;
  onOpen?: () => void;
}) {
  const { setOpen } = useCompanion();
  return (
    <Button
      className={className}
      onClick={() => {
        onOpen?.();
        setOpen(true);
      }}
    >
      {children}
    </Button>
  );
}

export default function StudyCompanion() {
  const { open, setOpen } = useCompanion();
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Bumped by "Clear chat" so a reply that arrives later is ignored.
  const generation = useRef(0);
  const { submitted, submittedAttemptId, setId } = usePractice();
  const location = useLocation();
  const path = location.pathname.split("/");
  const lesson =
    path[2] === "materials" && path[3]
      ? lessons.find((item) => item.id === path[3])
      : undefined;
  const page =
    lesson?.title ||
    navigation.student.find((item) => item.path === path[2])?.label ||
    (path[2] === "feedback" ? "Feedback form" : "Student overview");
  const launcher = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const previousOpen = useRef(open);
  useEffect(() => {
    if (open) input.current?.focus();
    else if (previousOpen.current) launcher.current?.focus();
    previousOpen.current = open;
  }, [open]);
  useEffect(() => {
    if (open) end.current?.scrollIntoView({ block: "nearest" });
  }, [messages, open]);
  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
      }
    };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [open, setOpen]);
  const onPractice = path[2] === "practice";
  const send = async () => {
    const text = draft.trim();
    if (!text || pending) return;
    const history = messages
      .filter((m) => !m.failed)
      .slice(-HISTORY_ITEMS)
      .map((m) => ({
        role: m.from === "you" ? ("user" as const) : ("assistant" as const),
        text: m.text,
      }));
    const run = ++generation.current;
    setError(null);
    setPending(true);
    setMessages((items) => [
      ...items.filter((m) => !(m.failed && m.text === text)),
      { from: "you", text },
    ]);
    setDraft("");
    try {
      const result = await sendCompanionMessage({
        message: text,
        history,
        context: {
          page: onPractice ? "practice" : "other",
          set_id: onPractice ? setId : null,
          attempt_id: onPractice ? submittedAttemptId : null,
          label: page.slice(0, 80),
        },
      });
      if (run !== generation.current) return;
      setMessages((items) => [
        ...items,
        { from: "companion", text: result.reply },
      ]);
    } catch (caught) {
      if (run !== generation.current) return;
      setMessages((items) =>
        items.map((m, i) =>
          i === items.length - 1 ? { ...m, failed: true } : m,
        ),
      );
      setDraft((current) => current || text);
      setError(failureMessage(caught));
    } finally {
      if (run === generation.current) {
        setPending(false);
        input.current?.focus();
      }
    }
  };
  return (
    <div className="companion-widget">
      {open && (
        <Paper
          component="section"
          variant="outlined"
          role="dialog"
          aria-modal="false"
          aria-labelledby="companion-title"
          className="companion-window"
        >
          <header className="companion-window-header">
            <span className="icon-box purple">
              <Sparkles size={21} />
            </span>
            <div>
              <h2 id="companion-title">Your study companion</h2>
              <small>A nudge in the right direction.</small>
            </div>
            <Tooltip title="Clear chat and start fresh">
              <IconButton
                aria-label="Clear chat"
                size="small"
                onClick={() => {
                  generation.current++;
                  setPending(false);
                  setError(null);
                  setMessages([]);
                  setDraft("");
                  input.current?.focus();
                }}
              >
                <RotateCcw size={17} />
              </IconButton>
            </Tooltip>
            <Tooltip title="Minimise">
              <IconButton
                aria-label="Minimise study companion"
                size="small"
                onClick={() => setOpen(false)}
              >
                <X size={19} />
              </IconButton>
            </Tooltip>
          </header>
          <div className="companion-page" aria-live="polite">
            Current page: {page}
          </div>
          <div
            className="companion-history"
            role="log"
            aria-label="Conversation"
            aria-live="polite"
          >
            <div className="widget-welcome">
              <span className="icon-box purple">
                <MessageCircle size={22} />
              </span>
              <h3>What are you curious about today?</h3>
              <p>
                Tell me what you understand and where you’re getting stuck.
                We’ll take it one thought at a time.
              </p>
              <small>
                {submitted
                  ? "Practice submitted · Ask about your attempt from the Practice page"
                  : "Hints only before whole-set submission"}
              </small>
            </div>
            {messages.map((message, index) => (
              <div key={index} className={`chat-message ${message.from}`}>
                <span>
                  {message.from === "you" ? "You" : "Study companion"}
                </span>
                <p>{message.text}</p>
              </div>
            ))}
            {pending && (
              <div className="chat-message companion" role="status">
                <span>Study companion</span>
                <p>Thinking...</p>
              </div>
            )}
            <div ref={end} />
          </div>
          {error && (
            <p role="alert" className="companion-error">
              {error}
            </p>
          )}
          <form
            className="companion-compose"
            onSubmit={(event) => {
              event.preventDefault();
              send();
            }}
          >
            <TextField
              inputRef={input}
              label="Message your study companion"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              inputProps={{ maxLength: 1000 }}
            />
            <Button
              variant="contained"
              type="submit"
              aria-label="Send question"
              disabled={!draft.trim() || pending}
            >
              <Send size={18} />
            </Button>
          </form>
          <p className="companion-disclaimer">
            AI study companion · Replies can be wrong · Messages reset on reload
          </p>
        </Paper>
      )}
      {!open && (
        <Tooltip title="Your study companion">
          <Fab
            ref={launcher}
            color="primary"
            aria-label="Open study companion"
            aria-expanded={false}
            onClick={() => setOpen(true)}
          >
            <MessageCircle size={25} />
          </Fab>
        </Tooltip>
      )}
    </div>
  );
}

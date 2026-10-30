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

type Message = { from: "you" | "companion"; text: string };
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
  const { submitted } = usePractice();
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
  const send = () => {
    if (!draft.trim()) return;
    setMessages((items) => [
      ...items,
      { from: "you", text: draft.trim() },
      {
        from: "companion",
        text: `Preview only · You’re viewing ${page}. ${submitted ? "After submission, the full app will help explain the answers and your reasoning." : "Before whole-set submission, the full app will offer guiding questions and hints, never reveal or confirm answers."} No AI request was made.`,
      },
    ]);
    setDraft("");
    input.current?.focus();
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
                  ? "Practice submitted · Explanations available in the full app"
                  : "Hints only before whole-set submission"}
              </small>
            </div>
            {messages.map((message, index) => (
              <div key={index} className={`chat-message ${message.from}`}>
                <span>
                  {message.from === "you" ? "You" : "Study companion · Preview"}
                </span>
                <p>{message.text}</p>
              </div>
            ))}
            <div ref={end} />
          </div>
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
              inputProps={{ maxLength: 2000 }}
            />
            <Button
              variant="contained"
              type="submit"
              aria-label="Send question"
              disabled={!draft.trim()}
            >
              <Send size={18} />
            </Button>
          </form>
          <p className="companion-disclaimer">
            UI preview · No AI connected · Messages reset on reload
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

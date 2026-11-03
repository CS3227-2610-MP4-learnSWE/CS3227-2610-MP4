import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router";
import { Alert, Button, Tab, Tabs, TextField } from "@mui/material";
import {
  ArrowRight,
  Check,
  Code2,
  GraduationCap,
  Sparkles,
  Quote,
} from "lucide-react";
import { Brand, ThemeToggle } from "../components/ui";
import { type Role } from "../data";
import { useAuth } from "../auth/AuthContext";
import { demoAccessEnabled } from "../auth/demoAccess";
import { homePath } from "../auth/RequireRole";
import { ApiError } from "../services/client";

const copy = {
  student: {
    title: "Your next chapter starts here.",
    subtitle: "A little curiosity. A little practice. A lot of possibility.",
  },
  teacher: {
    title: "Make room for your best teaching.",
    subtitle: "Less time preparing. More moments of understanding.",
  },
  admin: {
    title: "Better learning starts with listening.",
    subtitle: "Turn thoughtful feedback into meaningful improvements.",
  },
};
type Mode = "signin" | "signup";

// Fixed wording per failure; the raw server body is never shown.
function failureMessage(error: unknown, mode: Mode): string {
  const e = error instanceof ApiError ? error : null;
  if (e?.status === 429)
    return e.retryAfterSeconds
      ? `Too many attempts. Please wait ${e.retryAfterSeconds} seconds and try again.`
      : "Too many attempts. Please wait a little and try again.";
  if (e?.status === 401)
    return "Email or password is incorrect. Check them and try again, or create an account.";
  if (e?.status === 422)
    return mode === "signup"
      ? "Check your details: use a valid email, a display name, and a password of 10 to 128 characters that is not a common password."
      : "Enter your email and password.";
  if (e?.status === 503)
    return "Sign-in is unavailable right now. Please try again later.";
  return "We could not reach the server. Check your connection and try again.";
}

export default function Login({
  dark,
  toggle,
}: {
  dark: boolean;
  toggle: () => void;
}) {
  const { user, login, signup } = useAuth();
  // The demo tabs only pick which demo shortcut to show; a real sign-in takes its role from the server.
  const [role, setRole] = useState<Role>("student");
  const [mode, setMode] = useState<Mode>("signin");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accepted, setAccepted] = useState(false);
  if (user) return <Navigate to={homePath(user.role)} replace />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    setAccepted(false);
    try {
      if (mode === "signin") {
        await login(email, password);
      } else {
        await signup(displayName, email, password);
        setMode("signin");
        setPassword("");
        setAccepted(true);
      }
    } catch (caught) {
      setError(failureMessage(caught, mode));
    } finally {
      setPending(false);
    }
  };
  return (
    <div className="login-page">
      <header className="login-header">
        <Brand />
        <div className="login-header-right">
          <span className="demo-pill">
            <span /> Demo · Sample data
          </span>
          <ThemeToggle dark={dark} toggle={toggle} />
        </div>
      </header>
      <main className="login-main">
        <section className="login-story">
          <div className="eyebrow">
            <span className="little-line" /> A SPACE TO LEARN. A SPACE TO GROW.
          </div>
          <h1>{copy[role].title}</h1>
          <p className="login-subtitle">{copy[role].subtitle}</p>
          <div className="login-illustration" aria-hidden="true">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="floating-label label-top">
              <span className="icon-box green">
                <Check size={17} />
              </span>
              One step closer.
              <span className="mini-dot" />
            </div>
            <div className="illustration-card">
              <div className="illustration-top">
                <span className="icon-box blue">
                  <Code2 size={22} />
                </span>
                <span>
                  Learning, made meaningful
                  <small>SOFTWARE ENGINEERING ESSENTIALS</small>
                </span>
                <span className="ellipsis">•••</span>
              </div>
              <div className="illustration-code">
                <span>
                  <i>01</i>
                  <b>def</b> build_something_great():
                </span>
                <span>
                  <i>02</i> curiosity = <em>True</em>
                </span>
                <span>
                  <i>03</i> <b>while</b> curiosity:
                </span>
                <span>
                  <i>04</i> learn<span className="syntax-blue">()</span>
                </span>
                <span>
                  <i>05</i> grow<span className="syntax-blue">()</span>
                </span>
              </div>
              <div className="illustration-footer">
                <span className="avatar-stack">
                  <b>A</b>
                  <b>J</b>
                  <b>M</b>
                </span>
                <span>Better, together.</span>
                <span className="tiny-bars">
                  <i />
                  <i />
                  <i />
                  <i />
                </span>
              </div>
            </div>
            <div className="floating-label label-bottom">
              <span className="icon-box purple">
                <Sparkles size={18} />
              </span>
              <div>
                A nudge in the right direction
                <small>Your AI study companion</small>
              </div>
            </div>
            <span className="decoration-star star-one">✦</span>
            <span className="decoration-star star-two">✧</span>
          </div>
          <div className="login-quote">
            <Quote size={18} />
            <p>
              “The beautiful thing about learning is that nobody can take it
              away from you.”<span>— B. B. King</span>
            </p>
          </div>
        </section>
        <section className="login-form-wrap">
          <div className="login-form">
            <span className="login-welcome-icon">
              <GraduationCap size={28} />
            </span>
            <h2>Welcome to learnSWE</h2>
            <p>Your space to keep moving forward.</p>
            <Tabs
              value={mode}
              onChange={(_, value: Mode) => {
                setMode(value);
                setError(null);
                setAccepted(false);
              }}
              variant="fullWidth"
              aria-label="Account"
              className="role-tabs"
            >
              <Tab value="signin" label="Sign in" />
              <Tab value="signup" label="Create account" />
            </Tabs>
            {accepted && (
              <Alert severity="success" role="status" sx={{ mt: 2 }}>
                Thanks. If this email can be used, your student account is
                ready. Sign in to continue.
              </Alert>
            )}
            {error && (
              <Alert severity="error" role="alert" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}
            <form onSubmit={submit} noValidate>
              {mode === "signup" && (
                <TextField
                  label="Display name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  autoComplete="name"
                  required
                />
              )}
              <TextField
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                required
              />
              <TextField
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={
                  mode === "signin" ? "current-password" : "new-password"
                }
                helperText={
                  mode === "signup"
                    ? "10 to 128 characters. Avoid common passwords and your email."
                    : undefined
                }
                required
              />
              <Button
                fullWidth
                variant="contained"
                type="submit"
                disabled={pending}
                endIcon={<ArrowRight size={17} />}
              >
                {mode === "signin" ? "Sign in" : "Create account"}
              </Button>
              {mode === "signup" && (
                <small>Accounts created here are student accounts.</small>
              )}
            </form>
            {demoAccessEnabled() && (
              <>
                <div className="login-divider">
                  <span>JUST TAKING A LOOK?</span>
                </div>
                <h3 className="demo-shortcut-heading">
                  Demo shortcut (development): sample data, not signed in, no
                  real account
                </h3>
                <Tabs
                  value={role}
                  onChange={(_, value: Role) => setRole(value)}
                  variant="fullWidth"
                  aria-label="Choose a demo role"
                  className="role-tabs"
                >
                  <Tab value="student" label="Student" />
                  <Tab value="teacher" label="Teacher" />
                  <Tab value="admin" label="Admin" />
                </Tabs>
                <Button
                  component={Link}
                  to={`/${role}/overview`}
                  fullWidth
                  variant="outlined"
                  endIcon={<ArrowRight size={16} />}
                >
                  Explore {role} demo
                </Button>
                <p className="login-disclaimer">
                  No account needed. Demo screens show sample data and use no
                  session. Live practice and the study companion need a real
                  sign-in.
                </p>
              </>
            )}
          </div>
        </section>
      </main>
      <footer className="login-footer">
        <span>Made for curious minds.</span>
        <span>Learn thoughtfully. Build confidently.</span>
      </footer>
    </div>
  );
}

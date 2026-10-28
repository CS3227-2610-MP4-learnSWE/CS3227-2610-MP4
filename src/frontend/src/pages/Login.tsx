import { useState } from "react";
import { Link } from "react-router";
import { Button, Tab, Tabs, TextField } from "@mui/material";
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

const copy = {
  student: {
    title: "Your next chapter starts here.",
    subtitle: "A little curiosity. A little practice. A lot of possibility.",
    label: "Learn at your own pace",
  },
  teacher: {
    title: "Make room for your best teaching.",
    subtitle: "Less time preparing. More moments of understanding.",
    label: "Teach with intention",
  },
  admin: {
    title: "Better learning starts with listening.",
    subtitle: "Turn thoughtful feedback into meaningful improvements.",
    label: "See the bigger picture",
  },
};
export default function Login({
  dark,
  toggle,
  notify,
}: {
  dark: boolean;
  toggle: () => void;
  notify: (message?: string) => void;
}) {
  const [role, setRole] = useState<Role>("student");
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
              value={role}
              onChange={(_, value: Role) => setRole(value)}
              variant="fullWidth"
              aria-label="Choose your role"
              className="role-tabs"
            >
              <Tab value="student" label="Student" />
              <Tab value="teacher" label="Teacher" />
              <Tab value="admin" label="Admin" />
            </Tabs>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                notify();
              }}
              noValidate
              autoComplete="off"
            >
              <TextField
                label="Email address"
                placeholder="you@example.com"
                type="email"
                autoComplete="off"
              />
              <TextField
                label="Password"
                placeholder="Enter your password"
                type="password"
                autoComplete="off"
              />
              <div className="form-caption">
                <span>
                  <span className="caption-dot" /> {copy[role].label}
                </span>
                <span>Preview only</span>
              </div>
              <Button
                fullWidth
                variant="contained"
                type="submit"
                endIcon={<ArrowRight size={17} />}
              >
                Sign in
              </Button>
            </form>
            <div className="create-account">
              <span>New around here?</span>
              <Button onClick={() => notify()}>Create account</Button>
            </div>
            <div className="login-divider">
              <span>JUST TAKING A LOOK?</span>
            </div>
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
              No account needed. Sign-in and registration are visual previews.
            </p>
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

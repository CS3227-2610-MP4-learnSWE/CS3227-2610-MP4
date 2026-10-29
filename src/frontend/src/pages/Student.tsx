import { useEffect, useState } from "react";
import { Link, Navigate, useLocation } from "react-router";
import {
  Alert,
  Button,
  FormControlLabel,
  Radio,
  RadioGroup,
  TextField,
} from "@mui/material";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock3,
  Flame,
  Lightbulb,
  Sparkles,
  Target,
} from "lucide-react";
import {
  ArrowBadge,
  CourseArt,
  EmptyState,
  PageHeading,
  Panel,
  PreviewNote,
  PrimaryLink,
  Progress,
  SectionHeading,
  Stat,
  Tag,
} from "../components/ui";
import { lessons, questions, weeklyActivity } from "../data";
import { useDemo } from "../state";
import { useCompanion } from "../components/StudyCompanion";

function Overview() {
  const { completed } = useDemo();
  const { setOpen } = useCompanion();
  return (
    <>
      <PageHeading
        eyebrow="YOUR LEARNING JOURNEY"
        title="A little progress, every day."
        description="Welcome back, Alex. Let’s make room for something new."
        action={
          <span className="streak">
            <Flame size={16} /> 4-day learning streak
          </span>
        }
      />
      <div className="student-hero">
        <div className="hero-copy">
          <span className="hero-kicker">
            <span /> YOUR NEXT CHAPTER
          </span>
          <h2>
            Good code starts
            <br />
            with clear thinking.
          </h2>
          <p>
            Pick up where you left off. A few thoughtful
            <br className="desktop-break" /> minutes today can make all the
            difference.
          </p>
          <PrimaryLink to="/student/materials/clean-code">
            Continue learning
          </PrimaryLink>
          <span className="hero-meta">
            <Clock3 size={14} />
            12 min lesson<span>•</span>Clean code
          </span>
        </div>
        <div className="hero-art">
          <CourseArt large />
          <div className="hero-art-label">
            <span className="icon-box green">
              <Check size={16} />
            </span>
            Clarity is a superpower.
          </div>
        </div>
      </div>
      <div className="stats-grid">
        <Stat
          label="Lessons completed"
          value={`${2 + completed.length} / 8`}
          detail={`${2 + completed.length} of 8 lessons`}
          icon="book"
        />
        <Stat
          label="Practice average"
          value="82%"
          detail="↑ 8% from last week · Sample"
          icon="code"
          tone="purple"
        />
        <Stat
          label="Time well spent"
          value="2.4 hrs"
          detail="Learning this week · Sample"
          icon="usage"
          tone="green"
        />
      </div>
      <div className="dashboard-columns">
        <div>
          <SectionHeading
            title="Keep your curiosity going"
            link="All materials"
            to="/student/materials"
          />
          <div className="lesson-cards">
            {lessons.slice(0, 2).map((lesson) => (
              <LessonCard key={lesson.id} lesson={lesson} />
            ))}
          </div>
        </div>
        <div>
          <SectionHeading title="Your learning rhythm" />
          <Panel className="rhythm-panel">
            <div className="rhythm-top">
              <span>This week</span>
              <Tag tone="green">Looking good</Tag>
            </div>
            <div
              className="bar-chart"
              role="img"
              aria-label="Sample learning activity over seven days"
            >
              {weeklyActivity.map((height, i) => (
                <div key={i}>
                  <div
                    className={`chart-bar ${i === 5 ? "highlight" : ""}`}
                    style={{ height: `${height}%` }}
                  />
                  <span>{["M", "T", "W", "T", "F", "S", "S"][i]}</span>
                </div>
              ))}
            </div>
            <p className="rhythm-note">
              <span className="dot green-dot" /> Showing up is the hardest part.
              You’re doing it.
            </p>
            <small className="muted">Illustrative activity · Sample data</small>
          </Panel>
        </div>
      </div>
      <div className="companion-strip">
        <span className="icon-box purple">
          <Sparkles size={23} />
        </span>
        <div>
          <h3>A question is a great place to start.</h3>
          <p>Get a thoughtful hint from your AI study companion.</p>
        </div>
        <Button
          onClick={() => setOpen(true)}
          endIcon={<ArrowRight size={16} />}
        >
          Let’s think it through
        </Button>
      </div>
    </>
  );
}
function LessonCard({ lesson }: { lesson: (typeof lessons)[number] }) {
  const { completed } = useDemo();
  const done = completed.includes(lesson.id);
  return (
    <Link to={`/student/materials/${lesson.id}`} className="lesson-card">
      <CourseArt tone={lesson.tone} />
      <div className="lesson-card-body">
        <div className="lesson-meta">
          <span>{lesson.topic}</span>
          <span>
            <Clock3 size={12} />
            {lesson.duration}
          </span>
        </div>
        <h3>{lesson.title}</h3>
        <p>{lesson.description}</p>
        <div className="lesson-card-bottom">
          <span>
            {done ? (
              <>
                <CheckCircle2 size={14} /> Complete
              </>
            ) : lesson.progress ? (
              "Continue lesson"
            ) : (
              "Start learning"
            )}
          </span>
          <ArrowBadge />
        </div>
      </div>
    </Link>
  );
}
function Materials() {
  const [filter, setFilter] = useState("All topics");
  const [search, setSearch] = useState("");
  const visible = lessons.filter(
    (lesson) =>
      (filter === "All topics" || filter === lesson.topic) &&
      `${lesson.title} ${lesson.topic}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <PageHeading
        eyebrow="A LIBRARY FOR YOUR CURIOSITY"
        title="Small lessons. Lasting understanding."
        description="Explore the ideas behind better software, one topic at a time."
      />
      <div className="toolbar">
        <div className="filter-buttons">
          {[
            "All topics",
            "Clean code",
            "Software testing",
            "Version control",
          ].map((topic) => (
            <Button
              key={topic}
              onClick={() => setFilter(topic)}
              variant={topic === filter ? "contained" : "text"}
              size="small"
            >
              {topic}
            </Button>
          ))}
        </div>
        <TextField
          label="Search materials"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ maxWidth: 240 }}
        />
      </div>
      <div className="material-grid">
        {visible.map((lesson) => (
          <LessonCard lesson={lesson} key={lesson.id} />
        ))}
      </div>
      {visible.length === 0 && (
        <EmptyState title="Nothing here just yet">
          Try another topic or a different search.
        </EmptyState>
      )}
      <PreviewNote>
        Published sample materials · Completion changes last until refresh.
      </PreviewNote>
    </>
  );
}
function Lesson({ id }: { id: string }) {
  const lesson = lessons.find((item) => item.id === id);
  const { setOpen } = useCompanion();
  const { completed, toggleCompleted } = useDemo();
  if (!lesson)
    return (
      <EmptyState title="Lesson not found">
        <Link to="/student/materials">Return to materials</Link>
      </EmptyState>
    );
  return (
    <>
      <Link className="back-link" to="/student/materials">
        <ArrowLeft size={16} /> All study materials
      </Link>
      <PageHeading
        eyebrow={`${lesson.topic.toUpperCase()} · LESSON ${lesson.chapter}`}
        title={lesson.title}
        description={`${lesson.duration} read · Software engineering essentials`}
        action={
          <Button
            variant={completed.includes(id) ? "outlined" : "contained"}
            startIcon={<Check size={17} />}
            onClick={() => toggleCompleted(id)}
          >
            {completed.includes(id) ? "Mark as incomplete" : "Mark as complete"}
          </Button>
        }
      />
      <div className="reader-layout">
        <Panel className="lesson-reader">
          <Tag>STUDY NOTES · SAMPLE</Tag>
          <h2>
            {id === "clean-code"
              ? "Let your code tell a clear story."
              : id === "testing"
                ? "Confidence comes from a useful safety net."
                : "Build together, thoughtfully."}
          </h2>
          <p>
            Software is read more often than it is written. A thoughtful
            approach makes it easier for you and your teammates to understand
            what happens, why it happens, and what can safely change.
          </p>
          <h3 id="one-clear-idea">01 / Start with one clear idea</h3>
          <p>
            {id === "clean-code"
              ? "A function should have a single, focused responsibility. Choose a name that describes its intention rather than its implementation. If you need “and” to explain what a function does, consider splitting it."
              : id === "testing"
                ? "A useful test captures an important behaviour. Start with a concrete example, exercise the real behaviour, and check an independently determined outcome."
                : "Keep commits focused on a single meaningful change. Write a clear message so a teammate can understand the intention without reconstructing your entire workflow."}
          </p>
          <pre className="code-block">
            <code>
              {id === "clean-code"
                ? "def calculate_total(prices):\n    return sum(prices)\n\n# One name. One clear intention."
                : id === "testing"
                  ? "def test_total_of_two_prices():\n    assert calculate_total([4, 6]) == 10"
                  : 'git switch -c improve-lesson\ngit add lesson.md\ngit commit -m "Clarify lesson example"'}
            </code>
          </pre>
          <h3 id="easy-to-change">02 / Make it easy to change</h3>
          <p>
            Small, focused changes are easier to review and reason about. Look
            for clear boundaries and avoid adding flexibility before you need
            it. A simpler design usually gives you fewer things to keep in your
            head.
          </p>
          <div className="callout">
            <Lightbulb size={22} />
            <div>
              <strong>A moment to reflect</strong>
              <p>
                Think about a piece of code you found hard to understand. What
                is one small change that could make its intention clearer?
              </p>
            </div>
          </div>
          <h3 id="put-it-into-practice">
            03 / Put understanding into practice
          </h3>
          <p>
            Reading is a starting point. Try a practice set, explain your
            reasoning, and use hints to bridge the gaps. Getting stuck is part
            of learning.
          </p>
          <PrimaryLink to="/student/practice">Try the practice set</PrimaryLink>
        </Panel>
        <aside>
          <Panel className="reader-outline">
            <span className="eyebrow">IN THIS LESSON</span>
            <a href="#one-clear-idea">One clear idea</a>
            <a href="#easy-to-change">Easy to change</a>
            <a href="#put-it-into-practice">Put it into practice</a>
            <hr />
            <p>Need another perspective?</p>
            <Button
              onClick={() => setOpen(true)}
              startIcon={<Sparkles size={16} />}
            >
              Ask your companion
            </Button>
          </Panel>
        </aside>
      </div>
    </>
  );
}
export function Practice() {
  const { answers, answer, submitted, submit, resetPractice } = useDemo();
  const [error, setError] = useState(false);
  const [hint, setHint] = useState(false);
  const count = questions.filter((q) => answers[q.id]?.trim()).length;
  const score = questions.filter(
    (q) => answers[q.id]?.trim() === q.answer,
  ).length;
  return (
    <>
      <PageHeading
        eyebrow="UNDERSTAND IT. THEN TRY IT."
        title="Put your knowledge to work."
        description="A few focused questions to turn understanding into confidence."
      />
      <div className="practice-layout">
        <div>
          <Panel className="practice-intro">
            <div>
              <Tag tone="purple">SOFTWARE ENGINEERING ESSENTIALS</Tag>
              <h2>Clear code, confident changes</h2>
              <p>3 MCQs · About 5 minutes · Whole-set submission</p>
            </div>
            <span className="icon-box purple">
              <Target size={25} />
            </span>
          </Panel>
          {error && (
            <Alert severity="warning" sx={{ my: 2 }}>
              Answer all 3 questions before submitting the whole set.
            </Alert>
          )}
          {submitted && (
            <Alert severity="success" sx={{ my: 2 }}>
              <h2 className="result-title">
                {score} / 3 —{" "}
                {score === 3
                  ? "Nicely done!"
                  : "Keep building your understanding."}
              </h2>
              Your whole set is submitted. Review your answers and explanations
              below.
            </Alert>
          )}
          {questions.map((q, i) => (
            <Panel key={q.id} className="question-panel">
              <div className="question-number">
                QUESTION {String(i + 1).padStart(2, "0")}
                <span>Choose one</span>
              </div>
              <h3>{q.text}</h3>
              {q.code && (
                <pre className="code-block">
                  <code>{q.code}</code>
                </pre>
              )}
              {
                <RadioGroup
                  aria-label={q.text}
                  value={answers[q.id] || ""}
                  onChange={(e) => answer(q.id, e.target.value)}
                >
                  {q.options.map((option) => (
                    <FormControlLabel
                      className={`answer-option ${answers[q.id] === option ? "selected" : ""}`}
                      value={option}
                      key={option}
                      control={<Radio size="small" />}
                      label={option}
                      disabled={submitted}
                    />
                  ))}
                </RadioGroup>
              }
              {submitted && (
                <div className="solution">
                  <strong>Correct answer: {q.answer}</strong>
                  <p>{q.explanation}</p>
                </div>
              )}
            </Panel>
          ))}
          <div className="practice-submit">
            <p>
              <CheckCircle2 size={16} /> Answers are revealed after you submit
              the whole set.
            </p>
            <Button
              variant="contained"
              onClick={() => {
                if (submitted) {
                  resetPractice();
                  setHint(false);
                  setError(false);
                } else if (count < questions.length) setError(true);
                else {
                  submit();
                  setError(false);
                }
              }}
            >
              {submitted ? "Start another demo attempt" : "Submit practice set"}
            </Button>
          </div>
        </div>
        <aside className="practice-aside">
          <Panel className="practice-progress">
            <span className="eyebrow">YOUR PRACTICE SESSION</span>
            <h3>{submitted ? "A step forward." : "One thought at a time."}</h3>
            <Progress
              value={Math.round((count / 3) * 100)}
              label={`${count} of 3 answered`}
            />
            <p>Take your time. You can change any answer before submitting.</p>
          </Panel>
          <Panel className="hint-panel">
            <span className="icon-box purple">
              <Sparkles size={22} />
            </span>
            <h3>A nudge, not a shortcut.</h3>
            <p>
              {submitted
                ? "Your explanations are now available alongside each question."
                : "Your study companion can help you think through a concept without revealing the answer."}
            </p>
            {hint && (
              <div className="hint-text">
                {submitted
                  ? "Compare your reasoning with each explanation. What assumption would you change next time?"
                  : "Break the problem into smaller ideas. What is each question asking you to measure or protect? Trace the code one line at a time."}
              </div>
            )}
            <Button
              variant="outlined"
              fullWidth
              onClick={() => setHint(true)}
              startIcon={<Lightbulb size={16} />}
            >
              {submitted ? "Reflect on your answers" : "Get a hint"}
            </Button>
            <small>Scripted demo · No AI request</small>
          </Panel>
        </aside>
      </div>
      <PreviewNote>
        Demo scoring runs in your browser. Sample answer keys are not secure;
        production enforcement belongs in the backend.
      </PreviewNote>
    </>
  );
}
function LegacyAssistant() {
  const { setOpen } = useCompanion();
  useEffect(() => {
    setOpen(true);
  }, [setOpen]);
  return <Navigate to="/student/overview" replace />;
}
export default function Student() {
  const path = useLocation().pathname.split("/");
  switch (path[2]) {
    case "overview":
      return <Overview />;
    case "materials":
      return path[3] ? <Lesson id={path[3]} /> : <Materials />;
    case "practice":
      return <Practice />;
    case "assistant":
      return <LegacyAssistant />;
    default:
      return (
        <EmptyState title="This page isn’t here">
          <Link to="/student/overview">Back to your overview</Link>
        </EmptyState>
      );
  }
}

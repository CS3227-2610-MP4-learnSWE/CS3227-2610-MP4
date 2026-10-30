import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  FormControlLabel,
  Radio,
  RadioGroup,
} from "@mui/material";
import { CheckCircle2, Lightbulb, Sparkles, Target } from "lucide-react";
import {
  PageHeading,
  Panel,
  PreviewNote,
  Progress,
  Tag,
} from "../components/ui";
import { usePractice } from "../practice/PracticeContext";

export default function Practice() {
  const p = usePractice();
  const { load, loadSet, set, choices, results, submitted } = p;
  const [hint, setHint] = useState(false);
  useEffect(() => {
    if (load === "idle") loadSet();
  }, [load, loadSet]);

  const heading = (
    <PageHeading
      eyebrow="UNDERSTAND IT. THEN TRY IT."
      title="Put your knowledge to work."
      description="A few focused questions to turn understanding into confidence."
    />
  );
  if (load === "error")
    return (
      <>
        {heading}
        <Alert
          severity="error"
          sx={{ my: 2 }}
          action={
            <Button color="inherit" size="small" onClick={loadSet}>
              Try again
            </Button>
          }
        >
          We could not load the practice set. Please try again.
        </Alert>
      </>
    );
  if (!set)
    return (
      <>
        {heading}
        <p role="status">Loading the practice set…</p>
      </>
    );

  const total = set.questions.length;
  const count = set.questions.filter((q) => choices[q.id]).length;
  const resultOf = (id: string) => results?.questions.find((r) => r.id === id);
  const submitting = p.phase === "submitting";
  const missingNumbers = p.missing
    .map((id) => set.questions.findIndex((q) => q.id === id) + 1)
    .filter((n) => n > 0);
  return (
    <>
      {heading}
      <div className="practice-layout">
        <div>
          <Panel className="practice-intro">
            <div>
              <Tag tone="purple">SOFTWARE ENGINEERING ESSENTIALS</Tag>
              <h2>{set.title}</h2>
              <p>{total} MCQs · Whole-set submission</p>
            </div>
            <span className="icon-box purple">
              <Target size={25} />
            </span>
          </Panel>
          {p.message === "incomplete" && (
            <Alert severity="warning" sx={{ my: 2 }}>
              Answer all {total} questions before submitting the whole set.
              {missingNumbers.length > 0 &&
                ` Still to answer: question ${missingNumbers.join(", ")}.`}
            </Alert>
          )}
          {p.message === "retry" && (
            <Alert
              severity="error"
              sx={{ my: 2 }}
              action={
                <Button color="inherit" size="small" onClick={p.submit}>
                  Try again
                </Button>
              }
            >
              We could not finish submitting just now.{" "}
              {p.locked
                ? "Your answers are saved; try again to finish."
                : "Your answers are kept."}
            </Alert>
          )}
          {results && (
            <Alert
              severity={
                results.score.correct === results.score.total
                  ? "success"
                  : "warning"
              }
              sx={{ my: 2 }}
            >
              <h2 className="result-title">
                {results.score.correct} / {results.score.total} —{" "}
                {results.score.correct === results.score.total
                  ? "Nicely done!"
                  : "Keep building your understanding."}
              </h2>
              Your whole set is submitted. Review your answers and explanations
              below.
            </Alert>
          )}
          {set.questions.map((q, i) => {
            const result = resultOf(q.id);
            const textOf = (id: string) =>
              q.choices.find((c) => c.id === id)?.text ?? "";
            const optionState = (id: string) => {
              if (!result) return choices[q.id] === id ? "selected" : "";
              if (id === result.correct_choice) return "correct";
              return id === result.selected ? "wrong" : "";
            };
            return (
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
                <RadioGroup
                  aria-label={q.text}
                  value={choices[q.id] || ""}
                  onChange={(e) => p.choose(q.id, e.target.value)}
                >
                  {q.choices.map((c) => (
                    <FormControlLabel
                      className={`answer-option ${optionState(c.id)}`}
                      value={c.id}
                      key={c.id}
                      control={<Radio size="small" />}
                      label={c.text}
                      disabled={submitted || submitting || p.locked}
                    />
                  ))}
                </RadioGroup>
                {result && (
                  <div className={`solution ${result.correct ? "" : "wrong"}`}>
                    <strong>
                      {result.correct ? "Correct" : "Not quite"} · Your answer:{" "}
                      {textOf(result.selected)}
                    </strong>
                    <p>Correct answer: {textOf(result.correct_choice)}</p>
                    <p>{result.explanation}</p>
                  </div>
                )}
              </Panel>
            );
          })}
          <div className="practice-submit">
            <p>
              <CheckCircle2 size={16} /> Answers are revealed after you submit
              the whole set.
            </p>
            <Button
              variant="contained"
              disabled={submitting}
              onClick={() => {
                if (submitted) {
                  p.startAnother();
                  setHint(false);
                } else p.submit();
              }}
            >
              {submitted ? "Start another attempt" : "Submit practice set"}
            </Button>
          </div>
        </div>
        <aside className="practice-aside">
          <Panel className="practice-progress">
            <span className="eyebrow">YOUR PRACTICE SESSION</span>
            <h3>{submitted ? "A step forward." : "One thought at a time."}</h3>
            <Progress
              value={Math.round((count / total) * 100)}
              label={`${count} of ${total} answered`}
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
        Questions, scoring and explanations come from the server. The hint panel
        is a scripted demo and makes no AI request.
      </PreviewNote>
    </>
  );
}

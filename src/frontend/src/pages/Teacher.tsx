import { useRef, useState } from "react";
import { Link, useLocation } from "react-router";
import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Tab,
  Tabs,
  TextField,
} from "@mui/material";
import {
  ArrowRight,
  Check,
  Clock3,
  FileText,
  Plus,
  Sparkles,
  Upload,
  WandSparkles,
} from "lucide-react";
import {
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
import { lessons } from "../data";
import { questions } from "../teacherDemo";

type Props = { notify: (message?: string) => void };
function Overview() {
  return (
    <>
      <PageHeading
        eyebrow="MAKE UNDERSTANDING POSSIBLE"
        title="Teaching, with a little more space."
        description="Welcome back, Jamie. Good teaching starts with your ideas."
        action={
          <PrimaryLink to="/teacher/generate">Open content studio</PrimaryLink>
        }
      />
      <div className="teacher-hero">
        <div>
          <Tag tone="purple">YOUR IDEAS, AMPLIFIED</Tag>
          <h2>
            Less preparation.
            <br />
            More lightbulb moments.
          </h2>
          <p>
            Bring your course materials. Shape thoughtful lessons
            <br className="desktop-break" /> and practice with a little help
            from AI.
          </p>
          <PrimaryLink to="/teacher/generate">
            Create something meaningful
          </PrimaryLink>
        </div>
        <div className="teacher-art">
          <CourseArt tone="purple" large />
          <span className="teacher-art-badge">
            <Sparkles size={19} /> Always reviewed by you.
          </span>
        </div>
      </div>
      <div className="stats-grid">
        <Stat
          label="Students learning"
          value="48"
          detail="Across your sample course"
          icon="people"
        />
        <Stat
          label="Materials published"
          value="8"
          detail="2 drafts ready for review"
          icon="book"
          tone="purple"
        />
        <Stat
          label="Practice completion"
          value="76%"
          detail="↑ 12% this week · Sample"
          icon="review"
          tone="green"
        />
      </div>
      <div className="dashboard-columns">
        <div>
          <SectionHeading
            title="A few things to pick up"
            link="View drafts"
            to="/teacher/review"
          />
          <Panel className="task-list">
            {[
              {
                title: "Clean code essentials",
                detail: "Study notes · Draft ready for your review",
                path: "review",
              },
              {
                title: "Testing with confidence",
                detail: "3 MCQs · Awaiting review",
                path: "review",
              },
              {
                title: "Your teaching experience",
                detail: "A new feedback request from the team",
                path: "inbox",
              },
            ].map((task, i) => (
              <Link key={task.title} to={`/teacher/${task.path}`}>
                <span className={`icon-box ${i === 1 ? "purple" : "blue"}`}>
                  <FileText size={20} />
                </span>
                <div>
                  <strong>{task.title}</strong>
                  <small>{task.detail}</small>
                </div>
                <ArrowRight size={17} />
              </Link>
            ))}
          </Panel>
        </div>
        <div>
          <SectionHeading title="Where a little help matters" />
          <Panel className="topic-progress">
            <Tag tone="green">LEARNING PULSE · SAMPLE</Tag>
            <h3>Understanding takes practice.</h3>
            <p>These topics could use another explanation.</p>
            <Progress value={58} label="Writing focused functions" />
            <Progress value={72} label="Thinking in test cases" />
            <Progress value={86} label="Version control basics" />
          </Panel>
        </div>
      </div>
    </>
  );
}
function Materials({ notify }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [filename, setFilename] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const visible = lessons.filter((l) =>
    `${l.title} ${l.topic}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <PageHeading
        eyebrow="THE STARTING POINT FOR GREAT LESSONS"
        title="Your materials, all together."
        description="A thoughtful home for the ideas you want to share."
        action={
          <Button
            variant="contained"
            startIcon={<Upload size={17} />}
            onClick={() => setOpen(true)}
          >
            Upload material
          </Button>
        }
      />
      <Panel className="library-panel">
        <div className="library-toolbar">
          <h2>
            Course materials <span className="count-badge">3</span>
          </h2>
          <TextField
            label="Search your materials"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ maxWidth: 280 }}
          />
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Material</th>
                <th>Topic</th>
                <th>Status</th>
                <th>Updated</th>
                <th>
                  <span className="sr-only">Action</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((lesson) => (
                <tr key={lesson.id}>
                  <td>
                    <span className={`file-icon ${lesson.tone}`}>
                      <FileText size={20} />
                    </span>
                    <div>
                      <strong>{lesson.title}</strong>
                      <small>Course notes · Sample PDF</small>
                    </div>
                  </td>
                  <td>{lesson.topic}</td>
                  <td>
                    <Tag
                      tone={
                        lesson.sourceStatus === "Published" ? "green" : "amber"
                      }
                    >
                      {lesson.sourceStatus}
                    </Tag>
                  </td>
                  <td>{lesson.updated}</td>
                  <td>
                    <Button component={Link} to="/teacher/review" size="small">
                      Review
                      <ArrowRight size={14} />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!visible.length && (
          <EmptyState title="No matching materials">
            Try a different title or topic.
          </EmptyState>
        )}
      </Panel>
      <PreviewNote>
        Sample library · Uploads are a visual preview. No files leave your
        browser.
      </PreviewNote>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Upload material · Preview</DialogTitle>
        <DialogContent>
          <p className="muted">
            Choose a file to preview the upload interface. It will not be read,
            uploaded or saved.
          </p>
          <Button
            onClick={() => fileInput.current?.click()}
            variant="outlined"
            startIcon={<Upload size={18} />}
            fullWidth
          >
            Choose a file
            <input
              type="file"
              ref={fileInput}
              hidden
              onChange={(e) => setFilename(e.target.files?.[0]?.name || "")}
            />
          </Button>
          {filename && <p>{filename}</p>}
          <TextField
            sx={{ mt: 3 }}
            label="Course"
            value="Software engineering essentials"
            slotProps={{ input: { readOnly: true } }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            onClick={() =>
              notify("Upload preview only. No file was uploaded or saved.")
            }
            variant="contained"
          >
            Preview upload
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
function Generate() {
  const [type, setType] = useState("Study notes");
  const [source, setSource] = useState("Clean code essentials");
  const [preview, setPreview] = useState(false);
  return (
    <>
      <PageHeading
        eyebrow="A HEAD START, NOT A REPLACEMENT"
        title="Your ideas. A little momentum."
        description="Turn source materials into a starting point you can make your own."
      />
      <div className="studio-layout">
        <Panel className="studio-controls">
          <span className="icon-box purple">
            <WandSparkles size={23} />
          </span>
          <h2>Content studio</h2>
          <p>Choose the material. Set the direction.</p>
          <TextField
            select
            label="Source material"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            {[
              "Clean code essentials",
              "Software testing notes",
              "Version control guide",
            ].map((item) => (
              <MenuItem key={item} value={item}>
                {item}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Create a draft of"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            {["Study notes", "Practice questions"].map((item) => (
              <MenuItem key={item} value={item}>
                {item}
              </MenuItem>
            ))}
          </TextField>
          <div className="callout small">
            <Check size={18} />
            <p>
              You stay in control. Every draft needs your review before
              publication.
            </p>
          </div>
          <Button
            fullWidth
            variant="contained"
            startIcon={<Sparkles size={17} />}
            onClick={() => setPreview(true)}
          >
            Preview generation
          </Button>
          <PreviewNote>Displays a fixed sample. No AI request.</PreviewNote>
        </Panel>
        <Panel className="draft-preview">
          {preview ? (
            <>
              <div className="draft-top">
                <Tag tone="purple">Sample draft · No AI request was made</Tag>
                <span className="muted">{type}</span>
              </div>
              <h2>
                {type === "Study notes"
                  ? "Writing code with clear intentions"
                  : "A little practice in clear thinking"}
              </h2>
              <p className="muted">
                Source selection: {source} · Fixed illustrative output
              </p>
              {type === "Study notes" ? (
                <>
                  <h3>Start with a single responsibility</h3>
                  <p>
                    A focused function does one thing well. This makes its
                    purpose easier to explain, test and change.
                  </p>
                  <pre className="code-block">
                    {"def calculate_total(prices):\n    return sum(prices)"}
                  </pre>
                  <h3>Choose names that explain why</h3>
                  <p>
                    Prefer clear intention over clever abbreviation. A useful
                    name lets a reader understand the idea without tracing every
                    implementation detail.
                  </p>
                  <div className="callout">
                    <Sparkles size={20} />
                    <p>
                      Reflection: Which function in your last project could
                      benefit from a clearer name?
                    </p>
                  </div>
                </>
              ) : (
                questions.map((q, i) => (
                  <div className="draft-question" key={q.id}>
                    <h3>
                      {i + 1}. {q.text}
                    </h3>
                    <ul aria-label="Answer choices">
                      {q.options.map((option) => (
                        <li key={option}>{option}</li>
                      ))}
                    </ul>
                    <p>Correct choice: {q.answer}</p>
                    <p className="muted">{q.explanation}</p>
                  </div>
                ))
              )}
              <Button
                component={Link}
                to="/teacher/review"
                endIcon={<ArrowRight size={16} />}
              >
                Review sample content
              </Button>
            </>
          ) : (
            <div className="empty-state studio-empty">
              <div className="studio-empty-art">
                <Sparkles size={38} />
                <span>✦</span>
              </div>
              <h2>A little inspiration lives here.</h2>
              <p>
                Your generated draft will appear here.
                <br />
                For now, explore a sample to see how it feels.
              </p>
              <Tag tone="purple">Always a draft. Always your decision.</Tag>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
function Review({ notify }: Props) {
  const [tab, setTab] = useState(0);
  const [notes, setNotes] = useState(
    "A focused function has one clear responsibility. Give it a name that communicates intention, keep its inputs explicit, and make the result easy to test.",
  );
  const [drafts, setDrafts] = useState(
    questions.map((q) => ({
      text: q.text,
      answer: q.answer,
      explanation: q.explanation,
    })),
  );
  const update = (
    i: number,
    key: "text" | "answer" | "explanation",
    value: string,
  ) =>
    setDrafts((items) =>
      items.map((item, index) =>
        index === i ? { ...item, [key]: value } : item,
      ),
    );
  return (
    <>
      <PageHeading
        eyebrow="YOUR EXPERTISE MAKES THE DIFFERENCE"
        title="A thoughtful final look."
        description="Review every note, question and explanation before sharing it."
        action={
          <Button
            variant="contained"
            startIcon={<Check size={17} />}
            onClick={() =>
              notify(
                "Publication preview only. Nothing was published or saved.",
              )
            }
          >
            Preview publication
          </Button>
        }
      />
      <Panel className="review-panel">
        <div className="review-title">
          <div>
            <Tag tone="amber">DRAFT · SAMPLE CONTENT</Tag>
            <h2>Clean code essentials</h2>
            <p className="muted">
              Software engineering essentials · Prepared for your review
            </p>
          </div>
          <span className="icon-box blue">
            <FileText size={26} />
          </span>
        </div>
        <Tabs
          value={tab}
          onChange={(_, value: number) => setTab(value)}
          aria-label="Review content type"
        >
          <Tab label="Study notes" />
          <Tab label="Practice questions & answers" />
        </Tabs>
        <div className="review-editor">
          {tab === 0 ? (
            <TextField
              label="Study notes draft"
              multiline
              minRows={10}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          ) : (
            drafts.map((q, i) => (
              <div className="editable-question" key={i}>
                <span className="eyebrow">QUESTION {i + 1}</span>
                <TextField
                  label={`Question ${i + 1}`}
                  value={q.text}
                  onChange={(e) => update(i, "text", e.target.value)}
                />
                <ul aria-label={`Choices for question ${i + 1}`}>
                  {questions[i].options.map((option) => (
                    <li key={option}>{option}</li>
                  ))}
                </ul>
                <TextField
                  select
                  label={`Answer key ${i + 1}`}
                  value={q.answer}
                  onChange={(e) => update(i, "answer", e.target.value)}
                >
                  {questions[i].options.map((option) => (
                    <MenuItem key={option} value={option}>
                      {option}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  label={`Explanation ${i + 1}`}
                  multiline
                  minRows={2}
                  value={q.explanation}
                  onChange={(e) => update(i, "explanation", e.target.value)}
                />
              </div>
            ))
          )}
        </div>
        <PreviewNote>
          Edits stay in this screen only. Preview publication does not save or
          share them.
        </PreviewNote>
      </Panel>
      <div className="callout small">
        <Clock3 size={20} />
        <p>
          In the planned app, students see published questions first. Answer
          keys and solution explanations are released only after whole-set
          submission.
        </p>
      </div>
    </>
  );
}
function PracticeSets({ notify }: Props) {
  const [selected, setSelected] = useState<string[]>([
    "responsibility",
    "regression",
  ]);
  const [title, setTitle] = useState("Clear code, confident changes");
  return (
    <>
      <PageHeading
        eyebrow="A BRIDGE FROM KNOWING TO DOING"
        title="Practice with a purpose."
        description="Bring the right questions together for a focused learning moment."
      />
      <div className="studio-layout">
        <Panel className="studio-controls">
          <h2>Build a practice set</h2>
          <TextField
            label="Set title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <TextField label="Topic" defaultValue="Clean code" />
          <p>{selected.length} questions selected</p>
          <Button
            variant="contained"
            startIcon={<Plus size={16} />}
            onClick={() =>
              notify(
                "Practice-set preview only. No set was saved or published.",
              )
            }
          >
            Preview practice set
          </Button>
          <PreviewNote>Selection and text changes are local.</PreviewNote>
        </Panel>
        <div>
          {questions.map((q) => (
            <Panel key={q.id} className="question-panel">
              <FormControlLabel
                control={
                  <Checkbox
                    checked={selected.includes(q.id)}
                    onChange={() =>
                      setSelected((items) =>
                        items.includes(q.id)
                          ? items.filter((id) => id !== q.id)
                          : [...items, q.id],
                      )
                    }
                  />
                }
                label={<strong>{q.text}</strong>}
              />
              <p className="muted">Answer: {q.answer}</p>
              <p className="muted">{q.explanation}</p>
            </Panel>
          ))}
        </div>
      </div>
    </>
  );
}
export default function Teacher({ notify }: Props) {
  const section = useLocation().pathname.split("/")[2];
  switch (section) {
    case "overview":
      return <Overview />;
    case "materials":
      return <Materials notify={notify} />;
    case "generate":
      return <Generate />;
    case "review":
      return <Review notify={notify} />;
    case "practice":
      return <PracticeSets notify={notify} />;
    default:
      return (
        <EmptyState title="This page isn’t here">
          <Link to="/teacher/overview">Back to your overview</Link>
        </EmptyState>
      );
  }
}

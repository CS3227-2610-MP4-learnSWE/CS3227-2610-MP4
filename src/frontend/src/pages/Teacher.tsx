import { useEffect, useRef, useState } from "react";
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
import { questions } from "../teacherDemo";
import { ApiError } from "../services/client";
import TeacherContentStudio from "./TeacherContentStudio";
import {
  listTeacherCourses,
  listTeacherTopics,
  listTeacherMaterials,
  uploadTeacherMaterial,
  setTeacherMaterialTopic,
  downloadTeacherMaterial,
  type Course,
  type Topic,
  type Material,
} from "../services/teacherMaterials";

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
  const [courses, setCourses] = useState<Course[]>([]);
  const [courseId, setCourseId] = useState("");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topicFilter, setTopicFilter] = useState("");
  const [materials, setMaterials] = useState<Material[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [uploadTopic, setUploadTopic] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const demoEnabled =
    import.meta.env.VITE_APP_ENV === "development" &&
    import.meta.env.VITE_ALLOW_DEMO_IDENTITY === "true";

  const [courseReload, setCourseReload] = useState(0);
  const [dataReload, setDataReload] = useState(0);
  const loadCourses = () => setCourseReload((value) => value + 1);
  const refresh = () => setDataReload((value) => value + 1);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    listTeacherCourses()
      .then((items) => {
        if (!active) return;
        setCourses(items);
        setCourseId(items[0]?.id || "");
        if (!items.length) setLoading(false);
      })
      .catch(() => {
        if (active) {
          setError("Could not load courses. Please try again.");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [courseReload]);
  useEffect(() => {
    if (!courseId) return;
    let active = true;
    setLoading(true);
    setError("");
    setMaterials([]);
    // A course/filter/retry change supersedes both responses. A late response
    // cannot overwrite the selected course, even after a mutation completes.
    Promise.all([
      listTeacherTopics(courseId),
      listTeacherMaterials(courseId, topicFilter || undefined),
    ])
      .then(([nextTopics, nextMaterials]) => {
        if (!active) return;
        setTopics(nextTopics);
        setMaterials(nextMaterials);
      })
      .catch(() => {
        if (active)
          setError("Could not load topics or materials. Please retry.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [courseId, topicFilter, dataReload]);
  const visible = materials.filter((item) =>
    `${item.title} ${item.original_filename}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  const closeUpload = () => {
    setOpen(false);
    setTitle("");
    setFile(null);
    setUploadTopic("");
    setUploadError("");
    if (fileInput.current) fileInput.current.value = "";
  };
  const submit = async () => {
    if (!file || !title.trim()) {
      setUploadError(
        "Add a title and choose a PDF or UTF-8 text file (maximum 10 MiB).",
      );
      return;
    }
    if (file.size > 10 * 1024 * 1024 || !/\.(pdf|txt)$/i.test(file.name)) {
      setUploadError("Choose a PDF or UTF-8 text file no larger than 10 MiB.");
      return;
    }
    setBusy(true);
    setUploadError("");
    try {
      await uploadTeacherMaterial(courseId, {
        file,
        title,
        topicId: uploadTopic || undefined,
      });
      closeUpload();
      notify("Material uploaded. It has not been published to students.");
      refresh();
    } catch (reason) {
      setUploadError(
        reason instanceof ApiError && reason.code === "storage_quota_exceeded"
          ? "Upload would exceed the 100 MiB total storage limit."
          : "Upload failed. Check that the file is a readable PDF or UTF-8 text file within 10 MiB, then retry.",
      );
    } finally {
      setBusy(false);
    }
  };
  const changeTopic = async (item: Material, value: string) => {
    try {
      await setTeacherMaterialTopic(item.id, value || null);
      refresh();
    } catch {
      setError("Could not change the topic. Please retry.");
    }
  };
  const download = async (item: Material) => {
    try {
      const blob = await downloadTeacherMaterial(item.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = item.original_filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not download this material. Please retry.");
    }
  };
  return (
    <>
      <PageHeading
        eyebrow="THE STARTING POINT FOR GREAT LESSONS"
        title="Your materials, all together."
        description="Private source files for your teaching. Uploading does not publish a lesson."
        action={
          <Button
            variant="contained"
            startIcon={<Upload size={17} />}
            onClick={() => setOpen(true)}
            disabled={!courseId}
          >
            Upload material
          </Button>
        }
      />
      <PreviewNote>
        Development identity:{" "}
        {demoEnabled
          ? import.meta.env.VITE_DEMO_USER_ID || "demo-teacher"
          : "disabled (configure local .env)"}
        . Local testing only; this is not a real login.
      </PreviewNote>
      <Panel className="library-panel">
        <div className="library-toolbar">
          <h2>
            Course materials{" "}
            <span className="count-badge">{materials.length}</span>
          </h2>
          <TextField
            select
            label="Course"
            value={courseId}
            onChange={(e) => {
              setCourseId(e.target.value);
              setTopicFilter("");
              setUploadTopic("");
              setTopics([]);
              setMaterials([]);
              setLoading(true);
            }}
            sx={{ maxWidth: 240 }}
          >
            {courses.map((course) => (
              <MenuItem key={course.id} value={course.id}>
                {course.title}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Topic filter"
            value={topicFilter}
            onChange={(e) => setTopicFilter(e.target.value)}
            sx={{ maxWidth: 220 }}
          >
            <MenuItem value="">All topics</MenuItem>
            {topics.map((topic) => (
              <MenuItem key={topic.id} value={topic.id}>
                {topic.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Search your materials"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ maxWidth: 280 }}
          />
        </div>
        {loading && (
          <p className="library-status" role="status">
            Loading materials…
          </p>
        )}
        {error && (
          <div className="library-status" role="alert">
            <span>{error}</span>{" "}
            <Button onClick={courses.length ? refresh : loadCourses}>
              Retry
            </Button>
            {!courseId && (
              <small>Upload becomes available after a course loads.</small>
            )}
          </div>
        )}
        {!loading && !error && !courses.length && (
          <EmptyState title="No courses yet">
            You do not manage a course.
          </EmptyState>
        )}
        {!loading && !error && courses.length > 0 && (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Material</th>
                  <th>Topic</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <span className="file-icon blue">
                        <FileText size={20} />
                      </span>
                      <div>
                        <strong>{item.title}</strong>
                        <small>{item.original_filename}</small>
                      </div>
                    </td>
                    <td>
                      <TextField
                        select
                        label={`Change topic for ${item.title}`}
                        value={item.topic_id || ""}
                        onChange={(e) => changeTopic(item, e.target.value)}
                        sx={{ minWidth: 170 }}
                      >
                        <MenuItem value="">Unassigned</MenuItem>
                        {topics.map((topic) => (
                          <MenuItem key={topic.id} value={topic.id}>
                            {topic.name}
                          </MenuItem>
                        ))}
                      </TextField>
                    </td>
                    <td>{new Date(item.updated_at).toLocaleDateString()}</td>
                    <td>
                      <Button size="small" onClick={() => download(item)}>
                        Download
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!loading && !error && courses.length > 0 && !visible.length && (
          <EmptyState title="No matching materials">
            Upload a file or change the topic or search.
          </EmptyState>
        )}
      </Panel>
      <Dialog
        open={open}
        onClose={() => !busy && closeUpload()}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Upload material</DialogTitle>
        <DialogContent>
          <p className="muted">
            PDF or UTF-8 text · Up to 10 MiB per file · 100 MiB total upload
            storage.
          </p>
          <p className="muted">Source files remain private and unpublished.</p>
          <TextField
            label="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            sx={{ mt: 1 }}
          />
          <TextField
            select
            label="Topic optional"
            value={uploadTopic}
            onChange={(e) => setUploadTopic(e.target.value)}
            sx={{ mt: 2 }}
          >
            <MenuItem value="">Unassigned</MenuItem>
            {topics.map((topic) => (
              <MenuItem key={topic.id} value={topic.id}>
                {topic.name}
              </MenuItem>
            ))}
          </TextField>
          <Button
            onClick={() => fileInput.current?.click()}
            variant="outlined"
            sx={{ mt: 2 }}
            fullWidth
          >
            Choose a file
          </Button>
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.txt,application/pdf,text/plain"
            aria-label="Choose a file"
            style={{ position: "absolute", width: 1, height: 1, opacity: 0 }}
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          {file && <p>{file.name}</p>}
          {uploadError && <p role="alert">{uploadError}</p>}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeUpload} disabled={busy}>
            Cancel
          </Button>
          <Button variant="contained" onClick={submit} disabled={busy}>
            {busy ? "Uploading…" : "Upload"}
          </Button>
        </DialogActions>
      </Dialog>
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
      return <TeacherContentStudio />;
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

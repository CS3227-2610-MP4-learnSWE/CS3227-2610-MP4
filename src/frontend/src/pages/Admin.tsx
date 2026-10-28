import { useState } from "react";
import { Link, useLocation } from "react-router";
import {
  Avatar,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  TextField,
} from "@mui/material";
import {
  ArrowRight,
  BarChart3,
  FileText,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
} from "lucide-react";
import {
  EmptyState,
  PageHeading,
  Panel,
  PreviewNote,
  PrimaryLink,
  SectionHeading,
  Stat,
  Tag,
} from "../components/ui";
import { feedback, weeklyActivity } from "../data";

type Props = { notify: (message?: string) => void };
function Overview() {
  const [period, setPeriod] = useState("This week");
  return (
    <>
      <PageHeading
        eyebrow="LISTEN. UNDERSTAND. MAKE IT BETTER."
        title="A clearer picture of learning."
        description="Welcome back, Morgan. Here’s what’s happening across learnSWE."
        action={
          <TextField
            select
            label="Reporting period"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            sx={{ width: 160 }}
          >
            {["This week", "Last week"].map((p) => (
              <MenuItem key={p} value={p}>
                {p}
              </MenuItem>
            ))}
          </TextField>
        }
      />
      <div className="stats-grid four">
        <Stat
          label="Active learners"
          value={period === "This week" ? "128" : "116"}
          detail="Illustrative active accounts"
          icon="people"
        />
        <Stat
          label="Practice sets completed"
          value={period === "This week" ? "246" : "212"}
          detail="Sample whole-set submissions"
          icon="code"
          tone="purple"
        />
        <Stat
          label="AI generation success"
          value="98.2%"
          detail="Successful / attempted · Sample"
          icon="sparkles"
          tone="green"
        />
        <Stat
          label="Feedback responses"
          value="32"
          detail="Across 3 sample forms"
          icon="forms"
          tone="amber"
        />
      </div>
      <div className="dashboard-columns">
        <Panel className="analytics-chart">
          <div className="section-heading">
            <div>
              <h2>A community showing up</h2>
              <p className="muted">
                Sample feature interactions · {period.toLowerCase()}
              </p>
            </div>
            <Tag>Illustrative data</Tag>
          </div>
          <div
            className="analytics-bars"
            role="img"
            aria-label={`Illustrative feature interaction chart for ${period.toLowerCase()}`}
          >
            {weeklyActivity.map((value, i) => (
              <div key={i}>
                <div className="bar-pair">
                  <i
                    style={{
                      height: `${value * (period === "This week" ? 1 : 0.8)}%`,
                    }}
                  />
                  <i style={{ height: `${value * 0.6}%` }} />
                </div>
                <span>
                  {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i]}
                </span>
              </div>
            ))}
          </div>
          <div className="chart-legend">
            <span>
              <i />
              Practice
            </span>
            <span>
              <i />
              AI companion
            </span>
          </div>
        </Panel>
        <Panel className="feedback-pulse">
          <span className="icon-box purple">
            <MessageSquare size={22} />
          </span>
          <h2>
            A small question.
            <br />A meaningful insight.
          </h2>
          <p>
            Make space for the voices behind the numbers. Invite your community
            to share what matters.
          </p>
          <PrimaryLink to="/admin/forms">Create feedback form</PrimaryLink>
          <div className="pulse-bottom">
            <span className="avatar-stack">
              <b>A</b>
              <b>J</b>
              <b>M</b>
            </span>
            <span>32 sample voices. Plenty to learn.</span>
          </div>
        </Panel>
      </div>
      <SectionHeading
        title="What your community is saying"
        link="Explore feedback"
        to="/admin/responses"
      />
      <div className="feedback-cards">
        {feedback.map((item) => (
          <Panel key={item.id} className="feedback-card">
            <div>
              <Tag tone={item.sentiment === "Positive" ? "green" : "purple"}>
                {item.tag}
              </Tag>
              <span>“</span>
            </div>
            <blockquote>{item.quote}</blockquote>
            <small>{item.author} · Sample response</small>
          </Panel>
        ))}
      </div>
      <PreviewNote>
        All metrics are illustrative. No analytics events are collected in this
        preview.
      </PreviewNote>
    </>
  );
}
function Forms() {
  const [title, setTitle] = useState("A better learning experience");
  const [audience, setAudience] = useState("Students");
  const [feature, setFeature] = useState("AI study companion");
  const [items, setItems] = useState([
    { text: "How useful has the experience been?", required: true },
    { text: "What would make it better?", required: false },
  ]);
  const [open, setOpen] = useState(false);
  return (
    <>
      <PageHeading
        eyebrow="GOOD QUESTIONS OPEN DOORS"
        title="Make space for feedback."
        description="Ask the right people about the moments that matter."
        action={
          <Button
            variant="contained"
            onClick={() => setOpen(true)}
            endIcon={<ArrowRight size={16} />}
          >
            Preview survey request
          </Button>
        }
      />
      <div className="studio-layout">
        <Panel className="studio-controls">
          <span className="icon-box blue">
            <FileText size={23} />
          </span>
          <h2>Form details</h2>
          <TextField
            label="Form title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <TextField
            select
            label="Audience"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
          >
            {["Students", "Teachers"].map((value) => (
              <MenuItem key={value} value={value}>
                {value}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Related feature"
            value={feature}
            onChange={(e) => setFeature(e.target.value)}
          >
            {[
              "AI study companion",
              "Practice sets",
              "Content studio",
              "General experience",
            ].map((value) => (
              <MenuItem key={value} value={value}>
                {value}
              </MenuItem>
            ))}
          </TextField>
          <PreviewNote>
            Preview only. No form is published or delivered.
          </PreviewNote>
        </Panel>
        <div>
          <Panel className="form-panel">
            <Tag>FORM PREVIEW</Tag>
            <h2>{title || "Untitled form"}</h2>
            <p className="muted">
              For {audience.toLowerCase()} · {feature}
            </p>
            {items.map((item, i) => (
              <div className="form-question" key={i}>
                <TextField
                  label={`Question ${i + 1}`}
                  value={item.text}
                  onChange={(e) =>
                    setItems((old) =>
                      old.map((q, index) =>
                        index === i ? { ...q, text: e.target.value } : q,
                      ),
                    )
                  }
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={item.required}
                      onChange={(e) =>
                        setItems((old) =>
                          old.map((q, index) =>
                            index === i
                              ? { ...q, required: e.target.checked }
                              : q,
                          ),
                        )
                      }
                    />
                  }
                  label="Required"
                />
              </div>
            ))}
            <Button
              startIcon={<Plus size={16} />}
              onClick={() =>
                setItems((old) => [...old, { text: "", required: false }])
              }
            >
              Add question
            </Button>
          </Panel>
        </div>
      </div>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Survey request preview</DialogTitle>
        <DialogContent>
          <Tag>{audience}</Tag>
          <h2>{title || "Untitled form"}</h2>
          <p>Would appear in recipients’ inboxes with a link to the form.</p>
          <p>
            {items.length} questions · Related feature: {feature}
          </p>
          <PreviewNote>Nothing will be published or sent.</PreviewNote>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Back to editing</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
function Responses() {
  const [filter, setFilter] = useState("All responses");
  const [analysis, setAnalysis] = useState(false);
  const [source, setSource] = useState<string | null>(null);
  const visible = feedback.filter(
    (item) => filter === "All responses" || item.sentiment === filter,
  );
  return (
    <>
      <PageHeading
        eyebrow="THE VOICES BEHIND THE NUMBERS"
        title="Listen a little closer."
        description="Explore feedback and find the ideas worth taking forward."
        action={
          <Button
            variant="contained"
            startIcon={<Sparkles size={17} />}
            onClick={() => setAnalysis(true)}
          >
            Preview AI analysis
          </Button>
        }
      />
      <div className="response-layout">
        <div>
          <div className="filter-buttons inbox-filters">
            {["All responses", "Positive", "Suggestion"].map((value) => (
              <Button
                key={value}
                size="small"
                variant={filter === value ? "contained" : "text"}
                onClick={() => setFilter(value)}
              >
                {value}
              </Button>
            ))}
          </div>
          {visible.map((item) => (
            <Panel className="response-card" key={item.id}>
              <div className="response-top">
                <Tag tone={item.sentiment === "Positive" ? "green" : "purple"}>
                  {item.tag}
                </Tag>
                <span>{item.id}</span>
              </div>
              <blockquote>“{item.quote}”</blockquote>
              <small>{item.author} · Sample response</small>
            </Panel>
          ))}
        </div>
        <Panel className="insight-panel">
          <span className="icon-box purple">
            <Sparkles size={24} />
          </span>
          <h2>A starting point for understanding.</h2>
          {analysis ? (
            <>
              <Tag tone="purple">Fixed sample · No AI request</Tag>
              <h3>Guidance is making a difference</h3>
              <p>Students value hints that encourage independent thinking.</p>
              <Button size="small" onClick={() => setSource("FB-024")}>
                Supporting response FB-024
                <ArrowRight size={14} />
              </Button>
              <h3>Clarity could go further</h3>
              <p>
                Feedback asks for source comparisons and clearer post-submission
                explanations.
              </p>
              <Button size="small" onClick={() => setSource("FB-025")}>
                Supporting response FB-025
                <ArrowRight size={14} />
              </Button>
              <Button size="small" onClick={() => setSource("FB-026")}>
                Supporting response FB-026
                <ArrowRight size={14} />
              </Button>
              <div className="callout small">
                <Sparkles size={18} />
                <p>
                  <strong>Suggested improvement</strong>
                  <br />
                  Explore a side-by-side source view. This is a suggestion, not
                  a user quote.
                </p>
              </div>
            </>
          ) : (
            <p>
              Preview a sample summary, recurring themes and suggestions. Your
              judgement stays at the centre.
            </p>
          )}
          <PreviewNote>
            No changes or messages are triggered by this analysis.
          </PreviewNote>
        </Panel>
      </div>
      <Dialog
        open={!!source}
        onClose={() => setSource(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Supporting feedback · {source}</DialogTitle>
        <DialogContent>
          <blockquote>
            {feedback.find((item) => item.id === source)?.quote}
          </blockquote>
          <p className="muted">
            {feedback.find((item) => item.id === source)?.author} · Illustrative
            response
          </p>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSource(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
function Announcements() {
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [audience, setAudience] = useState("Students and teachers");
  const [open, setOpen] = useState(false);
  return (
    <>
      <PageHeading
        eyebrow="CLOSE THE FEEDBACK LOOP"
        title="Keep your community in the loop."
        description="A thoughtful update helps people feel heard."
      />
      <Panel className="form-panel announcement-panel">
        <span className="icon-box blue">
          <Send size={23} />
        </span>
        <h2>A message with purpose</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setOpen(true);
          }}
        >
          <TextField
            select
            label="Recipients"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
          >
            {[
              "Students and teachers",
              "Students",
              "Teachers",
              "Sample feedback submitter",
            ].map((value) => (
              <MenuItem key={value} value={value}>
                {value}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            required
            label="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <TextField
            required
            label="Message"
            multiline
            minRows={6}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <div className="form-actions">
            <span className="muted">Review before sharing.</span>
            <Button type="submit" variant="contained">
              Preview announcement
            </Button>
          </div>
        </form>
        <PreviewNote>No delivery endpoint is connected.</PreviewNote>
      </Panel>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Announcement preview</DialogTitle>
        <DialogContent>
          <Tag>{audience}</Tag>
          <h2>{subject}</h2>
          <p className="message-body">{message}</p>
          <PreviewNote>
            Nothing will be sent. This is a visual preview only.
          </PreviewNote>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Back to editing</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
function People({ notify }: Props) {
  const [filter, setFilter] = useState("All roles");
  const people = [
    {
      name: "Alex Lee",
      initials: "AL",
      email: "alex@example.com",
      role: "Student",
      status: "Active",
    },
    {
      name: "Jamie Wong",
      initials: "JW",
      email: "jamie@example.com",
      role: "Teacher",
      status: "Active",
    },
    {
      name: "Morgan Wong",
      initials: "MW",
      email: "morgan@example.com",
      role: "Admin",
      status: "Active",
    },
    {
      name: "Sam Chen",
      initials: "SC",
      email: "sam@example.com",
      role: "Student",
      status: "Invited",
    },
  ];
  return (
    <>
      <PageHeading
        eyebrow="A COMMUNITY OF CURIOUS MINDS"
        title="The people who make it happen."
        description="A preview of account roles and course access. No real users are connected."
      />
      <Panel className="library-panel">
        <div className="library-toolbar">
          <h2>
            People <span className="count-badge">4</span>
          </h2>
          <TextField
            select
            label="Filter role"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            sx={{ width: 170 }}
          >
            {["All roles", "Student", "Teacher", "Admin"].map((value) => (
              <MenuItem key={value} value={value}>
                {value}
              </MenuItem>
            ))}
          </TextField>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Person</th>
                <th>Role</th>
                <th>Course access</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {people
                .filter(
                  (person) => filter === "All roles" || person.role === filter,
                )
                .map((person) => (
                  <tr key={person.email}>
                    <td>
                      <Avatar
                        sx={{
                          width: 35,
                          height: 35,
                          fontSize: 12,
                          bgcolor: "action.selected",
                          color: "primary.main",
                        }}
                      >
                        {person.initials}
                      </Avatar>
                      <div>
                        <strong>{person.name}</strong>
                        <small>{person.email}</small>
                      </div>
                    </td>
                    <td>{person.role}</td>
                    <td>
                      {person.role === "Admin"
                        ? "Administrative access"
                        : "SE essentials"}
                    </td>
                    <td>
                      <Tag
                        tone={person.status === "Active" ? "green" : "amber"}
                      >
                        {person.status}
                      </Tag>
                    </td>
                    <td>
                      <Button
                        size="small"
                        onClick={() =>
                          notify(
                            "Access-management preview only. No account or permission was changed.",
                          )
                        }
                      >
                        Preview access
                      </Button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <PreviewNote>
        All names and addresses are fictitious sample records.
      </PreviewNote>
    </>
  );
}
function Usage() {
  const [period, setPeriod] = useState("This week");
  return (
    <>
      <PageHeading
        eyebrow="THOUGHTFUL USE OF SHARED RESOURCES"
        title="AI usage"
        description="Understand requests, reliability and the resources behind your AI features."
        action={
          <TextField
            select
            label="Reporting period"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            sx={{ width: 160 }}
          >
            {["This week", "Last week"].map((value) => (
              <MenuItem key={value} value={value}>
                {value}
              </MenuItem>
            ))}
          </TextField>
        }
      />
      <div className="stats-grid">
        <Stat
          label="Sample AI requests"
          value={period === "This week" ? "842" : "710"}
          detail="Illustrative requests, not measured"
          icon="sparkles"
          tone="purple"
        />
        <Stat
          label="Sample failures"
          value="15"
          detail="Includes 4 rate-limit examples"
          icon="usage"
          tone="amber"
        />
        <Stat
          label="Actual token usage"
          value="Unavailable"
          detail="No AI provider connected"
          icon="review"
          tone="green"
        />
      </div>
      <Panel className="library-panel">
        <div className="library-toolbar">
          <h2>By feature</h2>
          <Tag>Illustrative data</Tag>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Feature</th>
                <th>Requests</th>
                <th>Failures</th>
                <th>Rate limited</th>
                <th>Tokens</th>
              </tr>
            </thead>
            <tbody>
              {[
                {
                  name: "Student companion",
                  requests: period === "This week" ? 624 : 520,
                  failures: 9,
                  limited: 3,
                },
                {
                  name: "Teacher generation",
                  requests: period === "This week" ? 174 : 150,
                  failures: 5,
                  limited: 1,
                },
                {
                  name: "Feedback analysis",
                  requests: period === "This week" ? 44 : 40,
                  failures: 1,
                  limited: 0,
                },
              ].map((row) => (
                <tr key={row.name}>
                  <td>
                    <span className="file-icon purple">
                      <Sparkles size={19} />
                    </span>
                    <strong>{row.name}</strong>
                  </td>
                  <td>{row.requests}</td>
                  <td>{row.failures}</td>
                  <td>{row.limited}</td>
                  <td>
                    <span className="muted">Unavailable</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <div className="callout">
        <BarChart3 size={22} />
        <p>
          Real request counts, quotas and token measurements will be added when
          the SoC LLM integration is implemented. This preview does not call an
          AI provider or collect usage.
        </p>
      </div>
    </>
  );
}
export default function Admin({ notify }: Props) {
  const section = useLocation().pathname.split("/")[2];
  switch (section) {
    case "overview":
      return <Overview />;
    case "forms":
      return <Forms />;
    case "responses":
      return <Responses />;
    case "announcements":
      return <Announcements />;
    case "users":
      return <People notify={notify} />;
    case "usage":
      return <Usage />;
    default:
      return (
        <EmptyState title="This page isn’t here">
          <Link to="/admin/overview">Back to analytics</Link>
        </EmptyState>
      );
  }
}

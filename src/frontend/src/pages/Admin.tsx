import { useState } from "react";
import AdminAccounts from "./AdminAccounts";
import AdminCourses from "./AdminCourses";
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
  TextField,
} from "@mui/material";
import {
  ArrowRight,
  BarChart3,
  FileText,
  Plus,
  Sparkles,
} from "lucide-react";
import {
  EmptyState,
  PageHeading,
  Panel,
  PreviewNote,
  Stat,
  Tag,
} from "../components/ui";

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
function AdminContent() {
  const section = useLocation().pathname.split("/")[2];
  switch (section) {
    case "forms":
      return <Forms />;
    case "users":
      return <AdminAccounts />;
    case "courses":
      return <AdminCourses />;
    case "usage":
      return <Usage />;
    default:
      return (
        <EmptyState title="This page isn’t here">
          <Link to="/admin/analytics">Back to analytics</Link>
        </EmptyState>
      );
  }
}

export default function Admin() {
  const section = useLocation().pathname.split("/")[2];
  const preview = ["forms", "usage"].includes(section);
  return (
    <div className={`admin-surface${preview ? " admin-preview" : ""}`}>
      <AdminContent />
    </div>
  );
}

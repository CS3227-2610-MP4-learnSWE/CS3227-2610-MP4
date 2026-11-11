import { Link, useNavigate } from "react-router";
import { Button } from "@mui/material";
import { PageHeading, Panel } from "../ui";
import { useFeedbackRead } from "../../hooks/useFeedbackRead";
import { adminBase } from "../../services/feedbackApi";
import { hubPaths } from "../../lib/feedbackPaths";

const stateLabel = { open: "Open", closed: "Closed", draft: "Draft" } as const;

/** The Responses tab landing: pick a published form, then review its responses at its own address. */
export default function ResponsesChooser() {
  const navigate = useNavigate();
  const read = useFeedbackRead(`${adminBase}?limit=100&offset=0`, "forms");
  const forms = read.data?.items.filter((form) => form.state !== "draft");
  return (
    <div className="admin-surface admin-feedback">
      <PageHeading
        title="Feedback responses"
        description="Choose a form to review its submitted responses. Unfinished drafts are private and never shown."
      />
      <Panel>
        {read.loading && <p role="status">Loading feedback forms...</p>}
        {read.error && (
          <div>
            <p role="alert">{read.error}</p>
            <Button onClick={read.reload}>Retry</Button>
          </div>
        )}
        {forms && !forms.length && (
          <>
            <p role="status">
              No published feedback forms yet. Publish a form on the Forms tab
              to collect responses.
            </p>
            <Link to={hubPaths.forms()}>Go to Forms</Link>
          </>
        )}
        {forms && forms.length > 0 && (
          <div className="feedback-hub-chooser">
            <label htmlFor="feedback-hub-form">Feedback form</label>
            <select
              id="feedback-hub-form"
              value=""
              onChange={(event) => {
                if (event.target.value)
                  navigate(hubPaths.formResponses(event.target.value));
              }}
            >
              <option value="">Choose a feedback form</option>
              {forms.map((form) => (
                <option key={form.id} value={form.id}>
                  {`${form.title} · ${stateLabel[form.state]} · Responses: ${form.response_count}`}
                </option>
              ))}
            </select>
            {read.data?.next_offset !== null && (
              <p>
                Showing the first 100 forms. Open an older form from the Forms
                tab, then choose Review responses.
              </p>
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}

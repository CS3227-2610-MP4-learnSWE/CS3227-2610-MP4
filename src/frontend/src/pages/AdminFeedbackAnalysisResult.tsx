import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { Button } from "@mui/material";
import { PageHeading, Panel } from "../components/ui";
import { useFeedbackPaths } from "../lib/feedbackPaths";
import QuestionResults from "../components/QuestionResults";
import DeleteAnalysisDialog from "../components/DeleteAnalysisDialog";
import { useAnalysisPolling } from "../hooks/useAnalysisPolling";
import type { Analysis } from "../services/feedbackAnalysisApi";
import {
  DELETE_404,
  DELETED_STATUS,
  localTime,
  stepText,
} from "../messages/feedbackAnalysis";

function Evidence({ id, labels }: { id: string; labels: string[] }) {
  const paths = useFeedbackPaths();
  return (
    <span className="analysis-evidence">
      {labels.map((label) => (
        <Link
          key={label}
          to={paths.analysisEvidence(id, label)}
          aria-label={`Response ${label}`}
        >
          {label}
        </Link>
      ))}
    </span>
  );
}

function AiSection({ analysis }: { analysis: Analysis }) {
  const { ai, free_text: freeText } = analysis;
  const { done, total, step } = ai.progress;
  return (
    <section>
      <h2>AI analysis</h2>
      {ai.status === "running" && (
        <>
          <p role="status">
            AI analysis running. Step {done} of {total}: {stepText(step)}.
          </p>
          <div
            role="progressbar"
            aria-label="AI analysis progress"
            aria-valuemin={0}
            aria-valuenow={done}
            aria-valuemax={total}
            className="analysis-bar-track"
          >
            <span
              className="analysis-bar"
              style={{ width: `${total ? (done * 100) / total : 0}%` }}
            />
          </div>
        </>
      )}
      {ai.status === "failed" && ai.error && (
        <>
          <p role="alert">{ai.error.message}</p>
          <p>
            Stopped at step {done} of {total}. The statistics above are still
            correct.
          </p>
        </>
      )}
      {ai.status === "complete" && ai.result && (
        <>
          <p>AI-generated. Check the supporting responses before acting.</p>
          {freeText.used < freeText.total && (
            <p>
              AI themes based on {freeText.used} of {freeText.total} free-text
              answers.
            </p>
          )}
          <h3>Summary</h3>
          <p>{ai.result.summary}</p>
          <h3>Recurring issues</h3>
          {!ai.result.themes.length && <p>No recurring issues were found.</p>}
          <ul>
            {ai.result.themes.map((theme, i) => (
              <li key={i}>
                <strong>{theme.title}</strong> <em>Reported in feedback</em>
                <p>{theme.description}</p>
                <Evidence id={analysis.id} labels={theme.evidence} />
              </li>
            ))}
          </ul>
          <h3>Suggested improvements</h3>
          {!ai.result.suggestions.length && <p>No suggestions were made.</p>}
          <ul>
            {ai.result.suggestions.map((s, i) => (
              <li key={i}>
                <p>{s.text}</p>
                <em>
                  {s.basis === "feedback"
                    ? "Based on feedback"
                    : "AI suggestion (no supporting feedback)"}
                </em>{" "}
                <Evidence id={analysis.id} labels={s.evidence} />
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

export function AdminFeedbackAnalysisResultScreen({
  analysisId,
}: {
  analysisId: string;
}) {
  const navigate = useNavigate();
  const paths = useFeedbackPaths();
  const { analysis, loadError, notFound, pollError, loading, retry } =
    useAnalysisPolling(analysisId);
  const [deleting, setDeleting] = useState(false);
  return (
    <div className="admin-surface feedback-analysis">
      <PageHeading title="Feedback analysis result" />
      <p>
        <Link to={paths.analysis()}>Back to Feedback analysis</Link>
      </p>
      {loading && !analysis && !loadError && (
        <p role="status">Loading analysis...</p>
      )}
      {loadError && (
        <div>
          <p role="alert">{loadError}</p>
          {!notFound && <Button onClick={retry}>Retry</Button>}
        </div>
      )}
      {analysis && (
        <>
          <Panel>
            <p>
              Generated {localTime(analysis.created_at)} from{" "}
              {analysis.response_count} responses
            </p>
            {analysis.expected_count !== null &&
              analysis.expected_count !== analysis.response_count && (
                <p>
                  You selected {analysis.expected_count} responses;{" "}
                  {analysis.response_count} were analysed because responses
                  changed after you opened the list.
                </p>
              )}
            <Button color="error" onClick={() => setDeleting(true)}>
              Delete analysis
            </Button>
          </Panel>
          <Panel>
            <h2>Question results</h2>
            <p>Computed from the selected responses without AI.</p>
            <QuestionResults aggregates={analysis.aggregates} />
          </Panel>
          <Panel>
            <AiSection analysis={analysis} />
            {pollError && (
              <div>
                <p role="alert">{pollError}</p>
                {!pollError.startsWith("Stopped waiting") && (
                  <Button onClick={retry}>Retry</Button>
                )}
              </div>
            )}
          </Panel>
          {deleting && (
            <DeleteAnalysisDialog
              target={analysis}
              onClose={() => setDeleting(false)}
              onDeleted={(gone) =>
                navigate(paths.analysis(), {
                  replace: true,
                  state: { status: gone ? DELETE_404 : DELETED_STATUS },
                })
              }
            />
          )}
        </>
      )}
    </div>
  );
}

/** The old `/admin/feedback/analysis/:analysisId` page: a thin wrapper that reads the id from the address. */
export default function AdminFeedbackAnalysisResult() {
  const { analysisId = "" } = useParams();
  return <AdminFeedbackAnalysisResultScreen analysisId={analysisId} />;
}

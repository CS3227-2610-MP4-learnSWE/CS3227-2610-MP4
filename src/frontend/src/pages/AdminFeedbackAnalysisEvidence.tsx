import { useCallback, useLayoutEffect, useState } from "react";
import { Link, useLocation } from "react-router";
import { Button } from "@mui/material";
import { PageHeading, Panel } from "../components/ui";
import { useFeedbackPaths } from "../lib/feedbackPaths";
import {
  getAnalysis,
  getEvidence,
  type Analysis,
  type Evidence,
} from "../services/feedbackAnalysisApi";
import { loadMessage, localTime } from "../messages/feedbackAnalysis";

const answerText = (
  question: Evidence["response"]["form_snapshot"]["questions"][number],
  value: unknown,
) => {
  const label = (id: unknown) =>
    question.options.find((o) => o.id === id)?.label ?? "";
  if (value === null || value === undefined) return "Skipped";
  if (Array.isArray(value)) return value.map(label).join(", ");
  if (question.type === "multiple_choice" || question.type === "dropdown")
    return label(value);
  return String(value);
};

export function AdminFeedbackAnalysisEvidenceScreen({
  analysisId,
  label,
}: {
  analysisId: string;
  label: string;
}) {
  const paths = useFeedbackPaths();
  const [data, setData] = useState<Evidence | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  // Opened directly (first entry of this tab): the analysis is read too, independently of the evidence.
  const direct = useLocation().key === "default";
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  // Layout effect: the read leaves as soon as the page mounts.
  useLayoutEffect(() => {
    let current = true;
    setLoading(true);
    setError("");
    setData(null);
    getEvidence(analysisId, label)
      .then((value) => current && setData(value))
      .catch((e) => current && setError(loadMessage(e, "the response")))
      .finally(() => current && setLoading(false));
    return () => {
      current = false;
    };
  }, [analysisId, label, attempt]);
  useLayoutEffect(() => {
    if (!direct) return;
    let current = true;
    setAnalysis(null);
    getAnalysis(analysisId).then(
      (value) => current && setAnalysis(value),
      () => undefined, // optional context only: a failure shows nothing and is not retried
    );
    return () => {
      current = false;
    };
  }, [analysisId, direct]);
  const unavailable = error.startsWith("This response cannot be shown");
  return (
    <div className="admin-surface feedback-analysis">
      <PageHeading title={`Response ${label}`} />
      <p>
        <Link to={paths.analysisResult(analysisId)}>Back to analysis</Link>
      </p>
      {loading && <p role="status">Loading response...</p>}
      {error && (
        <div>
          <p role="alert">{error}</p>
          {!unavailable && <Button onClick={retry}>Retry</Button>}
        </div>
      )}
      {data && analysis && (
        <p>
          From the analysis of {analysis.form_title}, generated{" "}
          {localTime(analysis.created_at)}.
        </p>
      )}
      {data && (
        <Panel>
          <p>Respondent: {data.response.respondent.display_name}</p>
          <p>Submitted {localTime(data.response.submitted_at)}</p>
          {data.response.form_snapshot.questions.map((question) => {
            const answer = data.response.answers.find(
              (a) => a.question_id === question.id,
            );
            return (
              <section key={question.id}>
                <h2>{question.prompt}</h2>
                <p>{answerText(question, answer?.value)}</p>
              </section>
            );
          })}
        </Panel>
      )}
    </div>
  );
}

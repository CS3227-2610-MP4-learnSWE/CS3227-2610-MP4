import { Navigate, useLocation } from "react-router";
import {
  FeedbackPathsProvider,
  hubPaths,
  parseHubPath,
  type HubRoute,
  type HubTab,
} from "../../lib/feedbackPaths";
import { AdminFeedbackScreen } from "../../pages/AdminFeedback";
import AdminFeedbackAnalysis from "../../pages/AdminFeedbackAnalysis";
import { AdminFeedbackAnalysisResultScreen } from "../../pages/AdminFeedbackAnalysisResult";
import { AdminFeedbackAnalysisEvidenceScreen } from "../../pages/AdminFeedbackAnalysisEvidence";
import { AdminMessagingScreen } from "../../pages/AdminMessaging";
import HubCountsProvider from "./HubCountsProvider";
import HubNotFound from "./HubNotFound";
import HubTabs, { TAB_PANEL_ID, tabId } from "./HubTabs";
import ResponsesChooser from "./ResponsesChooser";

// The create receipt travels from /forms/new to the saved form inside this screen, so these share one instance.
const FEEDBACK_SCREENS = [
  "forms",
  "form-new",
  "form",
  "form-edit",
  "response-list",
  "response",
];
const TABS: HubTab[] = ["forms", "responses", "analysis", "follow-up"];

function FollowUpNote() {
  const { search } = useLocation();
  if (new URLSearchParams(search).has("review")) return null;
  return (
    <p className="feedback-hub-note">
      To reply to one person, open their response on the Responses tab and
      choose Respond to feedback.
    </p>
  );
}

function Screen({ route }: { route: Exclude<HubRoute, { notFound: true }> }) {
  const location = useLocation();
  const p = route.params as Record<string, string>;
  switch (route.screen) {
    case "forms":
    case "form-new":
      return <AdminFeedbackScreen route={{ screen: route.screen }} />;
    case "form":
    case "form-edit":
    case "response-list":
      return (
        <AdminFeedbackScreen
          route={{ screen: route.screen, formId: p.formId }}
        />
      );
    case "response":
      return (
        <AdminFeedbackScreen
          route={{
            screen: "response",
            formId: p.formId,
            responseId: p.responseId,
          }}
        />
      );
    case "chooser":
      return <ResponsesChooser />;
    case "analysis":
      // The query (`?form=`) is part of the screen's identity: leaving it resets the selection.
      return <AdminFeedbackAnalysis key={location.search} />;
    case "analysis-result":
      return <AdminFeedbackAnalysisResultScreen analysisId={p.analysisId} />;
    case "analysis-evidence":
      return (
        <AdminFeedbackAnalysisEvidenceScreen
          analysisId={p.analysisId}
          label={p.label}
        />
      );
    case "announcement":
      return (
        <>
          <FollowUpNote />
          <AdminMessagingScreen />
        </>
      );
    case "reply":
      return (
        <AdminMessagingScreen
          reply={{ formId: p.formId, responseId: p.responseId }}
        />
      );
    default:
      return null;
  }
}

/** One area for the whole feedback loop: tabs around the existing screens, which are mounted unchanged. */
export default function FeedbackHub() {
  const { pathname } = useLocation();
  const route = parseHubPath(pathname);
  if (!route.notFound && route.tab === null)
    return <Navigate to={hubPaths.forms()} replace />;
  const firstSegment = pathname.split("/")[3];
  const tab = route.notFound
    ? (TABS.find((item) => item === firstSegment) ?? null)
    : route.tab;
  return (
    <HubCountsProvider>
      <section aria-label="Feedback hub" className="feedback-hub">
        <p className="feedback-hub-label">Feedback hub</p>
        <p className="feedback-hub-line">
          Create forms, review responses, analyse feedback and follow up with
          respondents, all in one place.
        </p>
        <HubTabs selected={tab} />
        <div
          role="tabpanel"
          id={TAB_PANEL_ID}
          aria-labelledby={tab ? tabId(tab) : undefined}
          className="feedback-hub-panel"
        >
          <FeedbackPathsProvider value={hubPaths}>
            {route.notFound ? (
              <HubNotFound />
            ) : (
              <Screen
                key={
                  FEEDBACK_SCREENS.includes(route.screen)
                    ? "feedback"
                    : route.screen
                }
                route={route}
              />
            )}
          </FeedbackPathsProvider>
        </div>
      </section>
    </HubCountsProvider>
  );
}

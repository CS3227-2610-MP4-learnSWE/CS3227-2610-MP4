import { useRef } from "react";
import { useLocation, useNavigate } from "react-router";
import { hubPaths, type HubTab } from "../../lib/feedbackPaths";
import { formatCount, useHubCounts, type CountKind } from "./hubCounts";

export const TAB_PANEL_ID = "feedback-hub-panel";
export const tabId = (tab: HubTab) => `feedback-hub-tab-${tab}`;

const tabs: { tab: HubTab; label: string; kind: CountKind; landing: string }[] =
  [
    { tab: "forms", label: "Forms", kind: "forms", landing: hubPaths.forms() },
    {
      tab: "responses",
      label: "Responses",
      kind: "responses",
      landing: hubPaths.responses(),
    },
    {
      tab: "analysis",
      label: "Analysis",
      kind: "analysis",
      landing: hubPaths.analysis(),
    },
    {
      tab: "follow-up",
      label: "Follow-up",
      kind: "followUp",
      landing: hubPaths.announcement(),
    },
  ];

/** The four hub tabs. A tab is a link target: activating it pushes that tab's landing address. */
export default function HubTabs({ selected }: { selected: HubTab | null }) {
  const navigate = useNavigate();
  const location = useLocation();
  const counts = useHubCounts();
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const focusTab = (index: number) =>
    buttons.current[(index + tabs.length) % tabs.length]?.focus();
  const shown = tabs.map((item) => ({
    ...item,
    count: formatCount(counts[item.kind], item.kind, counts.drafts),
  }));
  return (
    <>
      <div
        role="tablist"
        aria-label="Feedback sections"
        className="feedback-hub-tabs"
        data-testid="hub-tabs"
      >
        {shown.map((item, index) => {
          const active = item.tab === selected;
          return (
            <button
              key={item.tab}
              ref={(node) => {
                buttons.current[index] = node;
              }}
              type="button"
              role="tab"
              id={tabId(item.tab)}
              aria-selected={active}
              aria-controls={TAB_PANEL_ID}
              aria-describedby={
                item.count ? `${tabId(item.tab)}-count` : undefined
              }
              tabIndex={active || (selected === null && index === 0) ? 0 : -1}
              className={`feedback-hub-tab ${active ? "active" : ""}`}
              onClick={() => {
                // The selected tab on its own landing address changes nothing and sends nothing.
                if (location.pathname === item.landing && !location.search)
                  return;
                navigate(item.landing);
              }}
              onKeyDown={(event) => {
                const keys: Record<string, number> = {
                  ArrowRight: index + 1,
                  ArrowLeft: index - 1,
                  Home: 0,
                  End: tabs.length - 1,
                };
                if (event.key in keys) {
                  event.preventDefault();
                  focusTab(keys[event.key]);
                }
              }}
            >
              {item.label}
              {item.count && (
                <span className="feedback-hub-badge" aria-hidden="true">
                  {item.count.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
      {shown.map(
        (item) =>
          item.count && (
            <span
              key={item.tab}
              id={`${tabId(item.tab)}-count`}
              className="sr-only"
            >
              {item.count.description}
            </span>
          ),
      )}
    </>
  );
}

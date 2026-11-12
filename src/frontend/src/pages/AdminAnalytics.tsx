import { useEffect, useMemo, useState } from "react";
import { IconButton, Tooltip } from "@mui/material";
import { RefreshCw } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router";
import BlockState from "../components/analytics/BlockState";
import ChatbotUsersTable from "../components/analytics/ChatbotUsersTable";
import DailyActivity from "../components/analytics/DailyActivity";
import GenerationTable from "../components/analytics/GenerationTable";
import HealthStrip, {
  type TimeChoices,
} from "../components/analytics/HealthStrip";
import HourlyCharts from "../components/analytics/HourlyCharts";
import PeriodSelector from "../components/analytics/PeriodSelector";
import AiUsageSection from "../components/analytics/AiUsageSection";
import QualitySection from "../components/analytics/QualitySection";
import { PageHeading, Panel } from "../components/ui";
import { useAnalyticsBlock } from "../hooks/useAnalyticsBlock";
import { browserZone } from "../lib/analyticsTime";
import {
  HOURLY_RANGES,
  choiceFromParams,
  hourlyRequestPeriod,
  periodOfChoice,
  todayUtc,
  type HourlyRange,
  type Range,
} from "../lib/period";
import * as api from "../services/featureAnalytics";

const SECTIONS = ["users", "ai", "quality"] as const;
const SETTLED = ["success", "error"];

/** Feature Analytics hub: one period for the Health, Feature outcomes, AI usage and Quality sections. */
export default function AdminAnalytics() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const today = useMemo(todayUtc, []);
  const choice = choiceFromParams(params, today);
  const { from, to } = periodOfChoice(choice, today);
  const period = useMemo(() => ({ from, to }), [from, to]);
  const rawWorkflow = params.get("workflow");
  const workflow: api.Workflow =
    api.WORKFLOWS.find((w) => w.id === rawWorkflow)?.id ?? "student_exercise";

  // Invalid or conflicting URL values are replaced by the defaults, without a message.
  useEffect(() => {
    const wanted = new URLSearchParams();
    if (["range", "from", "to"].some((key) => params.has(key))) {
      if (choice.kind === "custom") {
        wanted.set("from", choice.from);
        wanted.set("to", choice.to);
      } else wanted.set("range", choice.range);
    }
    if (params.has("workflow")) wanted.set("workflow", workflow);
    if (wanted.toString() !== params.toString())
      navigate({ search: `?${wanted}` }, { replace: true });
  }, [params, choice, workflow, navigate]);

  const withWorkflow = (next: URLSearchParams) => {
    if (params.has("workflow")) next.set("workflow", workflow);
    return `?${next}`;
  };
  const chooseRange = (range: Range) =>
    navigate({ search: withWorkflow(new URLSearchParams({ range })) });
  const chooseCustom = (from: string, to: string) =>
    navigate({ search: withWorkflow(new URLSearchParams({ from, to })) });
  const chooseWorkflow = (next: api.Workflow) => {
    const query = new URLSearchParams(params);
    query.set("workflow", next);
    navigate({ search: `?${query}` }, { replace: true });
  };

  // One independent read per block. Refresh changes `refresh`, which starts every read again.
  const [refresh, setRefresh] = useState(0);
  const key = `${period.from}|${period.to}`;
  // The hourly charts have their own range; rolling ranges end at the moment of the last refresh or choice.
  const [hourlyRange, setHourlyRange] = useState<HourlyRange>("period");
  const anchor = useMemo(() => new Date(), [refresh, hourlyRange]); // eslint-disable-line react-hooks/exhaustive-deps
  const hourlyPeriod = useMemo(
    () => hourlyRequestPeriod(hourlyRange, period, anchor),
    [hourlyRange, period, anchor],
  );
  const health = useAnalyticsBlock(
    `health|${key}`,
    (s) => api.getHealth(period, s),
    [refresh],
  );
  const hourly = useAnalyticsBlock(
    `hourly|${hourlyPeriod.from}|${hourlyPeriod.to}`,
    (s) => api.getHourly(hourlyPeriod, s),
    [refresh],
  );
  const daily = useAnalyticsBlock(
    `daily|${key}`,
    (s) => api.getDaily(period, s),
    [refresh],
  );
  const generation = useAnalyticsBlock(
    `generation|${key}`,
    (s) => api.readGeneration(period, s),
    [refresh],
  );

  const [statuses, setStatuses] = useState<Record<string, string>>({});
  const reporters = useMemo(
    () =>
      Object.fromEntries(
        SECTIONS.map((name) => [
          name,
          (status: string) =>
            setStatuses((all) =>
              all[name] === status ? all : { ...all, [name]: status },
            ),
        ]),
      ) as Record<(typeof SECTIONS)[number], (status: string) => void>,
    [],
  );
  const own = [health.status, hourly.status, daily.status, generation.status];
  const settled =
    own.every((s) => SETTLED.includes(s)) &&
    SECTIONS.every((name) => SETTLED.includes(statuses[name] ?? ""));
  const failed =
    own.includes("error") || SECTIONS.some((n) => statuses[n] === "error");
  const [updated, setUpdated] = useState<Date | null>(null);
  useEffect(() => {
    if (settled) setUpdated(new Date());
  }, [settled, failed]);

  const [times, setTimes] = useState<TimeChoices>({
    chatbot: "all",
    generation: "all",
  });
  const zone = browserZone();
  const sectionKey = `${key}|${refresh}`;

  return (
    <>
      <div className="analytics-hub-header">
        <PageHeading
          title="Feature Analytics"
          description={`Recorded data only. Dates are UTC; chart times are shown in your local time (${zone || "local time"}).`}
        />
        <div className="analytics-hub-controls">
          <PeriodSelector
            choice={choice}
            today={today}
            onRange={chooseRange}
            onCustom={chooseCustom}
          />
          <p className="analytics-hub-updated">
            {updated ? (
              <>
                Last updated{" "}
                <time dateTime={updated.toISOString()}>
                  {updated.toLocaleTimeString()}
                </time>
                {failed && ". Some sections could not be loaded."}
              </>
            ) : (
              "Not updated yet"
            )}
          </p>
          <Tooltip title="Refresh">
            <span>
              <IconButton
                aria-label="Refresh"
                className="analytics-hub-refresh"
                disabled={!settled}
                onClick={() => setRefresh((n) => n + 1)}
              >
                <RefreshCw size={20} aria-hidden="true" />
              </IconButton>
            </span>
          </Tooltip>
        </div>
      </div>

      <Panel className="analytics-panel" role="region" ariaLabel="Health">
        <h2 className="analytics-hub-section-title">Health</h2>
        <BlockState
          block={health}
          loading="Loading health..."
          subject="Health"
          retryLabel="Retry health"
        >
          {(data) => (
            <HealthStrip
              health={data}
              choices={times}
              onChoice={(w, next) => setTimes({ ...times, [w]: next })}
            />
          )}
        </BlockState>
        <div role="region" aria-label="Hourly activity">
          <div
            role="radiogroup"
            aria-label="Hourly chart range"
            className="analytics-hub-radios analytics-hub-range"
          >
            {HOURLY_RANGES.map((option) => (
              <label key={option.id}>
                <input
                  type="radio"
                  name="Hourly chart range"
                  checked={hourlyRange === option.id}
                  onChange={() => setHourlyRange(option.id)}
                />
                {option.label}
              </label>
            ))}
          </div>
          <BlockState
            block={hourly}
            loading="Loading hourly charts..."
            subject="Hourly charts"
            retryLabel="Retry hourly charts"
          >
            {(data) => (
              <HourlyCharts
                hourly={data}
                period={period}
                range={hourlyRange}
                now={anchor}
                timeZone={zone}
              />
            )}
          </BlockState>
        </div>
      </Panel>

      <Panel
        className="analytics-panel"
        role="region"
        ariaLabel="Feature outcomes"
      >
        <h2 className="analytics-hub-section-title">Feature outcomes</h2>
        <div role="region" aria-label="Daily activity">
          <BlockState
            block={daily}
            loading="Loading daily activity..."
            subject="Daily activity"
            retryLabel="Retry daily activity"
          >
            {(data) => <DailyActivity daily={data} />}
          </BlockState>
        </div>
        <ChatbotUsersTable
          key={sectionKey}
          period={period}
          report={reporters.users}
        />
        <div role="group" aria-label="Generation reliability">
          <h3>Generation reliability</h3>
          <BlockState
            block={generation}
            loading="Loading generation reliability..."
            subject="Generation reliability"
            retryLabel="Retry generation reliability"
          >
            {(data) => <GenerationTable data={data} />}
          </BlockState>
        </div>
      </Panel>

      <Panel className="analytics-panel" role="region" ariaLabel="AI usage">
        <h2 className="analytics-hub-section-title">AI usage</h2>
        <AiUsageSection
          key={sectionKey}
          period={period}
          report={reporters.ai}
        />
      </Panel>

      <Panel className="analytics-panel" role="region" ariaLabel="Quality">
        <h2 className="analytics-hub-section-title">Quality</h2>
        <QualitySection
          key={sectionKey}
          period={period}
          workflow={workflow}
          onWorkflow={chooseWorkflow}
          report={reporters.quality}
        />
      </Panel>
    </>
  );
}

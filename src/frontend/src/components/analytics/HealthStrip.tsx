import type { ReactNode } from "react";
import type * as api from "../../services/featureAnalytics";
import {
  notApplicableReason,
  percent1,
  seconds2,
  startsNote,
  unavailableReason,
} from "./copy";
import KpiTile from "./KpiTile";
import SeverityChip from "./SeverityChip";

export type TimeChoice = "all" | "successful" | "failed";
export type TimeChoices = { chatbot: TimeChoice; generation: TimeChoice };

const CHOICES: { id: TimeChoice; label: string }[] = [
  { id: "all", label: "All" },
  { id: "successful", label: "Successful" },
  { id: "failed", label: "Failed" },
];

type Tile = {
  state: api.State;
  reason: api.Reason | null;
  data_starts_on?: string | null;
};

/** Value and detail for a tile that is not available; null when the tile has numbers. */
function unusable(tile: Tile): { value: string; lines: string[] } | null {
  if (tile.state === "unavailable")
    return {
      value: "Unavailable",
      lines: [`${unavailableReason(tile.reason)}.`],
    };
  if (tile.state === "not_applicable")
    return {
      value: "Not applicable",
      lines: [`${notApplicableReason(tile.reason)}.`],
    };
  return null;
}

function FailureKpi({
  label,
  tile,
  threshold,
  detail,
  dataNote,
}: {
  label: string;
  tile: api.FailureTile;
  threshold: number;
  detail: string;
  dataNote: ReactNode;
}) {
  const bad = unusable(tile);
  const progress =
    tile.in_progress && tile.in_progress > 0
      ? [`${tile.in_progress} in progress`]
      : [];
  return (
    <KpiTile
      label={label}
      value={bad ? bad.value : percent1(tile.rate_percent ?? 0)}
      lines={[...(bad ? bad.lines : [detail]), ...progress]}
      severity={tile.severity}
      chip={
        tile.severity && !bad ? (
          <SeverityChip severity={tile.severity} threshold={threshold} />
        ) : undefined
      }
    >
      {dataNote}
    </KpiTile>
  );
}

function ResponseTimeKpi({
  label,
  tile,
  choice,
  onChoice,
  dataNote,
}: {
  label: string;
  tile: api.ResponseTimeTile;
  choice: TimeChoice;
  onChoice: (next: TimeChoice) => void;
  dataNote: ReactNode;
}) {
  const unavailable = tile.state === "unavailable";
  const set = tile[choice];
  const empty = !unavailable && (set.count ?? 0) === 0;
  const NONE = {
    all: "No requests in this period.",
    successful: "No successful requests in this period.",
    failed: "No failed requests in this period.",
  };
  const detail = {
    all: `${tile.all.count} requests, ${tile.failed.count} failed or timed out`,
    successful: `${tile.successful.count} successful requests`,
    failed: `${tile.failed.count} failed or timed-out requests (timeouts count as 120 s)`,
  };
  const name = `${label} outcome`;
  return (
    <KpiTile
      label={label}
      value={unavailable ? "Unavailable" : empty ? "No requests" : undefined}
      lines={[]}
    >
      <div role="radiogroup" aria-label={name} className="analytics-hub-radios">
        {CHOICES.map((option) => (
          <label key={option.id}>
            <input
              type="radio"
              name={name}
              checked={choice === option.id}
              onChange={() => onChoice(option.id)}
            />
            {option.label}
          </label>
        ))}
      </div>
      {unavailable ? (
        <p className="analytics-hub-tile-detail">
          {unavailableReason(tile.reason)}.
        </p>
      ) : empty ? (
        <p className="analytics-hub-tile-detail">{NONE[choice]}</p>
      ) : (
        <>
          <p className="analytics-hub-tile-time">
            Median{" "}
            <span data-testid="response-time-median">
              {seconds2(set.median_ms ?? 0)}
            </span>
          </p>
          <p className="analytics-hub-tile-time">
            p95{" "}
            <span data-testid="response-time-p95">
              {seconds2(set.p95_ms ?? 0)}
            </span>
          </p>
          <p className="analytics-hub-tile-detail">{detail[choice]}</p>
        </>
      )}
      {dataNote}
    </KpiTile>
  );
}

/** Six KPI tiles of the Health section. The response-time selectors change the shown set without a request. */
export default function HealthStrip({
  health,
  choices,
  onChoice,
}: {
  health: api.Health;
  choices: TimeChoices;
  onChoice: (workflow: keyof TimeChoices, next: TimeChoice) => void;
}) {
  const tiles: Tile[] = [
    health.chatbot_failure,
    health.generation_failure,
    health.rate_limited,
    health.chatbot_response_time,
    health.generation_response_time,
    health.practice_completion,
  ];
  const covered = tiles.filter((t) => t.state !== "unavailable");
  const shared =
    health.data_starts_on !== null &&
    covered.length > 0 &&
    covered.every((t) => t.data_starts_on === health.data_starts_on);
  const note = (tile: Tile): ReactNode =>
    !shared && tile.data_starts_on ? (
      <p className="analytics-hub-tile-detail">
        Data starts on {tile.data_starts_on}.
      </p>
    ) : null;
  const threshold = health.low_sample_threshold;
  const { chatbot_failure: chat, generation_failure: gen } = health;
  const limited = health.rate_limited;
  const done = health.practice_completion;
  const limitedBad = unusable(limited);
  const doneBad = unusable(done);
  return (
    <>
      <div role="group" aria-label="KPI tiles" className="analytics-hub-tiles">
        <FailureKpi
          label="Chatbot failure rate"
          tile={chat}
          threshold={threshold}
          detail={`${chat.failed} of ${chat.total} chatbot requests`}
          dataNote={note(chat)}
        />
        <FailureKpi
          label="Generation failure rate"
          tile={gen}
          threshold={threshold}
          detail={
            gen.includes_rate_limited
              ? `${gen.failed} of ${gen.total} generation requests, including rate-limited ones`
              : `${gen.failed} of ${gen.total} generation attempts; rate-limited requests are not recorded yet`
          }
          dataNote={note(gen)}
        />
        <KpiTile
          label="Rate-limited requests"
          value={limitedBad ? limitedBad.value : String(limited.count)}
          lines={
            limitedBad
              ? limitedBad.lines
              : [`of ${limited.total_requests} requests`]
          }
        >
          {note(limited)}
        </KpiTile>
        <ResponseTimeKpi
          label="Chatbot response time"
          tile={health.chatbot_response_time}
          choice={choices.chatbot}
          onChoice={(next) => onChoice("chatbot", next)}
          dataNote={note(health.chatbot_response_time)}
        />
        <ResponseTimeKpi
          label="Generation response time"
          tile={health.generation_response_time}
          choice={choices.generation}
          onChoice={(next) => onChoice("generation", next)}
          dataNote={note(health.generation_response_time)}
        />
        <KpiTile
          label="Practice completion"
          value={doneBad ? doneBad.value : `${done.percentage}%`}
          lines={
            doneBad
              ? doneBad.lines
              : [
                  `${done.submitted} of ${done.started} attempts submitted by the end of the period`,
                ]
          }
        >
          {note(done)}
        </KpiTile>
      </div>
      {shared && health.data_starts_on && (
        <p className="muted">{startsNote(health.data_starts_on)}</p>
      )}
    </>
  );
}

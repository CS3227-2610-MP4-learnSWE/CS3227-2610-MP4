import type { Generation } from "../../services/featureAnalytics";
import { startsNote, unavailableText } from "./copy";

/** Generation reliability: requests per workflow. Before limiter refusals are recorded, requests equal attempts. */
export default function GenerationTable({ data }: { data: Generation }) {
  const recorded = data.recording_started_on;
  const refusals = data.workflows.every(
    (row) => row.rate_limited_state?.state === "available",
  );
  return (
    <>
      <div
        className="table-scroll analytics-scroll"
        role="region"
        aria-label="Generation success rates, scrollable"
        tabIndex={0}
      >
        <table aria-label="Generation success rates">
          <thead>
            <tr>
              <th scope="col">Workflow</th>
              <th scope="col">Requests</th>
              <th scope="col">Successful</th>
              <th scope="col">Unsuccessful</th>
              <th scope="col">Success rate</th>
            </tr>
          </thead>
          <tbody>
            {data.workflows.map((row) => (
              <tr key={row.workflow}>
                <th scope="row">{row.label}</th>
                {row.state === "unavailable" ? (
                  <td colSpan={4}>{unavailableText(row.reason, recorded)}</td>
                ) : (
                  <>
                    <td>{row.requests ?? row.attempts}</td>
                    <td>{row.successful}</td>
                    <td>{row.unsuccessful}</td>
                    <td>
                      {row.state === "available"
                        ? `${row.rate_percent?.toFixed(1)}%`
                        : "No rate can be calculated: no generation requests in this period."}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted">
        {refusals
          ? "Requests include those refused by the rate limiter, which count as unsuccessful."
          : "Rate-limited requests are not recorded yet."}
      </p>
      {data.data_starts_on && (
        <p className="muted">{startsNote(data.data_starts_on)}</p>
      )}
    </>
  );
}

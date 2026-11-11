import { useEffect, useRef, useState } from "react";
import { Alert, Button, Tab, Tabs } from "@mui/material";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useAnalyticsBlock } from "../../hooks/useAnalyticsBlock";
import * as api from "../../services/featureAnalytics";
import { percent1, startsNote, unavailableText } from "./copy";

const COLUMNS: { sort: api.UsersSort; label: string; first: api.UsersOrder }[] =
  [
    { sort: "name", label: "Name", first: "asc" },
    { sort: "successful", label: "Successful", first: "desc" },
    { sort: "unsuccessful", label: "Unsuccessful", first: "desc" },
    { sort: "failure_rate", label: "Failure rate", first: "desc" },
  ];

/** Chatbot requests by user: role tabs, sortable columns and paging; every change is one request. */
export default function ChatbotUsersTable({
  period,
  report,
}: {
  period: api.Period;
  report: (status: string) => void;
}) {
  const [wanted, setWanted] = useState<api.UsersQuery>({
    role: "student",
    sort: "unsuccessful",
    order: "desc",
    offset: 0,
  });
  const block = useAnalyticsBlock(
    `users|${period.from}|${period.to}|${wanted.role}|${wanted.sort}|${wanted.order}|${wanted.offset}`,
    (signal) => api.getChatbotUsers(period, wanted, signal),
  );
  // The last successful table stays on screen (with a message above it) when a sort, page or tab change fails.
  const shown = useRef<api.ChatbotUsers | null>(null);
  if (block.data) shown.current = block.data;
  useEffect(() => report(block.status), [block.status, report]);

  const current = block.data ?? shown.current;
  const change = (next: Partial<api.UsersQuery>) =>
    setWanted({
      role: current?.role ?? wanted.role,
      sort: current?.sort ?? wanted.sort,
      order: current?.order ?? wanted.order,
      offset: current?.offset ?? wanted.offset,
      ...next,
    });
  const loading = block.status === "loading";
  const failed = block.status === "error";

  const from = current && current.rows.length > 0 ? current.offset + 1 : 0;
  const to = current ? current.offset + current.rows.length : 0;
  const total = current?.total_users ?? 0;
  const teacher = current?.role === "teacher";

  function sortBy(column: (typeof COLUMNS)[number]) {
    if (!current) return;
    change({
      sort: column.sort,
      order:
        current.sort === column.sort
          ? current.order === "asc"
            ? "desc"
            : "asc"
          : column.first,
      offset: 0,
    });
  }

  return (
    <div role="group" aria-label="Chatbot requests by user">
      <h3>Chatbot requests by user</h3>
      <Tabs
        value={current?.role ?? wanted.role}
        onChange={(_, role: api.UsersRole) => change({ role, offset: 0 })}
        aria-label="Role"
      >
        <Tab value="student" label="Students" />
        <Tab value="teacher" label="Teachers" />
      </Tabs>
      {failed && (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={block.reload}>
              Retry chatbot users
            </Button>
          }
        >
          {api.loadFailure("Chatbot users", block.error)}
        </Alert>
      )}
      {loading && <p role="status">Loading chatbot users...</p>}
      {current && !loading && (
        <>
          {teacher ? (
            <p>
              {unavailableText(current.reason, current.recording_started_on)}
            </p>
          ) : current.state === "unavailable" ? (
            <p>
              {unavailableText(current.reason, current.recording_started_on)}
            </p>
          ) : (
            <>
              <div className="analytics-hub-totals">
                <p className="analytics-hub-total">
                  <span className="analytics-hub-total-label">
                    Students total:{" "}
                  </span>
                  <strong>{current.totals.successful}</strong> successful,{" "}
                  <strong>{current.totals.unsuccessful}</strong> unsuccessful
                </p>
                <p className="analytics-hub-total">
                  <span className="analytics-hub-total-label">
                    Teachers total:{" "}
                  </span>
                  {unavailableText("no_source")}
                </p>
                <p className="analytics-hub-total">
                  <span className="analytics-hub-total-label">
                    All users total:{" "}
                  </span>
                  {unavailableText(current.all_users_total.reason)}
                </p>
              </div>
              {current.in_progress ? (
                <p className="muted">{current.in_progress} in progress</p>
              ) : null}
              {current.data_starts_on && (
                <p className="muted">{startsNote(current.data_starts_on)}</p>
              )}
              {current.rows.length === 0 ? (
                <p>No chatbot requests in this period.</p>
              ) : (
                <>
                  <div
                    className="table-scroll analytics-scroll"
                    role="region"
                    aria-label="Chatbot requests by user, scrollable"
                    tabIndex={0}
                  >
                    <table aria-label="Chatbot requests by user">
                      <thead>
                        <tr>
                          {COLUMNS.map((c) => (
                            <th
                              scope="col"
                              key={c.sort}
                              aria-sort={
                                current.sort === c.sort
                                  ? current.order === "asc"
                                    ? "ascending"
                                    : "descending"
                                  : undefined
                              }
                            >
                              <Button
                                size="small"
                                color="inherit"
                                onClick={() => sortBy(c)}
                                aria-label={`Sort by ${c.label}`}
                              >
                                {c.label}
                                {current.sort === c.sort ? (
                                  current.order === "asc" ? (
                                    <ArrowUp size={14} aria-hidden="true" />
                                  ) : (
                                    <ArrowDown size={14} aria-hidden="true" />
                                  )
                                ) : (
                                  <ArrowUpDown size={14} aria-hidden="true" />
                                )}
                              </Button>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {current.rows.map((row) => (
                          <tr key={row.user_id}>
                            <th scope="row">{row.name ?? row.user_id}</th>
                            <td>{row.successful}</td>
                            <td>{row.unsuccessful}</td>
                            <td>
                              {row.failure_rate_percent === null
                                ? "No requests"
                                : percent1(row.failure_rate_percent)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="analytics-pager">
                    <Button
                      variant="outlined"
                      disabled={loading || current.offset === 0}
                      onClick={() =>
                        change({
                          offset: Math.max(
                            0,
                            current.offset - api.USERS_PAGE_SIZE,
                          ),
                        })
                      }
                    >
                      Previous page
                    </Button>
                    <p>{`Showing ${from} to ${to} of ${total} users`}</p>
                    <Button
                      variant="outlined"
                      disabled={loading || to >= total}
                      onClick={() =>
                        change({ offset: current.offset + api.USERS_PAGE_SIZE })
                      }
                    >
                      Next page
                    </Button>
                  </div>
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

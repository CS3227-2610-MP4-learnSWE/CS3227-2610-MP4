import { Link, useLocation } from "react-router";
import { Button } from "@mui/material";
import { PageHeading, Panel } from "../components/ui";
import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { useFeedbackRead } from "../hooks/useFeedbackRead";
import MessagesInbox from "../components/MessagesInbox";
import { getSessionGeneration } from "../services/client";

import { Inbox, ClipboardList, ChevronRight } from "lucide-react";
import { publishInboxCount } from "../hooks/useInboxUnread";

const labels = {
  not_started: "Not started",
  draft: "Draft",
  completed: "Completed",
  closed: "Closed",
};
export default function FeedbackInbox() {
  const { user } = useAuth();
  const location = useLocation();
  const [offset, setOffset] = useState(0);
  const read = useFeedbackRead(
    `/api/feedback/inbox?limit=20&offset=${offset}`,
    "inbox",
  );
  useEffect(() => {
    if (read.data) publishInboxCount("requests", read.data.unread_count);
  }, [read.data]);
  return (
    <div className="messaging-page inbox-page">
      <PageHeading
        eyebrow="YOUR INBOX"
        title="Inbox"
        description="Feedback requests, announcements and replies, all in one place."
      />
      <Panel className="messaging-panel inbox-requests">
        <div className="inbox-section-heading">
          <div>
            <h2>Feedback requests</h2>
            <p>Share feedback or continue a saved draft.</p>
          </div>
          <span className="section-icon">
            <ClipboardList size={23} aria-hidden="true" />
          </span>
        </div>
        {read.loading && <p role="status">Loading feedback requests...</p>}
        {read.error && (
          <div>
            <p role="alert">{read.error}</p>
            <Button onClick={read.reload}>Retry</Button>
          </div>
        )}
        {read.data && (
          <>
            <p role="status">Unread requests: {read.data.unread_count}</p>
            {!read.data.items.length && <p>No feedback requests yet.</p>}
            <div className="feedback-list">
              {read.data.items.map((item) => (
                <article className="request-entry" key={item.id}>
                  <Link
                    className="inbox-request-row"
                    aria-label={item.title}
                    to={`/${user?.role}/feedback/${item.form_id}`}
                  >
                    <span className="request-row-icon">
                      <Inbox size={21} aria-hidden="true" />
                    </span>
                    <span className="request-row-content">
                      <strong>{item.title}</strong>
                      <span className="request-row-state">
                        {item.read_at ? "Read" : "Unread"} ·{" "}
                        <span className="inbox-chip">
                          {labels[item.response_status]}
                        </span>
                      </span>
                    </span>
                    <ChevronRight size={18} aria-hidden="true" />
                  </Link>
                </article>
              ))}
            </div>
            {offset > 0 && (
              <Button onClick={() => setOffset(Math.max(0, offset - 20))}>
                Previous page
              </Button>
            )}
            {read.data.next_offset !== null && (
              <Button onClick={() => setOffset(read.data!.next_offset!)}>
                Next page
              </Button>
            )}
          </>
        )}
      </Panel>
      <MessagesInbox key={`${location.key}:${getSessionGeneration()}`} />
    </div>
  );
}

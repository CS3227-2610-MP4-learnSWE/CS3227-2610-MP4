import { Link, useLocation } from "react-router";
import { Button } from "@mui/material";
import { PageHeading, Panel } from "../components/ui";
import { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { useFeedbackRead } from "../hooks/useFeedbackRead";
import MessagesInbox from "../components/MessagesInbox";
import { getSessionGeneration } from "../services/client";

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
  return (
    <>
      <PageHeading
        eyebrow="YOUR FEEDBACK"
        title="Feedback requests"
        description="Open a request to share feedback or continue your saved draft."
      />
      <Panel>
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
                <article key={item.id}>
                  <Link to={`/${user?.role}/feedback/${item.form_id}`}>
                    {item.title}
                  </Link>
                  <p>
                    {item.read_at ? "Read" : "Unread"} ·{" "}
                    {labels[item.response_status]}
                  </p>
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
    </>
  );
}

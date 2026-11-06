import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "@mui/material";
import { useAuth } from "../auth/AuthContext";
import { useMessagingRead } from "../hooks/useMessagingRead";
import { getSessionGeneration } from "../services/client";
import {
  messagingCode,
  messagingError,
  messagingWrite,
  type InboxMessage,
  type MessagePage,
} from "../services/messagingApi";
import { Panel } from "./ui";

export default function MessagesInbox() {
  const [offset, setOffset] = useState(0);
  const read = useMessagingRead<MessagePage>(
    `/api/messaging/inbox?limit=20&offset=${offset}`,
  );
  const [items, setItems] = useState<InboxMessage[]>([]);
  const [unread, setUnread] = useState(0);
  const [pending, setPending] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const inFlight = useRef(false);
  const alive = useRef(true);
  const controller = useRef<AbortController | null>(null);
  const navigate = useNavigate();
  const { user } = useAuth();
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!read.data) return;
    const data = read.data;
    setItems((old) =>
      offset === 0
        ? data.items
        : [
            ...old.filter((i) => !data.items.some((n) => n.id === i.id)),
            ...data.items,
          ],
    );
    setUnread(data.unread_count);
  }, [read.data, offset]);
  const mark = async (id: string) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(id);
    setErrors((old) => ({ ...old, [id]: "" }));
    controller.current = new AbortController();
    const generation = getSessionGeneration();
    try {
      const result = await messagingWrite<{ id: string; read_at: string }>(
        `/api/messaging/inbox/${encodeURIComponent(id)}/read`,
        {},
        controller.current.signal,
      );
      if (!alive.current || generation !== getSessionGeneration()) return;
      setItems((old) =>
        old.map((i) => (i.id === id ? { ...i, read_at: result.read_at } : i)),
      );
      setUnread((n) => Math.max(0, n - 1));
    } catch (error) {
      if (
        !alive.current ||
        generation !== getSessionGeneration() ||
        messagingCode(error) === "stale_session"
      )
        return;
      if (messagingCode(error) === "forbidden")
        navigate(`/${user?.role}/overview`, { replace: true });
      setErrors((old) => ({ ...old, [id]: messagingError(error) }));
    } finally {
      if (alive.current) {
        inFlight.current = false;
        setPending(null);
      }
    }
  };
  return (
    <Panel className="messaging-panel">
      <h2>Messages</h2>
      {read.loading && <p role="status">Loading messages…</p>}
      {read.error && (
        <div>
          <p role="alert">{read.error}</p>
          <Button
            onClick={read.reload}
            disabled={pending !== null || read.loading}
          >
            Retry messages
          </Button>
        </div>
      )}
      {(read.data || items.length > 0) && (
        <p role="status">{unread} unread messages</p>
      )}
      {read.data && !items.length && <p>No messages yet.</p>}
      <div className="messaging-list">
        {items.map((item) => (
          <article aria-label={item.subject} key={item.id}>
            <p>
              {item.kind === "announcement"
                ? "Announcement"
                : "Feedback response"}{" "}
              · {item.read_at ? "Read" : "Unread"}
            </p>
            <h3>{item.subject}</h3>
            <p className="messaging-text">{item.body}</p>
            <p>{item.sent_at}</p>
            {!item.read_at && (
              <Button
                onClick={() => void mark(item.id)}
                disabled={pending !== null || read.loading}
              >
                Mark as read
              </Button>
            )}
            {errors[item.id] && <p role="alert">{errors[item.id]}</p>}
          </article>
        ))}
      </div>
      {read.data?.next_offset !== null &&
        read.data?.next_offset !== undefined && (
          <Button
            disabled={read.loading || pending !== null}
            onClick={() => setOffset(read.data!.next_offset!)}
          >
            Load more messages
          </Button>
        )}
    </Panel>
  );
}

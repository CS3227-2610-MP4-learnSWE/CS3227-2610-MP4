import { useState } from "react";
import { Link, useLocation } from "react-router";
import {
  Button,
  FormControlLabel,
  Radio,
  RadioGroup,
  TextField,
} from "@mui/material";
import { ArrowRight, Inbox, MailOpen, MessageSquare } from "lucide-react";
import {
  EmptyState,
  PageHeading,
  Panel,
  PreviewNote,
  Tag,
} from "../components/ui";
import { type Role } from "../data";
import { useDemo } from "../state";

export default function InboxPage({ role }: { role: Role }) {
  const { messages, read } = useDemo();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState("All messages");
  const list = messages[role];
  const unread = list.filter((message) => message.unread).length;
  const selected = list.find((message) => message.id === selectedId);
  const visible = list.filter(
    (message) => filter !== "Unread" || message.unread,
  );
  return (
    <>
      <PageHeading
        eyebrow="LET’S KEEP IN TOUCH"
        title="Your inbox."
        description="Thoughtful updates, feedback requests and a little encouragement."
        action={<Tag>{unread} unread</Tag>}
      />
      <div className="filter-buttons inbox-filters">
        {["All messages", "Unread"].map((option) => (
          <Button
            key={option}
            size="small"
            variant={filter === option ? "contained" : "text"}
            onClick={() => setFilter(option)}
          >
            {option}
          </Button>
        ))}
      </div>
      <div className="inbox-layout">
        <Panel className="message-list">
          {visible.length ? (
            visible.map((message) => (
              <button
                className={`message-item ${message.unread ? "unread" : ""} ${selectedId === message.id ? "selected" : ""}`}
                key={message.id}
                onClick={() => {
                  setSelectedId(message.id);
                  read(role, message.id);
                }}
              >
                <span className="message-sender">
                  {message.sender}
                  <small>{message.time}</small>
                </span>
                <strong>{message.title}</strong>
                <span className="message-preview">{message.body}</span>
                <span className="message-category">
                  {message.unread && <i />}
                  {message.category}
                </span>
              </button>
            ))
          ) : (
            <EmptyState title="You’re all caught up">
              No unread messages. A little breathing room.
            </EmptyState>
          )}
        </Panel>
        <Panel className="message-detail">
          {selected ? (
            <>
              <div className="detail-top">
                <Tag tone={selected.survey ? "purple" : "blue"}>
                  {selected.category}
                </Tag>
                <MailOpen size={19} />
              </div>
              <h2>{selected.title}</h2>
              <p className="muted">
                {selected.sender} · {selected.time}
              </p>
              <p className="message-body">{selected.body}</p>
              {selected.survey && (
                <Button
                  component={Link}
                  to={`/${role}/feedback`}
                  variant="contained"
                  endIcon={<ArrowRight size={16} />}
                >
                  Open feedback form
                </Button>
              )}
              <PreviewNote>
                Sample inbox message · Nothing was sent externally.
              </PreviewNote>
            </>
          ) : (
            <div className="empty-state">
              <span className="icon-box blue">
                <Inbox size={27} />
              </span>
              <h3>A little space for connection.</h3>
              <p>Select a message to read it here.</p>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
export function FeedbackForm({
  notify,
}: {
  notify: (message?: string) => void;
}) {
  const [rating, setRating] = useState("");
  const [feedback, setFeedback] = useState("");
  const role = useLocation().pathname.split("/")[1];
  return (
    <>
      <PageHeading
        eyebrow="YOUR EXPERIENCE MATTERS"
        title="A better learning experience"
        description="A few thoughtful answers can help us make a meaningful difference."
      />
      <Panel className="form-panel">
        <span className="icon-box purple">
          <MessageSquare size={23} />
        </span>
        <h2>How is learnSWE working for you?</h2>
        <p className="muted">Sample feedback form · About 2 minutes</p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            notify("Preview only. Your feedback was not submitted or saved.");
          }}
        >
          <fieldset>
            <legend>How useful has the experience been?</legend>
            <RadioGroup
              value={rating}
              onChange={(e) => setRating(e.target.value)}
            >
              {["Very useful", "Somewhat useful", "Could be better"].map(
                (option) => (
                  <FormControlLabel
                    value={option}
                    key={option}
                    control={<Radio required />}
                    label={option}
                  />
                ),
              )}
            </RadioGroup>
          </fieldset>
          <TextField
            label="What would make it better?"
            multiline
            minRows={4}
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
          />
          <div className="form-actions">
            <Button component={Link} to={`/${role}/inbox`}>
              Back to inbox
            </Button>
            <Button type="submit" variant="contained">
              Preview submission
            </Button>
          </div>
        </form>
        <PreviewNote>No feedback endpoint is connected.</PreviewNote>
      </Panel>
    </>
  );
}

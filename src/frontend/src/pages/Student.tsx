import { useEffect, useState } from "react";
import { Link, Navigate, useLocation } from "react-router";
import { Button } from "@mui/material";
import { ArrowRight, Check, Sparkles } from "lucide-react";
import {
  CourseArt,
  EmptyState,
  PageHeading,
  PrimaryLink,
  Stat,
} from "../components/ui";
import { useAuth } from "../auth/AuthContext";
import { useCompanion } from "../components/StudyCompanion";
import { ApiError } from "../services/client";
import {
  getProgress,
  type Progress as ProgressData,
} from "../services/progress";
import { progressStatDetail } from "../services/progressMessages";
import Lesson from "./Lesson";
import Materials from "./Materials";
import Practice from "./Practice";
import Progress from "./Progress";

type StatsLoad =
  | { state: "loading" }
  | { state: "ready"; data: ProgressData }
  | { state: "error"; error: ApiError };

/** The three Overview stats, all read from the one progress response. */
function OverviewStats() {
  const demoMode = useAuth().status === "anonymous";
  const [load, setLoad] = useState<StatsLoad>({ state: "loading" });
  useEffect(() => {
    let current = true;
    getProgress().then(
      (data) => current && setLoad({ state: "ready", data }),
      (error) =>
        current &&
        setLoad({
          state: "error",
          error: error instanceof ApiError ? error : new ApiError(0, "network"),
        }),
    );
    return () => {
      current = false;
    };
  }, []);
  const none = { value: "–", detail: "" };
  let lessons = { value: "…", detail: "Loading…" };
  let practice = lessons;
  let topics = lessons;
  if (load.state === "error") {
    const detail = progressStatDetail(load.error, demoMode);
    lessons = practice = topics = { ...none, detail };
  } else if (load.state === "ready") {
    const { totals } = load.data.lessons;
    const { sets, average_latest_percent: average } = load.data.practice;
    const items = load.data.topics.items;
    lessons = {
      value: `${totals.completed_count} / ${totals.lesson_count}`,
      detail: `${totals.completed_count} of ${totals.lesson_count} lessons`,
    };
    practice =
      average === null
        ? { ...none, detail: "No practice submitted yet" }
        : {
            value: `${average}%`,
            detail: `Average of your latest score on each practice set (${sets.length} ${sets.length === 1 ? "set" : "sets"})`,
          };
    topics = {
      value: String(items.filter((i) => i.status === "needs_practice").length),
      detail:
        items.length === 0
          ? "Not enough activity yet"
          : "Based on your latest practice results",
    };
  }
  return (
    <>
      <div className="stats-grid">
        <Stat label="Lessons completed" icon="book" {...lessons} />
        <Stat
          label="Practice average"
          icon="code"
          tone="purple"
          {...practice}
        />
        <Stat
          label="Topics to revise"
          icon="overview"
          tone="green"
          {...topics}
        />
      </div>
      <Link className="text-link" to="/student/progress">
        View full progress
        <ArrowRight size={15} />
      </Link>
    </>
  );
}

function Overview() {
  const { setOpen } = useCompanion();
  return (
    <>
      <PageHeading
        eyebrow="YOUR LEARNING JOURNEY"
        title="A little progress, every day."
        description="Welcome back, Alex. Let’s make room for something new."
      />
      <div className="student-hero">
        <div className="hero-copy">
          <span className="hero-kicker">
            <span /> YOUR NEXT CHAPTER
          </span>
          <h2>
            Good code starts
            <br />
            with clear thinking.
          </h2>
          <p>
            Pick up where you left off. A few thoughtful
            <br className="desktop-break" /> minutes today can make all the
            difference.
          </p>
          <PrimaryLink to="/student/materials">Continue learning</PrimaryLink>
        </div>
        <div className="hero-art">
          <CourseArt large />
          <div className="hero-art-label">
            <span className="icon-box green">
              <Check size={16} />
            </span>
            Clarity is a superpower.
          </div>
        </div>
      </div>
      <OverviewStats />
      <div className="companion-strip">
        <span className="icon-box purple">
          <Sparkles size={23} />
        </span>
        <div>
          <h3>A question is a great place to start.</h3>
          <p>Get a thoughtful hint from your AI study companion.</p>
        </div>
        <Button
          onClick={() => setOpen(true)}
          endIcon={<ArrowRight size={16} />}
        >
          Let’s think it through
        </Button>
      </div>
    </>
  );
}
function LegacyAssistant() {
  const { setOpen } = useCompanion();
  useEffect(() => {
    setOpen(true);
  }, [setOpen]);
  return <Navigate to="/student/overview" replace />;
}
export default function Student() {
  const path = useLocation().pathname.split("/");
  switch (path[2]) {
    case "overview":
      return <Overview />;
    case "materials":
      return path[3] ? <Lesson key={path[3]} id={path[3]} /> : <Materials />;
    case "practice":
      return <Practice />;
    case "progress":
      return <Progress />;
    case "assistant":
      return <LegacyAssistant />;
    default:
      return (
        <EmptyState title="This page isn’t here">
          <Link to="/student/overview">Back to your overview</Link>
        </EmptyState>
      );
  }
}

import { useEffect, useState } from "react";
import { Link, Navigate, useLocation } from "react-router";
import { Button } from "@mui/material";
import { ArrowRight, Check, Flame, Sparkles } from "lucide-react";
import {
  CourseArt,
  EmptyState,
  PageHeading,
  Panel,
  PrimaryLink,
  SectionHeading,
  Stat,
  Tag,
} from "../components/ui";
import { weeklyActivity } from "../data";
import { useAuth } from "../auth/AuthContext";
import { isSignInNeeded } from "../auth/SignInNotice";
import { useCompanion } from "../components/StudyCompanion";
import { listCourses } from "../services/lessons";
import Lesson from "./Lesson";
import Materials from "./Materials";
import Practice from "./Practice";

type Totals = { lesson_count: number; completed_count: number };

/** The "Lessons completed" stat, read from the server totals. */
function LessonsCompletedStat() {
  const demoMode = useAuth().status === "anonymous";
  const [totals, setTotals] = useState<
    Totals | "loading" | "unauthenticated" | "failed"
  >("loading");
  useEffect(() => {
    let current = true;
    listCourses().then(
      (result) => current && setTotals(result.totals),
      (error) =>
        current &&
        setTotals(isSignInNeeded(error) ? "unauthenticated" : "failed"),
    );
    return () => {
      current = false;
    };
  }, []);
  // Decided at render so a change of session state never repeats the request.
  const text =
    totals === "loading"
      ? { value: "…", detail: "Loading…" }
      : totals === "unauthenticated" && demoMode
        ? { value: "–", detail: "Sign in to see your progress" }
        : totals === "failed" || totals === "unauthenticated"
          ? {
              value: "–",
              detail: "Unavailable. Open Study materials to try again.",
            }
          : {
              value: `${totals.completed_count} / ${totals.lesson_count}`,
              detail: `${totals.completed_count} of ${totals.lesson_count} lessons`,
            };
  return <Stat label="Lessons completed" icon="book" {...text} />;
}

function Overview() {
  const { setOpen } = useCompanion();
  return (
    <>
      <PageHeading
        eyebrow="YOUR LEARNING JOURNEY"
        title="A little progress, every day."
        description="Welcome back, Alex. Let’s make room for something new."
        action={
          <span className="streak">
            <Flame size={16} /> 4-day learning streak
          </span>
        }
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
      <div className="stats-grid">
        <LessonsCompletedStat />
        <Stat
          label="Practice average"
          value="82%"
          detail="↑ 8% from last week · Sample"
          icon="code"
          tone="purple"
        />
        <Stat
          label="Time well spent"
          value="2.4 hrs"
          detail="Learning this week · Sample"
          icon="usage"
          tone="green"
        />
      </div>
      <div className="dashboard-columns">
        <div>
          <SectionHeading title="Your learning rhythm" />
          <Panel className="rhythm-panel">
            <div className="rhythm-top">
              <span>This week</span>
              <Tag tone="green">Looking good</Tag>
            </div>
            <div
              className="bar-chart"
              role="img"
              aria-label="Sample learning activity over seven days"
            >
              {weeklyActivity.map((height, i) => (
                <div key={i}>
                  <div
                    className={`chart-bar ${i === 5 ? "highlight" : ""}`}
                    style={{ height: `${height}%` }}
                  />
                  <span>{["M", "T", "W", "T", "F", "S", "S"][i]}</span>
                </div>
              ))}
            </div>
            <p className="rhythm-note">
              <span className="dot green-dot" /> Showing up is the hardest part.
              You’re doing it.
            </p>
            <small className="muted">Illustrative activity · Sample data</small>
          </Panel>
        </div>
      </div>
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

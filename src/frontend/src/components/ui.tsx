import type { ReactNode } from "react";
import { Link } from "react-router";
import {
  Button,
  Chip,
  LinearProgress,
  Paper,
  Tooltip,
  IconButton,
} from "@mui/material";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  Code2,
  FileText,
  Inbox,
  LayoutDashboard,
  Moon,
  Send,
  ShieldCheck,
  Sparkles,
  Sun,
  Users,
  Activity,
  ClipboardCheck,
} from "lucide-react";

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const icons = {
    overview: LayoutDashboard,
    book: BookOpen,
    code: Code2,
    sparkles: Sparkles,
    inbox: Inbox,
    review: ClipboardCheck,
    forms: FileText,
    people: Users,
    usage: Activity,
    shield: ShieldCheck,
    send: Send,
  };
  const Component = icons[name as keyof typeof icons] || BookOpen;
  return <Component size={size} strokeWidth={1.8} aria-hidden="true" />;
}
export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/login" className="brand" aria-label="learnSWE home">
      <span className="brand-mark">
        <Code2 size={24} />
      </span>
      {!compact && (
        <span>
          learn<span className="brand-light">SWE</span>
          <span className="brand-dot">.</span>
        </span>
      )}
    </Link>
  );
}
export function ThemeToggle({
  dark,
  toggle,
}: {
  dark: boolean;
  toggle: () => void;
}) {
  return (
    <Tooltip title={dark ? "Light mode" : "Dark mode"}>
      <IconButton
        onClick={toggle}
        aria-label={`Switch to ${dark ? "light" : "dark"} mode`}
      >
        {dark ? <Sun size={19} /> : <Moon size={19} />}
      </IconButton>
    </Tooltip>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <Paper variant="outlined" className={`panel ${className}`}>
      {children}
    </Paper>
  );
}
export function SectionHeading({
  title,
  link,
  to,
}: {
  title: string;
  link?: string;
  to?: string;
}) {
  return (
    <div className="section-heading">
      <h2>{title}</h2>
      {link && to && (
        <Link className="text-link" to={to}>
          {link}
          <ArrowRight size={15} />
        </Link>
      )}
    </div>
  );
}
export function Stat({
  label,
  value,
  detail,
  icon,
  tone = "blue",
}: {
  label: string;
  value: string;
  detail: string;
  icon: string;
  tone?: string;
}) {
  return (
    <Panel className="stat">
      <div className="stat-top">
        <span>{label}</span>
        <span className={`icon-box ${tone}`}>
          <Icon name={icon} size={18} />
        </span>
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </Panel>
  );
}
export function Tag({
  children,
  tone = "blue",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <Chip size="small" label={children} className={`tag ${tone}`} />;
}
export function Progress({ value, label }: { value: number; label: string }) {
  return (
    <div className="progress">
      <div>
        <span>{label}</span>
        <strong>{value}%</strong>
      </div>
      <LinearProgress variant="determinate" value={value} aria-label={label} />
    </div>
  );
}
export function PreviewNote({
  children = "This is a local preview. No changes are saved or sent.",
}: {
  children?: ReactNode;
}) {
  return (
    <div className="preview-note">
      <ShieldCheck size={15} />
      <span>{children}</span>
    </div>
  );
}
export function PrimaryLink({
  to,
  children,
}: {
  to: string;
  children: ReactNode;
}) {
  return (
    <Button
      variant="contained"
      component={Link}
      to={to}
      endIcon={<ArrowRight size={16} />}
    >
      {children}
    </Button>
  );
}
export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="icon-box blue">
        <Check size={24} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function CourseArt({
  tone = "blue",
  large = false,
}: {
  tone?: string;
  large?: boolean;
}) {
  return (
    <div
      className={`course-art ${tone} ${large ? "large" : ""}`}
      aria-hidden="true"
    >
      <div className="art-grid" />
      <div className="code-window">
        <div className="window-dots">
          <i />
          <i />
          <i />
        </div>
        <div className="code-line long" />
        <div className="code-line medium" />
        <div className="code-line short" />
        <div className="code-line medium" />
      </div>
      <span className="floating-code">
        <Code2 size={large ? 38 : 24} />
      </span>
      <span className="art-star">✦</span>
    </div>
  );
}
export function ArrowBadge() {
  return (
    <span className="arrow-badge">
      <ArrowUpRight size={18} />
    </span>
  );
}

import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import {
  Avatar,
  Button,
  Drawer,
  IconButton,
  MenuItem,
  Select,
  Tooltip,
} from "@mui/material";
import {
  ArrowUpRight,
  ChevronDown,
  LogOut,
  Menu,
  Sparkles,
  X,
} from "lucide-react";
import { Brand, Icon, ThemeToggle } from "./ui";
import { navigation, names, roles, type Role } from "../data";
import { useDemo } from "../state";

function Health() {
  const [status, setStatus] = useState("Checking backend");
  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    fetch("/api/health", { signal: controller.signal })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok || data.status !== "ok")
          throw new Error("Unavailable");
        setStatus("Backend connected");
      })
      .catch(() => {
        if (!cancelled) setStatus("Backend unavailable");
      })
      .finally(() => clearTimeout(timeout));
    let cancelled = false;
    return () => {
      cancelled = true;
      clearTimeout(timeout);
      controller.abort();
    };
  }, []);
  return (
    <span
      className={`health ${status === "Backend connected" ? "connected" : ""}`}
      role="status"
    >
      <i />
      {status}
    </span>
  );
}
export default function Shell({
  role,
  dark,
  toggle,
}: {
  role: Role;
  dark: boolean;
  toggle: () => void;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const { messages } = useDemo();
  const unread = messages[role].filter((message) => message.unread).length;
  const section = location.pathname.split("/")[2];
  const current =
    navigation[role].find((item) => item.path === section)?.label ||
    (section === "feedback" ? "Feedback" : "Workspace");
  const sidebar = (
    <>
      <div className="sidebar-brand">
        <Brand />
        <IconButton
          className="mobile-close"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        >
          <X size={20} />
        </IconButton>
      </div>
      <div className="workspace-label">
        {role === "student"
          ? "YOUR LEARNING SPACE"
          : role === "teacher"
            ? "YOUR TEACHING SPACE"
            : "YOUR ADMIN SPACE"}
      </div>
      <nav aria-label={`${role} navigation`}>
        {navigation[role].map((item) => (
          <NavLink
            key={item.path}
            to={`/${role}/${item.path}`}
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            onClick={() => setOpen(false)}
          >
            <Icon name={item.icon} />
            <span>{item.label}</span>
            {item.path === "inbox" && unread > 0 && (
              <span className="nav-count">{unread}</span>
            )}
            {item.path === "generate" && <span className="nav-ai">AI</span>}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-tip">
          <span className="tip-sparkle">
            <Sparkles size={18} />
          </span>
          <strong>
            {role === "student"
              ? "A little help goes a long way."
              : role === "teacher"
                ? "Your ideas. A head start."
                : "Listen. Learn. Improve."}
          </strong>
          <p>
            {role === "student"
              ? "Your study companion is here when you need a nudge."
              : role === "teacher"
                ? "Turn your materials into meaningful learning."
                : "Turn feedback into a better experience."}
          </p>
          <Link
            to={
              role === "student"
                ? "/student/assistant"
                : role === "teacher"
                  ? "/teacher/generate"
                  : "/admin/responses"
            }
          >
            Explore{" "}
            {role === "admin"
              ? "insights"
              : role === "teacher"
                ? "the studio"
                : "AI companion"}
            <ArrowUpRight size={14} />
          </Link>
        </div>
        <div className="sidebar-user">
          <Avatar
            sx={{
              width: 36,
              height: 36,
              bgcolor: dark ? "#273c58" : "#e6edfc",
              color: "primary.main",
              fontSize: 13,
            }}
          >
            {names[role][0]}
            {role === "student" ? "L" : "W"}
          </Avatar>
          <div>
            <strong>
              {names[role]} {role === "student" ? "Lee" : "Wong"}
            </strong>
            <small>
              {role === "admin"
                ? "Administrator"
                : `${role[0].toUpperCase()}${role.slice(1)} account`}
            </small>
          </div>
          <Tooltip title="Back to login preview">
            <IconButton
              component={Link}
              to="/login"
              aria-label="Back to login preview"
            >
              <LogOut size={16} />
            </IconButton>
          </Tooltip>
        </div>
      </div>
    </>
  );
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className="sidebar">{sidebar}</aside>
      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        slotProps={{ paper: { className: "mobile-sidebar" } }}
      >
        {sidebar}
      </Drawer>
      <div className="app-main">
        <header className="topbar">
          <div className="breadcrumb">
            <IconButton
              className="menu-toggle"
              aria-label="Open navigation"
              onClick={() => setOpen(true)}
            >
              <Menu size={21} />
            </IconButton>
            <span className="breadcrumb-root">Workspace</span>
            <span className="breadcrumb-slash">/</span>
            <strong>{current}</strong>
          </div>
          <div className="topbar-actions">
            <span className="demo-pill">
              <span /> Demo · Sample data
            </span>
            <div className="role-select">
              <Select
                value={role}
                onChange={(event) =>
                  navigate(`/${event.target.value}/overview`)
                }
                size="small"
                inputProps={{ "aria-label": "Demo role" }}
                IconComponent={ChevronDown}
              >
                {roles.map((item) => (
                  <MenuItem key={item} value={item}>
                    {item[0].toUpperCase() + item.slice(1)}
                  </MenuItem>
                ))}
              </Select>
            </div>
            <ThemeToggle dark={dark} toggle={toggle} />
          </div>
        </header>
        <main id="main-content" className="workspace" key={role}>
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>Small steps. Meaningful progress.</span>
          <Health />
          <Button component={Link} to="/login" size="small">
            Login preview
          </Button>
        </footer>
      </div>
    </div>
  );
}

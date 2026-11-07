import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import {
  Avatar,
  Button,
  Alert,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
import { useAuth } from "../auth/AuthContext";
import StudyCompanion, { CompanionTrigger } from "./StudyCompanion";
import { useInboxUnread } from "../hooks/useInboxUnread";

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
  const { status, user, logout } = useAuth();
  const inboxUnread = useInboxUnread();
  const [logoutFailed, setLogoutFailed] = useState(false);
  const [logoutConfirm, setLogoutConfirm] = useState(false);
  const [logoutPending, setLogoutPending] = useState(false);
  const [dismissedTipFor, setDismissedTipFor] = useState<string | null>(null);
  const tipOwner = `${role}:${user?.id ?? "demo"}`;
  async function confirmLogout() {
    if (logoutPending) return;
    setLogoutPending(true);
    setLogoutFailed(false);
    try {
      await logout();
      setLogoutConfirm(false);
    } catch {
      setLogoutFailed(true);
    } finally {
      setLogoutPending(false);
    }
  }
  // Anonymous visitors are in demo mode (sample data, no session); signed-in users are real.
  const demoMode = status !== "authenticated";
  const displayName = user?.display_name ?? "";
  const unread = demoMode
    ? messages[role].filter((message) => message.unread).length
    : (inboxUnread ?? 0);
  const section = location.pathname.split("/")[2];
  const liveUsage = !demoMode && role === "admin" && section === "ai-usage";
  const liveFeedback =
    !demoMode &&
    (section === "feedback" ||
      (role === "admin" && section === "announcements") ||
      ((role === "student" || role === "teacher") && section === "inbox"));
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
        {navigation[role].map((original) => {
          const item =
            !demoMode && role === "admin" && original.path === "forms"
              ? { ...original, path: "feedback" }
              : !demoMode &&
                  role === "admin" &&
                  original.path === "announcements"
                ? { ...original, path: "announcements/new" }
                : original;
          return (
            <NavLink
              key={item.path}
              to={`/${role}/${item.path}`}
              className={({ isActive }) =>
                `nav-item ${isActive ? "active" : ""}`
              }
              onClick={() => setOpen(false)}
              aria-label={item.path === "inbox" ? "Inbox" : undefined}
              aria-description={
                item.path === "inbox" && unread > 0
                  ? `${unread} unread inbox items`
                  : undefined
              }
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.path === "inbox" && unread > 0 && (
                <span
                  className="nav-count"
                  role="status"
                  aria-label={`${unread} unread inbox items`}
                  aria-live="polite"
                  aria-atomic="true"
                >
                  {unread > 99 ? "99+" : unread}
                </span>
              )}
              {item.path === "generate" && <span className="nav-ai">AI</span>}
            </NavLink>
          );
        })}
      </nav>
      <div className="sidebar-bottom">
        {dismissedTipFor !== tipOwner && (
          <div className="sidebar-tip">
            <Tooltip title="Dismiss sidebar tip">
              <IconButton
                className="sidebar-tip-dismiss"
                aria-label="Dismiss sidebar tip"
                size="small"
                onClick={() => setDismissedTipFor(tipOwner)}
              >
                <X size={16} />
              </IconButton>
            </Tooltip>
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
            {role === "student" ? (
              <CompanionTrigger
                className="sidebar-companion-trigger"
                onOpen={() => setOpen(false)}
              >
                Open companion
                <ArrowUpRight size={14} />
              </CompanionTrigger>
            ) : (
              <Link
                to={
                  role === "teacher" ? "/teacher/generate" : "/admin/responses"
                }
              >
                Explore {role === "admin" ? "insights" : "the studio"}
                <ArrowUpRight size={14} />
              </Link>
            )}
          </div>
        )}
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
            {demoMode
              ? `${names[role][0]}${role === "student" ? "L" : "W"}`
              : displayName.slice(0, 2).toUpperCase()}
          </Avatar>
          <div>
            <strong>{demoMode ? "Demo (not signed in)" : displayName}</strong>
            <small>
              {role === "admin"
                ? "Administrator"
                : `${role[0].toUpperCase()}${role.slice(1)} account`}
            </small>
          </div>
          {demoMode ? (
            <Tooltip title="Back to login preview">
              <IconButton
                component={Link}
                to="/login"
                aria-label="Back to login preview"
              >
                <LogOut size={16} />
              </IconButton>
            </Tooltip>
          ) : (
            <Button
              size="small"
              onClick={() => {
                setLogoutFailed(false);
                setLogoutConfirm(true);
              }}
              startIcon={<LogOut size={16} />}
            >
              Log out
            </Button>
          )}
          {logoutFailed && !logoutConfirm && (
            <span role="alert">Could not log out. Try again.</span>
          )}
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
            {!liveUsage && !liveFeedback && (
              <span className="demo-pill">
                <span /> Demo · Sample data
              </span>
            )}
            {demoMode && (
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
            )}
            <ThemeToggle dark={dark} toggle={toggle} />
          </div>
        </header>
        <main id="main-content" className="workspace" key={role}>
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>Small steps. Meaningful progress.</span>
          <Health />
          {demoMode && (
            <Button component={Link} to="/login" size="small">
              Login preview
            </Button>
          )}
        </footer>
        {role === "student" && <StudyCompanion />}
      </div>
      <Dialog
        open={logoutConfirm && !demoMode}
        aria-labelledby="logout-confirm-title"
        aria-describedby="logout-confirm-description"
        onClose={() => {
          if (!logoutPending) setLogoutConfirm(false);
        }}
      >
        <DialogTitle id="logout-confirm-title">Confirm logout</DialogTitle>
        <DialogContent>
          <p id="logout-confirm-description">
            Are you sure you want to log out?
          </p>
          {logoutPending && <p role="status">Logging out...</p>}
          {logoutFailed && (
            <Alert severity="error">Could not log out. Try again.</Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            disabled={logoutPending}
            onClick={() => setLogoutConfirm(false)}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            disabled={logoutPending}
            onClick={() => void confirmLogout()}
          >
            Log out
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}

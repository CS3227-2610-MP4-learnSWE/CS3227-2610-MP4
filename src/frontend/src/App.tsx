import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Navigate, Route, Routes, useLocation } from "react-router";
import {
  Alert,
  createTheme,
  CssBaseline,
  Snackbar,
  ThemeProvider,
  useMediaQuery,
} from "@mui/material";
import { DemoProvider } from "./state";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireRole, RootRedirect } from "./auth/RequireRole";
import Login from "./pages/Login";
import { CompanionProvider } from "./components/StudyCompanion";
import Shell from "./components/Shell";
import Student from "./pages/Student";
import { PracticeProvider } from "./practice/PracticeContext";
import InboxPage, { FeedbackForm } from "./pages/Inbox";
import FeedbackInbox from "./pages/FeedbackInbox";
import RecipientFeedback from "./pages/RecipientFeedback";

// Loaded on demand so the student pages never download the teacher demo data.
const Teacher = lazy(() => import("./pages/Teacher"));
const Admin = lazy(() => import("./pages/Admin"));
const AdminFeedbackHub = lazy(() => import("./pages/AdminFeedbackHub"));
const AdminAnalytics = lazy(() => import("./pages/AdminAnalytics"));

function Inbox({ role }: { role: "student" | "teacher" }) {
  const { status } = useAuth();
  return status === "authenticated" ? (
    <FeedbackInbox />
  ) : (
    <InboxPage role={role} />
  );
}

function TeacherFeedbackIndex({
  notify,
}: {
  notify: (message?: string) => void;
}) {
  const { status } = useAuth();
  return status === "authenticated" ? (
    <Navigate to="/teacher/inbox" replace />
  ) : (
    <FeedbackForm notify={notify} />
  );
}

/** True once the user was signed in during this visit, so a mid-visit expiry is left to AuthContext's redirect. */
function useWasAuthenticated() {
  const { status } = useAuth();
  const was = useRef(false);
  if (status === "authenticated") was.current = true;
  return was.current;
}

function LiveFeedback() {
  const { status } = useAuth();
  const was = useWasAuthenticated();
  if (status === "anonymous" && !was) return <Navigate to="/login" replace />;
  if (status !== "authenticated") return null;
  return <RecipientFeedback />;
}

/**
 * Lazy pages. Role checks are RequireRole's; a session that expires while the page is open is left to
 * AuthContext (it navigates with the expiry notice). Only a visit that starts anonymous is sent to sign in here.
 */
function LiveAnalysis({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const was = useWasAuthenticated();
  if (status === "anonymous" && !was) return <Navigate to="/login" replace />;
  if (status !== "authenticated") return null;
  return (
    <Suspense fallback={<p role="status">Loading�</p>}>{children}</Suspense>
  );
}

const HUB = "/admin/feedback-hub";

/**
 * An old admin address sent to its hub page. The target is built from the raw (still encoded) path segments
 * after `/admin/`, so an encoded "/" in an id or label never becomes a path separator; query and hash are kept.
 */
function HubRedirect({ to }: { to: (segments: string[]) => string }) {
  const { pathname, search, hash } = useLocation();
  const segments = pathname.replace(/\/$/, "").split("/").slice(2);
  return <Navigate to={`${to(segments)}${search}${hash}`} replace />;
}

export default function App() {
  const prefersDark = useMediaQuery("(prefers-color-scheme: dark)");
  const [mode, setMode] = useState<"light" | "dark" | null>(null);
  const dark = (mode || (prefersDark ? "dark" : "light")) === "dark";
  const [notice, setNotice] = useState("");
  const notify = (
    message = "Not available in this preview. No changes were saved or sent.",
  ) => setNotice(message);
  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode: dark ? "dark" : "light",
          primary: { main: dark ? "#8aafff" : "#2463eb" },
          background: {
            default: dark ? "#10141d" : "#f7f8fb",
            paper: dark ? "#191f2b" : "#fff",
          },
          text: {
            primary: dark ? "#eef2fb" : "#1b263b",
            secondary: dark ? "#a0acc1" : "#69758a",
          },
          divider: dark ? "#2c3546" : "#e9edf4",
        },
        typography: {
          fontFamily: '"Inter", "Segoe UI", system-ui, sans-serif',
          button: {
            textTransform: "none",
            fontWeight: 600,
            letterSpacing: "-0.01em",
          },
        },
        shape: { borderRadius: 12 },
        components: {
          MuiButton: {
            defaultProps: { disableElevation: true },
            styleOverrides: { root: { borderRadius: 9, padding: "10px 18px" } },
          },
          MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
          MuiTextField: { defaultProps: { size: "small", fullWidth: true } },
          MuiChip: {
            styleOverrides: { root: { fontWeight: 600, fontSize: 11 } },
          },
        },
      }),
    [dark],
  );
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    document.documentElement.style.colorScheme = dark ? "dark" : "light";
  }, [dark]);
  const toggle = () => setMode(dark ? "light" : "dark");
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <DemoProvider>
          <Routes>
            <Route
              path="/login"
              element={<Login dark={dark} toggle={toggle} />}
            />
            <Route
              path="/student"
              element={
                <RequireRole role="student">
                  <PracticeProvider>
                    <CompanionProvider>
                      <Shell role="student" dark={dark} toggle={toggle} />
                    </CompanionProvider>
                  </PracticeProvider>
                </RequireRole>
              }
            >
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="inbox" element={<Inbox role="student" />} />
              <Route path="feedback/:formId" element={<LiveFeedback />} />
              <Route
                path="feedback"
                element={<FeedbackForm notify={notify} />}
              />
              <Route path="*" element={<Student />} />
            </Route>
            <Route
              path="/teacher"
              element={
                <RequireRole role="teacher">
                  <Shell role="teacher" dark={dark} toggle={toggle} />
                </RequireRole>
              }
            >
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="inbox" element={<Inbox role="teacher" />} />
              <Route path="feedback/:formId" element={<LiveFeedback />} />
              <Route
                path="feedback"
                element={<TeacherFeedbackIndex notify={notify} />}
              />
              <Route
                path="*"
                element={
                  <Suspense fallback={<p role="status">Loading…</p>}>
                    <Teacher notify={notify} />
                  </Suspense>
                }
              />
            </Route>
            <Route
              path="/admin"
              element={
                <RequireRole role="admin">
                  <Shell role="admin" dark={dark} toggle={toggle} />
                </RequireRole>
              }
            >
              <Route index element={<Navigate to="analytics" replace />} />
              <Route
                path="overview"
                element={<Navigate to="/admin/analytics" replace />}
              />
              <Route
                path="feedback-hub/*"
                element={
                  <LiveAnalysis>
                    <AdminFeedbackHub />
                  </LiveAnalysis>
                }
              />
              <Route
                path="feedback/analysis"
                element={<HubRedirect to={() => `${HUB}/analysis`} />}
              />
              <Route
                path="feedback/analysis/:analysisId"
                element={<HubRedirect to={(s) => `${HUB}/analysis/${s[2]}`} />}
              />
              <Route
                path="feedback/analysis/:analysisId/responses/:label"
                element={
                  <HubRedirect
                    to={(s) => `${HUB}/analysis/${s[2]}/responses/${s[4]}`}
                  />
                }
              />
              <Route
                path="feedback/new"
                element={<HubRedirect to={() => `${HUB}/forms/new`} />}
              />
              <Route
                path="feedback/:formId"
                element={<HubRedirect to={(s) => `${HUB}/forms/${s[1]}`} />}
              />
              <Route
                path="feedback/:formId/edit"
                element={
                  <HubRedirect to={(s) => `${HUB}/forms/${s[1]}/edit`} />
                }
              />
              <Route
                path="feedback/:formId/responses"
                element={<HubRedirect to={(s) => `${HUB}/responses/${s[1]}`} />}
              />
              <Route
                path="feedback/:formId/responses/:responseId"
                element={
                  <HubRedirect to={(s) => `${HUB}/responses/${s[1]}/${s[3]}`} />
                }
              />
              <Route
                path="feedback/:formId/responses/:responseId/reply"
                element={
                  <HubRedirect
                    to={(s) => `${HUB}/follow-up/reply/${s[1]}/${s[3]}`}
                  />
                }
              />
              <Route
                path="feedback"
                element={<HubRedirect to={() => `${HUB}/forms`} />}
              />
              <Route
                path="responses"
                element={<HubRedirect to={() => `${HUB}/forms`} />}
              />
              <Route
                path="announcements"
                element={<HubRedirect to={() => `${HUB}/follow-up`} />}
              />
              <Route
                path="announcements/new"
                element={<HubRedirect to={() => `${HUB}/follow-up`} />}
              />
              <Route
                path="analytics"
                element={
                  <LiveAnalysis>
                    <AdminAnalytics />
                  </LiveAnalysis>
                }
              />
              <Route
                path="ai-usage"
                element={<Navigate to="/admin/analytics" replace />}
              />
              <Route
                path="*"
                element={
                  <Suspense fallback={<p role="status">Loading…</p>}>
                    <Admin />
                  </Suspense>
                }
              />
            </Route>
            <Route path="*" element={<RootRedirect />} />
          </Routes>
        </DemoProvider>
      </AuthProvider>
      <Snackbar
        open={!!notice}
        autoHideDuration={5000}
        onClose={(_, reason) => {
          if (reason !== "clickaway") setNotice("");
        }}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert role="status" severity="info" onClose={() => setNotice("")}>
          {notice}
        </Alert>
      </Snackbar>
    </ThemeProvider>
  );
}

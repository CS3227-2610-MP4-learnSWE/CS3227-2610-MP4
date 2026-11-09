import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Navigate, Route, Routes } from "react-router";
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
import AdminFeedback from "./pages/AdminFeedback";
import AdminMessaging from "./pages/AdminMessaging";

// Loaded on demand so the student pages never download the teacher demo data.
const Teacher = lazy(() => import("./pages/Teacher"));
const Admin = lazy(() => import("./pages/Admin"));
const AdminFeedbackAnalysis = lazy(
  () => import("./pages/AdminFeedbackAnalysis"),
);
const AdminFeedbackAnalysisResult = lazy(
  () => import("./pages/AdminFeedbackAnalysisResult"),
);
const AdminFeedbackAnalysisEvidence = lazy(
  () => import("./pages/AdminFeedbackAnalysisEvidence"),
);

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

function LiveFeedback({ admin = false }: { admin?: boolean }) {
  const { status } = useAuth();
  if (status !== "authenticated") return <Navigate to="/login" replace />;
  return admin ? <AdminFeedback /> : <RecipientFeedback />;
}

function LiveAnalysis({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  return status === "authenticated" ? (
    <Suspense fallback={<p role="status">Loading�</p>}>{children}</Suspense>
  ) : (
    <Navigate to="/login" replace />
  );
}

function Announcements() {
  const { status } = useAuth();
  return status === "authenticated" ? (
    <AdminMessaging />
  ) : (
    <Suspense fallback={<p role="status">Loading…</p>}>
      <Admin />
    </Suspense>
  );
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
              <Route index element={<Navigate to="overview" replace />} />
              <Route
                path="feedback/analysis"
                element={
                  <LiveAnalysis>
                    <AdminFeedbackAnalysis />
                  </LiveAnalysis>
                }
              />
              <Route
                path="feedback/analysis/:analysisId"
                element={
                  <LiveAnalysis>
                    <AdminFeedbackAnalysisResult />
                  </LiveAnalysis>
                }
              />
              <Route
                path="feedback/analysis/:analysisId/responses/:label"
                element={
                  <LiveAnalysis>
                    <AdminFeedbackAnalysisEvidence />
                  </LiveAnalysis>
                }
              />
              <Route path="feedback/*" element={<LiveFeedback admin />} />
              <Route path="announcements" element={<Announcements />} />
              <Route path="announcements/new" element={<AdminMessaging />} />
              <Route
                path="feedback/:formId/responses/:responseId/reply"
                element={<AdminMessaging />}
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

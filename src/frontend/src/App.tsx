import { lazy, Suspense, useEffect, useMemo, useState } from "react";
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
import Login from "./pages/Login";
import { CompanionProvider } from "./components/StudyCompanion";
import Shell from "./components/Shell";
import Student from "./pages/Student";
import { PracticeProvider } from "./practice/PracticeContext";
import InboxPage, { FeedbackForm } from "./pages/Inbox";

// Loaded on demand so the student pages never download the teacher demo data.
const Teacher = lazy(() => import("./pages/Teacher"));
const Admin = lazy(() => import("./pages/Admin"));

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
      <DemoProvider>
        <Routes>
          <Route
            path="/login"
            element={<Login dark={dark} toggle={toggle} notify={notify} />}
          />
          <Route
            path="/student"
            element={
              <PracticeProvider>
                <CompanionProvider>
                  <Shell role="student" dark={dark} toggle={toggle} />
                </CompanionProvider>
              </PracticeProvider>
            }
          >
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="inbox" element={<InboxPage role="student" />} />
            <Route path="feedback" element={<FeedbackForm notify={notify} />} />
            <Route path="*" element={<Student />} />
          </Route>
          <Route
            path="/teacher"
            element={<Shell role="teacher" dark={dark} toggle={toggle} />}
          >
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="inbox" element={<InboxPage role="teacher" />} />
            <Route path="feedback" element={<FeedbackForm notify={notify} />} />
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
            element={<Shell role="admin" dark={dark} toggle={toggle} />}
          >
            <Route index element={<Navigate to="overview" replace />} />
            <Route
              path="*"
              element={
                <Suspense fallback={<p role="status">Loading…</p>}>
                  <Admin notify={notify} />
                </Suspense>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </DemoProvider>
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

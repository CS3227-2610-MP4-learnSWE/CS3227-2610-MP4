import { Link } from "react-router";
import { Alert } from "@mui/material";
import { ApiError } from "../services/client";

/** Shown in demo mode when a live (session-only) feature answers 401. */
export default function SignInNotice({
  message = "Sign in to use live practice and the study companion",
}: {
  message?: string;
}) {
  return (
    <Alert severity="info" sx={{ my: 2 }}>
      {message} <Link to="/login">Go to sign in</Link>
    </Alert>
  );
}

export const isSignInNeeded = (error: unknown) =>
  error instanceof ApiError &&
  error.status === 401 &&
  error.code === "unauthenticated";

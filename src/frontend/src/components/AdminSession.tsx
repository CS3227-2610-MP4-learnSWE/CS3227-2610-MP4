import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import SignInNotice from "../auth/SignInNotice";

/** Unmount all account data and passwords on logout or account switching. */
export default function AdminSession({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  if (status === "loading") return <p role="status">Loading accounts...</p>;
  if (status !== "authenticated")
    return <SignInNotice message="Sign in to manage accounts and courses." />;
  return children;
}

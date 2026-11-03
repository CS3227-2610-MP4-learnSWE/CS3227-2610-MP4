import type { ReactNode } from "react";
import { Navigate } from "react-router";
import type { Role } from "../data";
import { useAuth } from "./AuthContext";
import { demoAccessEnabled } from "./demoAccess";

export const homePath = (role: Role) => `/${role}/overview`;

/** UX guard only: the server enforces access on every API call. */
export function RequireRole({
  role,
  children,
}: {
  role: Role;
  children: ReactNode;
}) {
  const { status, user } = useAuth();
  if (status === "loading") return <p role="status">Checking your session…</p>;
  if (status === "authenticated" && user)
    return user.role === role ? (
      children
    ) : (
      <Navigate to={homePath(user.role)} replace />
    );
  // Anonymous: demo mode (sample data, no session) while demo access is enabled.
  return demoAccessEnabled() ? children : <Navigate to="/login" replace />;
}

/** "/" and unknown paths: signed-in users go home, everyone else to the login page. */
export function RootRedirect() {
  const { status, user } = useAuth();
  if (status === "loading") return <p role="status">Checking your session…</p>;
  return <Navigate to={user ? homePath(user.role) : "/login"} replace />;
}

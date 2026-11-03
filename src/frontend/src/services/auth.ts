import { ApiError, request } from "./client";
import type { Role } from "../data";

export type AuthUser = {
  id: string;
  email: string | null;
  display_name: string;
  role: Role;
};
export type Session = { user: AuthUser; csrf_token: string };

const bad = () => new ApiError(0, "bad_response");
const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

function parseSession(data: unknown): Session {
  const user = isObject(data) ? data.user : null;
  if (
    !isObject(data) ||
    typeof data.csrf_token !== "string" ||
    !isObject(user) ||
    typeof user.id !== "string" ||
    !(user.email === null || typeof user.email === "string") ||
    typeof user.display_name !== "string" ||
    !["student", "teacher", "admin"].includes(user.role as string)
  )
    throw bad();
  return data as Session;
}

let meInFlight: Promise<Session> | null = null;

/** One request at a time: React StrictMode mounts twice in development. */
export function me(): Promise<Session> {
  meInFlight ??= request("GET", "/api/auth/me")
    .then(parseSession)
    .finally(() => {
      meInFlight = null;
    });
  return meInFlight;
}

export async function login(email: string, password: string): Promise<Session> {
  return parseSession(
    await request("POST", "/api/auth/login", { email, password }),
  );
}

/** Always creates a student; the server answers the same for a new and an existing email. */
export async function signup(
  display_name: string,
  email: string,
  password: string,
): Promise<void> {
  await request("POST", "/api/auth/signup", { display_name, email, password });
}

export async function logout(): Promise<void> {
  await request("POST", "/api/auth/logout");
}

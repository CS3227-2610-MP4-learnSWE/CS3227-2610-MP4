import { useCallback, useState, type FormEvent } from "react";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Snackbar,
  TextField,
} from "@mui/material";
import { PageHeading, Panel } from "../components/ui";
import AdminSession from "../components/AdminSession";
import { useAuth } from "../auth/AuthContext";
import { useAdminRead } from "../hooks/useAdminRead";
import * as api from "../services/adminAccess";

function ReadError({ message, retry }: { message: string; retry: () => void }) {
  return message ? (
    <Alert severity="error" action={<Button onClick={retry}>Try again</Button>}>
      {message}
    </Alert>
  ) : null;
}

function CreateAccount({ created }: { created: () => Promise<void> }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [role, setRole] = useState<api.AccountRole>("student");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError("");
    setSuccess(false);
    if (password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await api.createAccount({ display_name: name, email, password, role });
      setName("");
      setEmail("");
      setPassword("");
      setConfirmation("");
      setSuccess(true);
      await created();
    } catch (failure) {
      setError(api.adminError(failure));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel className="admin-access-panel">
      <h2>Create account</h2>
      <p className="muted">
        Each account has one fixed role. Share the initial password privately
        with its owner.
      </p>
      <form
        className="admin-access-form admin-create-form"
        onSubmit={(event) => void submit(event)}
      >
        <TextField
          label="Display name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
          slotProps={{
            htmlInput: { maxLength: 80, "aria-label": "Display name" },
          }}
          disabled={busy}
        />
        <TextField
          label="Email"
          slotProps={{ htmlInput: { "aria-label": "Email" } }}
          type="email"
          autoComplete="off"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
          disabled={busy}
        />
        <TextField
          select
          label="Account role"
          slotProps={{
            select: {
              SelectDisplayProps: {
                "aria-label": "Account role",
                "aria-labelledby": undefined,
              },
            },
          }}
          value={role}
          onChange={(event) => setRole(event.target.value as api.AccountRole)}
          disabled={busy}
        >
          <MenuItem value="student">Student</MenuItem>
          <MenuItem value="teacher">Teacher</MenuItem>
          <MenuItem value="admin">Admin</MenuItem>
        </TextField>
        <TextField
          label="Password"
          helperText="Use 10–128 characters; avoid common passwords and the email address."
          slotProps={{ htmlInput: { "aria-label": "Password" } }}
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          disabled={busy}
        />
        <TextField
          label="Confirm password"
          slotProps={{ htmlInput: { "aria-label": "Confirm password" } }}
          type="password"
          autoComplete="new-password"
          value={confirmation}
          onChange={(event) => setConfirmation(event.target.value)}
          required
          disabled={busy}
        />
        <Button variant="contained" type="submit" disabled={busy}>
          Create account
        </Button>
      </form>
      {busy && <p role="status">Creating account...</p>}
      {error && <Alert severity="error">{error}</Alert>}
      <Snackbar
        open={success}
        autoHideDuration={6000}
        onClose={(_, reason) => {
          if (reason !== "clickaway") setSuccess(false);
        }}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity="success"
          variant="filled"
          role="status"
          onClose={() => setSuccess(false)}
        >
          Account created.
        </Alert>
      </Snackbar>
    </Panel>
  );
}

type ConfirmAction = {
  kind: "disable" | "archive" | "removal";
  course?: api.Course;
};
function AccountDetails({
  id,
  courses,
  refreshAccounts,
  onClose,
}: {
  id: string;
  courses: api.Course[];
  refreshAccounts: () => Promise<void>;
  onClose: () => void;
}) {
  const load = useCallback(() => api.getAccount(id), [id]);
  const detail = useAdminRead(load);
  const [courseId, setCourseId] = useState("");
  const [confirmation, setConfirmation] = useState<ConfirmAction | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const account = detail.data?.account;

  async function change(
    action: "enable" | "disable" | "archive" | "grant" | "removal",
    targetCourse?: api.Course,
  ) {
    if (busy || !account) return;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      if (action === "grant" || action === "removal") {
        const target = action === "grant" ? courseId : targetCourse?.id;
        if (!target) return;
        const result = await (action === "grant"
          ? api.grantCourseAccess(id, target)
          : api.revokeCourseAccess(id, target));
        detail.setData(result);
        setSuccess(
          action === "grant"
            ? "Course access granted."
            : "Course access removed.",
        );
      } else {
        await (action === "archive"
          ? api.archiveAccount(id)
          : api.setAccountStatus(
              id,
              action === "enable" ? "enabled" : "disabled",
            ));
        await Promise.all([detail.reload(), refreshAccounts()]);
        setSuccess(
          action === "archive"
            ? "Account archived."
            : action === "enable"
              ? "Account enabled."
              : "Account disabled.",
        );
      }
      setConfirmation(null);
    } catch (failure) {
      setError(api.adminError(failure));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Dialog
        open
        fullWidth
        maxWidth="sm"
        aria-labelledby="admin-account-details-title"
        onClose={() => {
          if (!busy) onClose();
        }}
        scroll="paper"
        className="admin-dialog"
      >
        <DialogTitle id="admin-account-details-title">
          Account details
        </DialogTitle>
        <DialogContent dividers>
          {detail.loading && <p role="status">Loading account...</p>}
          <ReadError
            message={detail.error}
            retry={() => void detail.reload()}
          />
          {account && (
            <>
              <h3>{account.display_name}</h3>
              <p>{account.email ?? "No email"}</p>
              <p>
                Role: {account.role} · Status: {account.status}
              </p>
              {account.status === "archived" ? (
                <p>This account is permanently archived.</p>
              ) : (
                <div className="admin-access-actions">
                  {account.status === "enabled" ? (
                    <Button
                      disabled={busy}
                      onClick={() => {
                        setError("");
                        setConfirmation({ kind: "disable" });
                      }}
                    >
                      Disable account
                    </Button>
                  ) : (
                    <Button
                      disabled={busy}
                      onClick={() => void change("enable")}
                    >
                      Enable account
                    </Button>
                  )}
                  <Button
                    color="error"
                    disabled={busy}
                    onClick={() => {
                      setError("");
                      setConfirmation({ kind: "archive" });
                    }}
                  >
                    Archive account
                  </Button>
                </div>
              )}
              {account.role === "admin" ? (
                <p>Administrators do not receive course assignments.</p>
              ) : (
                <>
                  <h3>
                    {account.role === "teacher"
                      ? "Teacher management assignments"
                      : "Student enrolments"}
                  </h3>
                  {!detail.data?.courses.length && <p>No course access.</p>}
                  <ul className="admin-course-list">
                    {detail.data?.courses.map((course) => (
                      <li key={course.id}>
                        <span>{course.title}</span>
                        {account.status !== "archived" && (
                          <Button
                            aria-label={`Remove course access ${course.title}`}
                            disabled={busy}
                            onClick={() => {
                              setError("");
                              setConfirmation({ kind: "removal", course });
                            }}
                          >
                            Remove course access
                          </Button>
                        )}
                      </li>
                    ))}
                  </ul>
                  {account.status !== "archived" && (
                    <div className="admin-access-form">
                      <TextField
                        select
                        label="Course"
                        slotProps={{
                          select: {
                            SelectDisplayProps: {
                              "aria-label": "Course",
                              "aria-labelledby": undefined,
                            },
                          },
                        }}
                        value={courseId}
                        disabled={busy}
                        onChange={(event) => setCourseId(event.target.value)}
                      >
                        <MenuItem value="">Select a course</MenuItem>
                        {courses.map((course) => (
                          <MenuItem key={course.id} value={course.id}>
                            {course.title}
                          </MenuItem>
                        ))}
                      </TextField>
                      <Button
                        variant="outlined"
                        disabled={busy || !courseId}
                        onClick={() => void change("grant")}
                      >
                        Grant course access
                      </Button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
          {busy && <p role="status">Saving changes...</p>}
          {error && !confirmation && <Alert severity="error">{error}</Alert>}
          {success && <p role="status">{success}</p>}
        </DialogContent>
        <DialogActions>
          <Button disabled={busy} onClick={onClose}>
            Close account details
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        className="admin-dialog"
        open={!!confirmation}
        onClose={() => {
          if (!busy) setConfirmation(null);
        }}
        aria-labelledby="admin-confirm-title"
      >
        <DialogTitle id="admin-confirm-title">
          {confirmation ? `Confirm ${confirmation.kind}` : "Confirm change"}
        </DialogTitle>
        <DialogContent>
          <p>
            {confirmation?.kind === "archive"
              ? `Permanently archive ${account?.display_name}? Login and course access will be removed. Learning and authorship history will be retained. This cannot be undone.`
              : confirmation?.kind === "disable"
                ? `Disable ${account?.display_name}? All their sessions will end.`
                : `Remove ${account?.display_name}'s access to ${confirmation?.course?.title}? Their history will be retained.`}
          </p>
          {error && <Alert severity="error">{error}</Alert>}
          {busy && <p role="status">Saving changes...</p>}
        </DialogContent>
        <DialogActions>
          <Button disabled={busy} onClick={() => setConfirmation(null)}>
            Cancel
          </Button>
          <Button
            disabled={busy}
            onClick={() => {
              if (confirmation)
                void change(confirmation.kind, confirmation.course);
            }}
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

function AccountsContent() {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState<api.AccountQuery>({
    status: "enabled",
    page: 1,
  });
  const [selected, setSelected] = useState<string | null>(null);
  const load = useCallback(() => api.listAccounts(query), [query]);
  const list = useAdminRead(load);
  const courses = useAdminRead(api.listCourses);
  const page = query.page ?? 1;
  const setFilter = (next: Partial<api.AccountQuery>) =>
    setQuery((current) => ({ ...current, ...next, page: 1 }));
  return (
    <>
      <PageHeading
        title="User and access management"
        description="Create accounts, manage access and preserve learning history."
      />
      <div className="admin-workspace">
        <Panel className="admin-access-panel">
          <h2>Find accounts</h2>
          <p className="muted">
            Search by name or email, then narrow by role and access status.
          </p>
          <form
            className="admin-access-form"
            onSubmit={(event) => {
              event.preventDefault();
              setFilter({ search: search.trim() });
            }}
          >
            <TextField
              label="Search accounts"
              slotProps={{ htmlInput: { "aria-label": "Search accounts" } }}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <Button type="submit" variant="outlined">
              Search
            </Button>
            <TextField
              select
              label="Role filter"
              slotProps={{
                select: {
                  SelectDisplayProps: {
                    "aria-label": "Role filter",
                    "aria-labelledby": undefined,
                  },
                },
              }}
              value={query.role ?? ""}
              onChange={(event) =>
                setFilter({
                  role: (event.target.value || undefined) as
                    api.AccountRole | undefined,
                })
              }
            >
              <MenuItem value="">All roles</MenuItem>
              <MenuItem value="student">Student</MenuItem>
              <MenuItem value="teacher">Teacher</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </TextField>
            <TextField
              select
              label="Status filter"
              slotProps={{
                select: {
                  SelectDisplayProps: {
                    "aria-label": "Status filter",
                    "aria-labelledby": undefined,
                  },
                },
              }}
              value={query.status ?? "enabled"}
              onChange={(event) =>
                setFilter({
                  status: event.target.value as api.AccountStatus | "all",
                })
              }
            >
              <MenuItem value="enabled">Enabled</MenuItem>
              <MenuItem value="disabled">Disabled</MenuItem>
              <MenuItem value="archived">Archived</MenuItem>
              <MenuItem value="all">All statuses</MenuItem>
            </TextField>
          </form>
          {list.loading && <p role="status">Loading accounts...</p>}
          <ReadError message={list.error} retry={() => void list.reload()} />
          {list.data && (
            <>
              {!list.data.accounts.length ? (
                <p>No accounts found.</p>
              ) : (
                <div className="table-scroll">
                  <table className="admin-accounts-table">
                    <thead>
                      <tr>
                        <th>Account</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.data.accounts.map((account) => (
                        <tr key={account.id}>
                          <td>
                            <div>
                              <strong>{account.display_name}</strong>
                              <small>{account.email ?? "No email"}</small>
                            </div>
                          </td>
                          <td data-label="Role">{account.role}</td>
                          <td data-label="Status">{account.status}</td>
                          <td>
                            <Button
                              aria-label={`Manage account ${account.display_name}`}
                              onClick={() => setSelected(account.id)}
                            >
                              Manage account
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="admin-access-actions">
                <Button
                  disabled={list.loading || page <= 1}
                  onClick={() => setQuery({ ...query, page: page - 1 })}
                >
                  Previous
                </Button>
                <span>
                  Page {list.data.page} · {list.data.total} accounts
                </span>
                <Button
                  disabled={
                    list.loading ||
                    page * list.data.page_size >= list.data.total
                  }
                  onClick={() => setQuery({ ...query, page: page + 1 })}
                >
                  Next
                </Button>
              </div>
            </>
          )}
        </Panel>
        <div className="admin-course-read-state">
          {courses.loading && <p role="status">Loading courses...</p>}
          <ReadError
            message={courses.error}
            retry={() => void courses.reload()}
          />
          {selected && (
            <AccountDetails
              key={selected}
              id={selected}
              courses={courses.data?.courses ?? []}
              refreshAccounts={list.reload}
              onClose={() => setSelected(null)}
            />
          )}
        </div>
        <CreateAccount created={list.reload} />
      </div>
    </>
  );
}

export default function AdminAccounts() {
  const { user } = useAuth();
  return (
    <AdminSession>
      <AccountsContent key={user?.id} />
    </AdminSession>
  );
}

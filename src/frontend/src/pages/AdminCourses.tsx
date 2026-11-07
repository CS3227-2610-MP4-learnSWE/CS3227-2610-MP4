import { useState, type FormEvent } from "react";
import { Alert, Button, TextField } from "@mui/material";
import { Link } from "react-router";
import { PageHeading, Panel } from "../components/ui";
import AdminSession from "../components/AdminSession";
import { useAuth } from "../auth/AuthContext";
import { useAdminRead } from "../hooks/useAdminRead";
import { adminError, createCourse, listCourses } from "../services/adminAccess";

function CoursesContent() {
  const courses = useAdminRead(listCourses);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    setSuccess(false);
    try {
      await createCourse(title);
      setTitle("");
      setSuccess(true);
      await courses.reload();
    } catch (failure) {
      setError(adminError(failure));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeading
        title="Courses"
        description="Create a course, then assign its teachers and students through Users."
      />
      <div className="admin-course-workspace">
        <Panel className="admin-access-panel">
          <h2>Create course</h2>
          <p className="muted">Use a clear title, up to 200 characters.</p>
          <form
            className="admin-access-form"
            onSubmit={(event) => void submit(event)}
          >
            <TextField
              label="Course title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              required
              disabled={busy}
              slotProps={{
                htmlInput: { maxLength: 200, "aria-label": "Course title" },
              }}
            />
            <Button variant="contained" type="submit" disabled={busy}>
              Create course
            </Button>
          </form>
          {busy && <p role="status">Creating course...</p>}
          {error && <Alert severity="error">{error}</Alert>}
          {success && <p role="status">Course created.</p>}
        </Panel>
        <Panel className="admin-access-panel">
          <h2>Available courses</h2>
          {courses.loading && <p role="status">Loading courses...</p>}
          {courses.error && (
            <Alert
              severity="error"
              action={
                <Button onClick={() => void courses.reload()}>Try again</Button>
              }
            >
              {courses.error}
            </Alert>
          )}
          {courses.data &&
            (courses.data.courses.length ? (
              <ul className="admin-course-list">
                {courses.data.courses.map((course) => (
                  <li key={course.id}>{course.title}</li>
                ))}
              </ul>
            ) : (
              <p>No courses yet.</p>
            ))}
          <Link to="/admin/users">Manage course access in Users</Link>
        </Panel>
      </div>
    </>
  );
}
export default function AdminCourses() {
  const { user } = useAuth();
  return (
    <AdminSession>
      <CoursesContent key={user?.id} />
    </AdminSession>
  );
}

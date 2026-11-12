import AdminAccounts from "./AdminAccounts";
import AdminCourses from "./AdminCourses";
import { Link, useLocation } from "react-router";
import { EmptyState } from "../components/ui";

function AdminContent() {
  const section = useLocation().pathname.split("/")[2];
  switch (section) {
    case "users":
      return <AdminAccounts />;
    case "courses":
      return <AdminCourses />;
    default:
      return (
        <EmptyState title="This page isn’t here">
          <Link to="/admin/analytics">Back to analytics</Link>
        </EmptyState>
      );
  }
}

export default function Admin() {
  return (
    <div className="admin-surface">
      <AdminContent />
    </div>
  );
}

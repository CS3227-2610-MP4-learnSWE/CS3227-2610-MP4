import { Link } from "react-router";
import { Panel } from "../ui";
import { hubPaths } from "../../lib/feedbackPaths";

/** A path under a known tab that matches no screen. Sends no request. */
export default function HubNotFound() {
  return (
    <div className="admin-surface admin-feedback">
      <Panel>
        <p role="alert">This Feedback hub page does not exist.</p>
        <Link to={hubPaths.forms()}>Go to Forms</Link>
      </Panel>
    </div>
  );
}

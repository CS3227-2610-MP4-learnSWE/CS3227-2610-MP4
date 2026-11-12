import { Link } from "react-router";
import { Button } from "@mui/material";
import { Panel } from "../ui";
import { hubPaths } from "../../lib/feedbackPaths";

/** A path under a known tab that matches no screen. Sends no request. */
export default function HubNotFound() {
  return (
    <div className="admin-surface admin-feedback">
      <Panel>
        <p role="alert">This Feedback hub page does not exist.</p>
        <Button component={Link} to={hubPaths.forms()} variant="contained">
          Go to Forms
        </Button>
      </Panel>
    </div>
  );
}

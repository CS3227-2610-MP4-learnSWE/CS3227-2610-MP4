import ConfirmDeleteDialog from "./ConfirmDeleteDialog";
import { deleteAnalysis } from "../services/feedbackAnalysisApi";
import {
  DELETE_404,
  deleteMessage,
  localTime,
} from "../messages/feedbackAnalysis";

export type DeleteTarget = {
  id: string;
  form_title: string;
  created_at: string;
  response_count: number;
};

export default function DeleteAnalysisDialog({
  target,
  onClose,
  onDeleted,
}: {
  target: DeleteTarget;
  onClose: () => void;
  /** `alreadyGone` is true when the server answered 404. */
  onDeleted: (alreadyGone: boolean) => void;
}) {
  return (
    <ConfirmDeleteDialog
      title="Delete this analysis permanently?"
      run={() => deleteAnalysis(target.id)}
      failure={(e) => {
        const message = deleteMessage(e);
        return { message, gone: message === DELETE_404 };
      }}
      onClose={onClose}
      onDeleted={onDeleted}
    >
      <p>
        Form: {target.form_title}. Created {localTime(target.created_at)}.
        Responses analysed: {target.response_count}.
      </p>
      <p>
        This permanently deletes the analysis: its statistics and charts, the AI
        summary, themes and suggestions, and the links to supporting responses.
        This cannot be undone.
      </p>
      <p>The original feedback responses and forms are not deleted.</p>
    </ConfirmDeleteDialog>
  );
}

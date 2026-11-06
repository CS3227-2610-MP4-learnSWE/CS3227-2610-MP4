"""Fixed, content-free feedback errors shared by validation and transactions."""
from errors import ApiError

ERRORS = {
    "input": (422, "invalid_feedback_input", "Check the feedback form fields and try again."),
    "title": (422, "invalid_feedback_title", "Enter a title of 1 to 160 characters."),
    "questions": (422, "invalid_feedback_questions", "Add 1 to 30 valid questions with unique identifiers."),
    "options": (422, "invalid_feedback_options", "Enter 2 to 20 distinct options for each choice question."),
    "scale": (422, "invalid_feedback_scale", "Set a scale with whole-number endpoints from 0 to 10, with the minimum below the maximum."),
    "association": (422, "invalid_feedback_association", "Select an available feature or published lesson."),
    "text": (422, "invalid_feedback_text", "One or more feedback fields exceed their text limit."),
    "large": (413, "feedback_too_large", "This feedback request is too large. Reduce its content and try again."),
    "audience": (422, "invalid_feedback_audience", "Select 1 to 500 different recipients from one audience role."),
    "answers": (422, "invalid_feedback_answers", "Answer every required question and check that all answers match their question type."),
    "draft_answers": (422, "invalid_feedback_draft_answers", "Check your draft answers and their size limits. Unanswered required questions can be saved."),
    "missing": (404, "feedback_not_found", "This feedback form or response is not available."),
    "version": (409, "feedback_version_conflict", "This form changed in another session. Reload the saved form before continuing."),
    "state": (409, "feedback_state_conflict", "This action is not available in the form's current state."),
    "audience_changed": (409, "feedback_audience_changed", "Some selected recipients are no longer eligible. Review the audience again."),
    "closed": (409, "feedback_closed", "This form is closed."),
    "submitted": (409, "feedback_already_submitted", "You have already submitted feedback."),
    "draft_version": (409, "feedback_draft_version_conflict", "Your draft changed in another session. Reload the saved draft before continuing."),
    "unavailable": (503, "feedback_unavailable", "The feedback service is temporarily unavailable. Try again later."),
    "error": (500, "feedback_error", "The feedback service encountered an error. Try again later."),
}


def fail(kind: str, **extra) -> ApiError:
    return ApiError(*ERRORS[kind], **extra)

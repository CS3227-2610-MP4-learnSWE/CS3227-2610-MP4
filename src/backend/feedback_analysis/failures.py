"""One registry of exact failure messages, and the mapping from shared-client errors to failure records."""
import logging
from dataclasses import dataclass
from uuid import uuid4

from llm_client import (Limits, LlmBadResponse, LlmBusy, LlmInputTooLarge, LlmNotConfigured, LlmRateLimited,
                        LlmTimeout, LlmUpstreamError)

from feedback_analysis.validate import InvalidReply

log = logging.getLogger("feedback_analysis")

_UNAFFECTED = "The statistics are unaffected."
MESSAGES = {
    "invalid_request": "The analysis request is malformed: {reason}.",
    "selection_required": "No responses are selected. Select at least one response, or use Select all, then generate the analysis.",
    "no_responses": "This form has no submitted responses, so there is nothing to analyse.",
    "too_many_responses": "You selected {n} responses, but one analysis can cover at most 500. Select fewer responses.",
    "nothing_to_analyse": "The {n} selected responses contain no answered questions, so there is nothing to analyse.",
    "form_not_found": "That form is not available. It may have been deleted. Choose another form.",
    "response_not_found": "{k} of the {n} selected responses are not available for this form (they may have been deleted or belong to another form). Reload the list and select again.",
    "analysis_in_progress": "Another analysis started {s} seconds ago is still running its AI step. A running AI step finishes or fails within 780 seconds. Wait for it, then generate again.",
    "analysis_not_found": "That analysis is not available. It does not exist or is not in your history.",
    "analysis_running": "This analysis cannot be deleted yet: its AI step has been running for {s} seconds. It finishes or is marked interrupted within {r} seconds (the limit is 780 seconds). Delete it after that.",
    "evidence_not_found": "This response cannot be shown. It was deleted, or the reference is not part of this analysis.",
    "internal_error": "An unexpected server error occurred while {step}. The cause was not an invalid request. Reference {ref} identifies it in the server logs.",
    "feedback_response_not_found": "This response was not found. It may already have been deleted, or it does not belong to this form.",
    "internal_error_response_delete": "An unexpected server error occurred while deleting the response. Nothing was confirmed as deleted. Reference {ref} identifies it in the server logs.",
    "ai_responses_deleted": "The AI step stopped while {step} because {k} of the {n} selected responses were deleted after the analysis started. The statistics remain correct for the responses present when the analysis was created. Start a new analysis to analyse the remaining responses.",
    "ai_timeout": "The AI service did not answer within {t} seconds (after up to 2 attempts) while processing {step}. " + _UNAFFECTED + " Start a new analysis to run the AI part again.",
    "rate_limited_minute": "The AI limit of {limit} requests per minute was reached while processing {step}. Try again in {n} seconds.",
    "rate_limited_day": "The daily AI limit of {limit} requests was reached while processing {step}. Try again in {n} seconds.",
    "ai_busy": "The AI service replied that it is busy (HTTP 429) while processing {step}. Try again in {n} seconds.",
    "ai_unavailable": "The AI service could not be reached or returned a server error while processing {step}, after up to 2 attempts. " + _UNAFFECTED + " Start a new analysis once the service is back.",
    "ai_not_configured": "AI analysis is not configured on this server (no SoC LLM settings are present), so the AI part could not start. Ask the site operator to configure it. " + _UNAFFECTED,
    "ai_input_too_large": "The AI input for {step} was {x} characters, over the limit of {limit}. This is a defect in the batch size, not something you can fix by selecting differently. Reference {ref} identifies it in the server logs.",
    "ai_reply_not_json": "The AI reply for {step} was not a single JSON object, so it was rejected. No AI result was saved. Start a new analysis.",
    "ai_reply_invalid": "The AI reply for {step} was rejected because {rule}. No AI result was saved. Start a new analysis.",
    "ai_reply_cut_off": "The AI reply for {step} was cut off at the output limit of {max_tokens} tokens{empty}. No AI result was saved. Select fewer responses and start a new analysis.",
    "analysis_interrupted": "The AI step was interrupted: it had been running for {s} seconds without finishing (the limit is 780 seconds), probably because the server restarted. It had finished {done} of {total} steps. " + _UNAFFECTED + " Start a new analysis.",
}
RULES = {
    "unexpected_field": "an unexpected field ({field}) was present",
    "missing_field": "a required field ({field}) was missing",
    "wrong_type": "{field} had the wrong type",
    "empty": "{field} was empty",
    "too_long": "{field} was longer than {max} characters",
    "too_many_items": "{field} had {count} items, the maximum is {max}",
    "theme_no_evidence": "a theme had no supporting responses",
    "label_outside_selection": "a supporting response label ({label}) is not in the selection",
    "label_outside_input": "a supporting response label ({label}) was not in the input for this step",
    "feedback_without_evidence": "a suggestion marked as based on feedback had no supporting responses",
    "ai_with_evidence": "a suggestion marked as an AI suggestion listed supporting responses",
    "bad_basis": "a suggestion basis was not feedback or ai",
}
STATUS = {"invalid_request": 422, "selection_required": 422, "no_responses": 422, "too_many_responses": 422,
          "nothing_to_analyse": 422, "form_not_found": 404, "response_not_found": 404, "analysis_in_progress": 409,
          "analysis_not_found": 404, "feedback_response_not_found": 404, "analysis_running": 409, "evidence_not_found": 404, "internal_error": 500}
INVALID_REASONS = {
    "form_id": "form_id is not a valid id", "request_id": "request_id is not a valid id",
    "ids_type": "response_ids must be a list of ids", "ids_value": "response_ids contains a value that is not a valid id",
    "both": "send either response_ids or select_all, not both", "neither": "send response_ids or select_all set to true",
    "select_all": "select_all must be true", "expected": "expected_count must be a whole number from 0 to 500",
    "too_large": "the request body is larger than 256 KiB",
    "expected_only": "expected_count is only allowed with select_all",
    "limit": "limit must be a whole number from 1 to 50", "offset": "offset must be a whole number from 0 to 100000",
}


def render(code, **values):
    if code == "ai_reply_cut_off":
        values.setdefault("empty", "")
    return MESSAGES[code].format(**values)


def step(kind, index=None, total=None):
    return {"kind": kind, "index": index, "total": total}


def step_text(step_):
    if step_["kind"] == "batch":
        return f"batch {step_['index']} of {step_['total']}"
    return "merging themes" if step_["kind"] == "merge" else "starting the AI step"


def new_reference():
    return uuid4().hex[:12]


@dataclass(frozen=True)
class FailureRecord:
    code: str
    message: str
    step: dict
    details: dict

    def as_dict(self):
        return {"code": self.code, "message": self.message, "step": self.step, "details": self.details}


def _record(code, step_, details, **values):
    return FailureRecord(code, render(code, step=step_text(step_), **values), step_, details)


def internal(step_, phrase, exc=None):
    """`phrase` completes "while ...", for example "processing batch 2 of 6"."""
    ref = new_reference()
    log.error("analysis internal error ref=%s class=%s", ref, type(exc).__name__ if exc else "-")
    return FailureRecord("internal_error", render("internal_error", step=phrase, ref=ref), step_, {"reference": ref})


def from_llm_error(exc, step_, client_limits=None, input_chars=0, timeout_seconds=None):
    limits = client_limits or Limits()
    if isinstance(exc, LlmTimeout):
        limit = timeout_seconds if timeout_seconds is not None else limits.timeout_seconds
        return _record("ai_timeout", step_, {"timeout_seconds": limit, "attempts": 2}, t=f"{limit:g}")
    if isinstance(exc, LlmRateLimited):
        day = "day" in exc.scope
        limit = limits.per_caller_per_day if day else limits.per_caller_per_minute
        return _record("rate_limited_day" if day else "rate_limited_minute", step_,
                       {"limit": limit, "window": "day" if day else "minute", "retry_after_seconds": exc.retry_after_seconds},
                       limit=limit, n=exc.retry_after_seconds)
    if isinstance(exc, LlmBusy):
        return _record("ai_busy", step_, {"retry_after_seconds": exc.retry_after_seconds}, n=exc.retry_after_seconds)
    if isinstance(exc, LlmUpstreamError):
        return _record("ai_unavailable", step_, {"attempts": 2})
    if isinstance(exc, LlmBadResponse):
        return _record("ai_reply_not_json", step_, {})
    if isinstance(exc, LlmNotConfigured):
        return _record("ai_not_configured", step_, {})
    if isinstance(exc, LlmInputTooLarge):
        ref = new_reference()
        log.error("analysis input too large ref=%s chars=%s", ref, input_chars)
        return _record("ai_input_too_large", step_, {"chars": input_chars, "limit": limits.max_input_chars, "reference": ref},
                       x=input_chars, limit=limits.max_input_chars, ref=ref)
    return internal(step_, f"processing {step_text(step_)}", exc)


def from_invalid_reply(exc: InvalidReply, step_):
    if exc.code == "ai_reply_not_json":
        return _record("ai_reply_not_json", step_, {})
    rule = RULES[exc.rule].format(field=exc.field, label=exc.label, max=exc.max, count=exc.count)
    return _record("ai_reply_invalid", step_, exc.details, rule=rule)


def responses_deleted(step_, phrase, missing, selected):
    return FailureRecord("ai_responses_deleted", render("ai_responses_deleted", step=phrase, k=missing, n=selected), step_,
                         {"missing": missing, "selected": selected})


# Model-output failures: the only ones the job retries (once).
RETRYABLE = frozenset({"ai_reply_cut_off", "ai_reply_not_json", "ai_reply_invalid"})


def after_two_attempts(record, first_code):
    """The second attempt's failure, marked as such: message suffix, details.attempts and details.first_attempt_code."""
    return FailureRecord(record.code, f"{record.message} The step failed after 2 attempts.", record.step,
                         {**record.details, "attempts": 2, "first_attempt_code": first_code})


def cut_off(step_, max_tokens, empty=False):
    """`empty`: the model produced no answer at all because it used its whole token budget before answering."""
    note = " (the model used its whole token budget before answering)" if empty else ""
    return _record("ai_reply_cut_off", step_, {"max_tokens": max_tokens}, max_tokens=max_tokens, empty=note)


def interrupted(seconds, done, total):
    return FailureRecord("analysis_interrupted", render("analysis_interrupted", s=seconds, done=done, total=total),
                         step("start"), {"ran_seconds": seconds, "done": done, "total": total})

"""Fixed, content-free errors for private administrative messages."""
from errors import ApiError

ERRORS = {
    "INVALID_SUBJECT": (422, "Enter a subject between 1 and 120 characters."),
    "INVALID_BODY": (422, "Enter a message between 1 and 5000 characters."),
    "INVALID_RECIPIENTS": (422, "Select between 1 and 500 recipients."),
    "INVALID_REQUEST": (422, "Check the message and audience, then review again."),
    "RECIPIENT_UNAVAILABLE": (404, "This feedback recipient is unavailable."),
    "PREVIEW_UNAVAILABLE": (404, "This message review is unavailable. Review the message again."),
    "MESSAGE_UNAVAILABLE": (404, "This message is unavailable."),
    "AUDIENCE_CHANGED": (409, "The audience has changed. Review the recipients again before sending."),
    "PREVIEW_EXPIRED": (409, "This review has expired. Review the message again."),
    "REQUEST_TOO_LARGE": (413, "The message request is too large. Shorten it and try again."),
    "MESSAGING_ERROR": (500, "Messaging encountered an error. Try again."),
    "MESSAGING_UNAVAILABLE": (503, "Messaging is temporarily unavailable. Try again."),
    "MESSAGING_RATE_LIMITED": (429, "Too many messaging requests. Wait a minute and try again."),
}


def fail(code, **kwargs):
    status, message = ERRORS[code]
    return ApiError(status, code, message, **kwargs)

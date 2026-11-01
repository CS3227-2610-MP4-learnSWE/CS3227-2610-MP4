"""Companion limits and fixed constants. One place to change them (each change is a separate approved change)."""

MESSAGE_MAX_CHARS = 1_000
HISTORY_MAX_ITEMS = 50  # most the request may carry
HISTORY_ITEM_MAX_CHARS = 2_000
HISTORY_KEEP_MESSAGES = 4  # most recent items sent to the model
HISTORY_KEEP_CHARS = 2_000  # oldest whole messages are dropped until they fit
LABEL_MAX_CHARS = 80

MAX_TOKENS = {"hint": 100, "explain": 200, "help": 150}

CANNED_REPLY = (
    "I can't share or confirm answers while this practice set is open. "
    "Tell me what you have tried and which idea is unclear, and I will give you a hint."
)

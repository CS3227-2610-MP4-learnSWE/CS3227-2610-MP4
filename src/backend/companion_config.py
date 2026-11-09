"""Companion limits and fixed constants. One place to change them (each change is a separate approved change)."""

MESSAGE_MAX_CHARS = 1_000
HISTORY_MAX_ITEMS = 50  # most the request may carry
HISTORY_ITEM_MAX_CHARS = 2_000
HISTORY_KEEP_MESSAGES = 4  # most recent items sent to the model
HISTORY_KEEP_CHARS = 2_000  # oldest whole messages are dropped until they fit
LABEL_MAX_CHARS = 80

MAX_TOKENS = {"hint": 100, "explain": 200, "help": 150, "lesson": 200}

CANNED_REPLY = (
    "I can't share or confirm answers while this practice set is open. "
    "Tell me what you have tried and which idea is unclear, and I will give you a hint."
)

# Grounding in published lessons (STU-03-grounding)
NOT_IN_LESSON_MARKER = "NOT_IN_LESSON:"
LIMITATION_SENTENCE = (
    "This isn't covered in the lesson materials I can see, so this is general help, not course material."
)
LESSON_CANNED_REPLY = (
    "I can't share or confirm practice answers. Ask me about the idea in the lesson and I will explain it."
)
LESSON_MAX_CHARS = 2_000
RELATED_LESSON_LIMIT = 2
LESSON_CANDIDATES = 200
RELATED_MIN_WORD_CHARS = 4
RELATED_MIN_WORDS = 2
RELATED_STOPWORDS = frozenset(
    {
        "what", "which", "who", "when", "where", "why", "how", "does", "this", "that", "these",
        "those", "with", "from", "about", "into", "have", "your", "please", "explain", "tell",
        "give", "show", "help", "mean", "means", "between", "difference", "example", "examples",
        "would", "could", "should", "there", "their", "them", "then", "than", "some", "much",
        "many", "work", "works", "like", "make", "need", "want", "know", "using", "used", "uses",
    }
)

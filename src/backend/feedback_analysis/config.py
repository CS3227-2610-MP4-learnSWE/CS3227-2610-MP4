"""Constants for ADM-03, in one place."""
MAX_RESPONSES = 500
MAX_ENTRY_CHARS = 280
MAX_LABELS_PER_ENTRY = 5
BATCH_DATA_CHARS = 9000
BATCH_MAX_ENTRIES = 30
MAX_MAP_CALLS = 10
MAP_MAX_TOKENS = 1600
MAP_TIMEOUT_SECONDS = 30.0  # per attempt
REDUCE_MAX_TOKENS = 3000
REDUCE_TIMEOUT_SECONDS = 60.0  # per attempt; map calls keep the shared client's default
AGG_PROMPT_CHARS = 1500
PARTIALS_PROMPT_CHARS = 6150
PROMPT_QUESTION_CHARS = 60
JOB_BOUND_SECONDS = 780
HISTORY_DEFAULT_LIMIT = 20
HISTORY_MAX_LIMIT = 50
# The ADM-06 usage label. ADM-06 already reserves "ADM-03" for this feature (see notes.md).
USAGE_FEATURE = "ADM-03"
REDUCE_MAX_REPLY_CHARS = 8000  # the shared client cuts replies at 2000 characters by default; the reduce JSON can be longer
REASONING_EFFORT = "low"  # live test: roughly halves hidden reasoning tokens and latency
AI_START_CUTOFF_SECONDS = 600  # no AI call starts after this; a started call ends within 121 s, so the job ends by 721 s < 780 s

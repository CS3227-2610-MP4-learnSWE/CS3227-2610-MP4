"""One UTC timestamp format for API responses."""
from datetime import timezone


def utc_timestamp(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

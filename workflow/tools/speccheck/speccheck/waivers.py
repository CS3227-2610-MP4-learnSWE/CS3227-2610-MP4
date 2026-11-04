"""Parse and validate the waiver file."""

from dataclasses import dataclass
from pathlib import Path

SCOPES = ("all", "added-items")
_FORMAT = 'expected "spec-id | scope | reason"'


@dataclass(frozen=True)
class Waiver:
    spec_id: str
    scope: str
    reason: str


class WaiverError(Exception):
    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


def _parse_line(number: int, text: str, seen: dict[str, Waiver]) -> Waiver:
    fields = [field.strip() for field in text.split("|")]
    if len(fields) != 3 or not all(fields):
        raise WaiverError(number, _FORMAT)
    spec_id, scope, reason = fields
    if scope not in SCOPES:
        raise WaiverError(number, f'unknown scope "{scope}"')
    if spec_id in seen:
        raise WaiverError(number, f'duplicate id "{spec_id}"')
    return Waiver(spec_id, scope, reason)


def load_waivers(path: Path) -> dict[str, Waiver]:
    """Read the waiver file; a missing file raises FileNotFoundError."""
    text = path.read_bytes().decode("utf-8-sig", errors="replace")
    waivers: dict[str, Waiver] = {}
    for number, raw in enumerate(text.split("\n"), 1):
        line = raw.strip()
        if line and not line.startswith("#"):
            waiver = _parse_line(number, line, waivers)
            waivers[waiver.spec_id] = waiver
    return waivers

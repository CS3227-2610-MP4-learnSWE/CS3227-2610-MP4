"""Shared newline normalisation used by note and MCQ generation and by draft editing."""
import pytest

from text_validation import normalise_newlines_and_trim


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("a\r\nb", "a\nb"),
        ("a\rb", "a\nb"),
        ("  a\r\n\r\nb \r\n", "a\n\nb"),
        ("\r\n \t", ""),
        ("plain", "plain"),
    ],
)
def test_normalise_newlines_and_trim(raw, expected):
    assert normalise_newlines_and_trim(raw) == expected

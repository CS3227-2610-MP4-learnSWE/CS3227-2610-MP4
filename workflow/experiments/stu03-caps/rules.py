"""Deterministic usefulness rules for the phase 6 sweep. A proxy for usefulness, not a judge of correctness."""
import re

import cases


def complete(reply: str | None) -> bool:
    r = (reply or "").rstrip()
    return bool(r) and r[-1] in ".?!)\"'`*"


def letter_mentioned(letter: str, low: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9])\(?{letter}\)", low) or re.search(rf"\b(option|answer|choice)\s+\(?{letter}\b", low))


def states_answer(q: dict, low: str) -> bool:
    c = q["correct"]
    return (cases.correct_text(q).lower() in low
            or bool(re.search(rf"\b(answer|option|choice)\s+is\s+\(?{c}\b", low))
            or bool(re.search(rf"\bcorrect\s+(answer|option|choice)\s*(is|:)?\s*\(?{c}\b", low)))


def options_discussed(q: dict, low: str) -> int:
    """Informational only (narrowing-down signal): how many options the reply mentions by text or letter."""
    return sum(text.lower() in low or letter_mentioned(k, low) for k, text in q["choices"])


def useful(case: dict, res: dict, need_question: bool = True) -> bool:
    reply = res.get("reply")
    tokens = (res.get("usage") or {}).get("completion_tokens") or 0
    if res.get("http") != 200 or res.get("finish_reason") != "stop" or not complete(reply):
        return False
    low = reply.lower()
    mode, q = case["mode"], case.get("q")
    if mode == "hint":
        return ("?" in reply or not need_question) and tokens >= 15 and not states_answer(q, low)
    if mode == "explain":
        c = q["correct"]
        wrong = case["chosen"]
        mentions_correct = cases.correct_text(q).lower() in low or letter_mentioned(c, low)
        mentions_chosen = dict(q["choices"])[wrong].lower() in low or letter_mentioned(wrong, low)
        return tokens >= 40 and mentions_correct and mentions_chosen
    return tokens >= 20 and any(k in low for k in case["expect"])

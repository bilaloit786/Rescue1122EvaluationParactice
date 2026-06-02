import re
from dataclasses import dataclass
from typing import Any


@dataclass
class MCQQuestion:
    question_text: str
    options: list[str]


INSTRUCTION_PREFIXES = (
    "which of the following",
    "choose the",
    "select the",
    "identify the",
    "determine the",
)

BAD_STARTS = (
    "others",
    "also",
    "and",
    "this",
    "these",
    "above",
)

ARTIFICIAL_PATTERNS = re.compile(
    r"\b(?:main safety point|initial scene size-up|practical drill evaluation|"
    r"training assessment|what should a responder do during|"
    r"which action best shows correct basic practice|manual section for this topic)\b",
    flags=re.I,
)

MEASUREMENT_CONTEXT = re.compile(
    r"\b(?:measurement|value|ratio|distance|width|height|headroom|tread|riser|"
    r"minutes?|hours?|feet|foot|inch|inches|percent|requirement|required|standard)\b",
    flags=re.I,
)


def _question_text(question: Any) -> str:
    if isinstance(question, MCQQuestion):
        return question.question_text or ""
    if isinstance(question, dict):
        return str(question.get("question") or question.get("q") or "")
    return str(getattr(question, "question_text", "") or getattr(question, "question", "") or "")


def _options(question: Any) -> list[str]:
    if isinstance(question, MCQQuestion):
        return [str(option) for option in question.options]
    if isinstance(question, dict):
        options = question.get("options") or question.get("opts") or []
        if isinstance(options, dict):
            options = [options[key] for key in sorted(options.keys())]
        return [str(option) for option in options]
    options = getattr(question, "options", []) or []
    return [str(option) for option in options]


def _is_numeric_only(value: str) -> bool:
    return bool(re.fullmatch(r"\s*\d+(?:\.\d+)?\s*", value or ""))


def _is_clear_short_prompt(text: str) -> bool:
    words = text.split()
    if len(words) == 2 and text.endswith(":"):
        first_word = words[0].strip(":").lower()
        second_word = words[1].strip(":").lower()
        if first_word not in {"they", "what", "where", "when", "who", "why", "how", "this", "these"}:
            return second_word in {"means", "mean", "is", "are", "include", "includes"}
    if len(words) < 3:
        return False
    if text.endswith(":"):
        return True
    if "?" in text:
        return True
    return text.lower().startswith(INSTRUCTION_PREFIXES)


def is_valid_question(question: MCQQuestion | dict[str, Any] | Any) -> bool:
    text = " ".join(_question_text(question).strip().split())
    options = _options(question)
    lower_text = text.lower()

    if not text or len(text.split()) > 28:
        return False
    if "____" in text:
        return False
    if re.match(rf"^({'|'.join(BAD_STARTS)})\b", lower_text):
        return False
    if ARTIFICIAL_PATTERNS.search(text):
        return False
    if len(options) < 4:
        return False
    if len({option.strip().lower() for option in options[:4]}) < 4:
        return False
    if all(_is_numeric_only(option) for option in options[:4]) and not MEASUREMENT_CONTEXT.search(text):
        return False
    if not _is_clear_short_prompt(text):
        return False
    if text.endswith("?") and len(text.split()) < 5 and not lower_text.startswith(INSTRUCTION_PREFIXES):
        return False
    return True

"""Sentence-aware verification spans for source-grounded evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

_CLOSING_PUNCTUATION = "\"'”’)]}"
_ABBREVIATIONS = {
    "al",
    "approx",
    "dr",
    "e.g",
    "eq",
    "eqs",
    "etc",
    "fig",
    "figs",
    "i.e",
    "mr",
    "mrs",
    "ms",
    "no",
    "prof",
    "ref",
    "refs",
    "sec",
    "secs",
    "vs",
}


@dataclass(frozen=True, slots=True)
class VerificationSpan:
    """Readable source context around one exact supporting substring."""

    quote: str
    supporting_quote: str
    truncated: bool


def expand_verification_span(
    supporting_quote: str,
    page_text: str,
    *,
    surrounding_sentences: int = 1,
    max_chars: int = 1200,
) -> VerificationSpan:
    """Expand a verified substring to complete sentences on the same page.

    PDF line wrapping is normalized for readability. The exact source substring
    remains separately available so deterministic evidence IDs need not change.
    """

    source = _readable_text(supporting_quote)
    page = _readable_text(page_text)
    if not source or not page:
        return VerificationSpan(
            quote=source,
            supporting_quote=source,
            truncated=True,
        )

    start = page.casefold().find(source.casefold())
    if start < 0:
        return VerificationSpan(
            quote=source,
            supporting_quote=source,
            truncated=True,
        )
    end = start + len(source)
    sentences = _sentence_spans(page)
    overlapping = [
        index
        for index, (sentence_start, sentence_end) in enumerate(sentences)
        if sentence_start < end and sentence_end > start
    ]
    if not overlapping:
        return VerificationSpan(
            quote=source,
            supporting_quote=source,
            truncated=True,
        )

    first = overlapping[0]
    last = overlapping[-1]
    required_start, required_end = sentences[first][0], sentences[last][1]
    required = page[required_start:required_end].strip()
    if (
        len(required) > max_chars
        or not _has_terminal_punctuation(required)
        or not _looks_like_prose(required)
    ):
        return VerificationSpan(
            quote=source[:max_chars].rstrip(),
            supporting_quote=source,
            truncated=True,
        )

    selected_start = required_start
    selected_end = required_end
    for _ in range(max(0, surrounding_sentences)):
        if first > 0:
            candidate_start = sentences[first - 1][0]
            if selected_end - candidate_start <= max_chars:
                first -= 1
                selected_start = candidate_start
        if last + 1 < len(sentences):
            candidate_end = sentences[last + 1][1]
            if candidate_end - selected_start <= max_chars:
                last += 1
                selected_end = candidate_end

    expanded = page[selected_start:selected_end].strip()
    return VerificationSpan(
        quote=expanded,
        supporting_quote=source,
        truncated=not (
            source.casefold() in expanded.casefold()
            and _has_terminal_punctuation(expanded)
            and _looks_like_prose(required)
        ),
    )


def _readable_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for index, character in enumerate(text):
        if character not in ".!?" or not _is_sentence_end(text, index):
            continue
        end = index + 1
        while end < len(text) and text[end] in _CLOSING_PUNCTUATION:
            end += 1
        sentence_start, sentence_end = _trim_span(text, start, end)
        if sentence_end > sentence_start:
            spans.append((sentence_start, sentence_end))
        start = end
        while start < len(text) and text[start].isspace():
            start += 1
    trailing_start, trailing_end = _trim_span(text, start, len(text))
    if trailing_end > trailing_start:
        spans.append((trailing_start, trailing_end))
    return spans


def _is_sentence_end(text: str, index: int) -> bool:
    character = text[index]
    if index + 1 < len(text) and not (
        text[index + 1].isspace() or text[index + 1] in _CLOSING_PUNCTUATION
    ):
        return False
    if character != ".":
        return True
    if (
        index > 0
        and index + 1 < len(text)
        and text[index - 1].isdigit()
        and text[index + 1].isdigit()
    ):
        return False
    prefix = text[:index]
    token_match = re.search(r"([A-Za-z](?:[A-Za-z.]*)?)$", prefix)
    token = token_match.group(1).casefold().rstrip(".") if token_match else ""
    if token in _ABBREVIATIONS or re.fullmatch(r"[a-z]", token):
        return False
    return True


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _has_terminal_punctuation(value: str) -> bool:
    return bool(re.search(r'[.!?]["\'”’)\]}]*$', value.rstrip()))


def _looks_like_prose(value: str) -> bool:
    words = re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", value)
    if len(words) < 6:
        return False
    alphabetic = sum(character.isalpha() for character in value)
    visible = sum(not character.isspace() for character in value)
    return visible > 0 and alphabetic / visible >= 0.55

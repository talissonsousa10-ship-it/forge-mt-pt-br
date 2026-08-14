from __future__ import annotations

from dataclasses import dataclass
import re

from forge_ptbr.glossary.model import GlossaryTerm


@dataclass(frozen=True, slots=True)
class GlossaryResult:
    text: str
    flags: tuple[str, ...]


def _pattern(term: GlossaryTerm, value: str) -> re.Pattern[str]:
    escaped = re.escape(value)
    if term.whole_word:
        escaped = rf"(?<!\w){escaped}(?!\w)"
    flags = 0 if term.case_sensitive else re.IGNORECASE
    return re.compile(escaped, flags)


def detect_terms(source_text: str, terms: list[GlossaryTerm], *, context: str = "") -> list[GlossaryTerm]:
    found: list[GlossaryTerm] = []
    for term in terms:
        if term.contexts and context not in term.contexts:
            continue
        if _pattern(term, term.source).search(source_text):
            found.append(term)
    return found


def apply_glossary(
    source_text: str,
    candidate: str,
    terms: list[GlossaryTerm],
    *,
    context: str = "",
) -> GlossaryResult:
    text = candidate
    flags: list[str] = []
    for term in detect_terms(source_text, terms, context=context):
        target_pattern = _pattern(term, term.target)
        if target_pattern.search(text):
            continue
        source_pattern = _pattern(term, term.source)
        if source_pattern.search(text):
            text = source_pattern.sub(term.target, text)
            continue
        flags.append(f"glossary_missing:{term.source}")
    return GlossaryResult(text=text, flags=tuple(flags))

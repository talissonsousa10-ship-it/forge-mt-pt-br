from __future__ import annotations

from dataclasses import dataclass
import re

from forge_ptbr.tokens import validate_token_equivalence


@dataclass(frozen=True, slots=True)
class QualityResult:
    score: int
    flags: tuple[str, ...]


def evaluate_quality(
    source: str,
    candidate: str,
    *,
    glossary_flags: tuple[str, ...] = (),
) -> QualityResult:
    flags: list[str] = []
    hard_failure = False

    if not candidate.strip():
        flags.append("blank_candidate")
        hard_failure = True

    if "__FORGE_TOKEN_" in candidate:
        flags.append("leaked_token_mask")
        hard_failure = True

    for error in validate_token_equivalence(source, candidate):
        kind, _, token = error.partition(": ")
        flags.append(f"{kind.replace(' ', '_')}:{token}")
        hard_failure = True

    flags.extend(glossary_flags)

    if source.strip() and len(source.strip()) >= 8 and source.strip().casefold() == candidate.strip().casefold():
        flags.append("suspicious_unchanged_source")

    if source.strip() and candidate.strip() and len(source.strip()) >= 10:
        ratio = len(candidate.strip()) / len(source.strip())
        if ratio < 0.25 or ratio > 3.0:
            flags.append("extreme_length_ratio")

    if re.search(r" {3,}|\n{3,}", candidate):
        flags.append("repeated_whitespace")

    if hard_failure:
        return QualityResult(score=0, flags=tuple(dict.fromkeys(flags)))

    score = 100
    for flag in flags:
        if flag.startswith("glossary_missing:"):
            score -= 15
        elif flag == "suspicious_unchanged_source":
            score -= 40
        elif flag == "extreme_length_ratio":
            score -= 20
        elif flag == "repeated_whitespace":
            score -= 10
    return QualityResult(score=max(0, score), flags=tuple(dict.fromkeys(flags)))

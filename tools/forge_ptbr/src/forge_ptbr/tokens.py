from collections import Counter
from dataclasses import dataclass
import re


TOKEN_RE = re.compile(r"\$\([A-Za-z0-9_]+\)|\{\d+\}|%(?:s|d)|\\n|\r?\n")


@dataclass(frozen=True, slots=True)
class MaskedText:
    text: str
    tokens: tuple[str, ...]


def extract_tokens(text: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in TOKEN_RE.finditer(text))


def mask_tokens(text: str) -> MaskedText:
    tokens: list[str] = []

    def replace(match: re.Match[str]) -> str:
        index = len(tokens)
        tokens.append(match.group(0))
        return f"__FORGE_TOKEN_{index}__"

    return MaskedText(TOKEN_RE.sub(replace, text), tuple(tokens))


def restore_tokens(masked_text: str, tokens: tuple[str, ...]) -> str:
    restored = masked_text
    for index, token in enumerate(tokens):
        restored = restored.replace(f"__FORGE_TOKEN_{index}__", token)
    return restored


def validate_token_equivalence(source: str, candidate: str) -> list[str]:
    source_counts = Counter(extract_tokens(source))
    candidate_counts = Counter(extract_tokens(candidate))
    errors: list[str] = []
    for token, count in source_counts.items():
        for _ in range(max(0, count - candidate_counts[token])):
            errors.append(f"missing token: {token}")
    for token, count in candidate_counts.items():
        for _ in range(max(0, count - source_counts[token])):
            errors.append(f"added token: {token}")
    return errors

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GlossaryTerm:
    source: str
    target: str
    case_sensitive: bool = False
    whole_word: bool = True
    contexts: tuple[str, ...] = ()
    notes: str = ""

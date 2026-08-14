from __future__ import annotations

from typing import Protocol


class TranslationProvider(Protocol):
    name: str

    def is_ready(self) -> bool:
        ...

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        ...

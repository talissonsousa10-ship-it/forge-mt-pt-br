from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    source_text: str
    translation: str
    plane: str
    resource_type: str
    context: str
    source_file: str
    source_path: str
    source_hash: str
    translator: str
    reviewed: bool

    def sort_key(self) -> tuple[str, ...]:
        return (
            self.source_text,
            self.plane,
            self.resource_type,
            self.context,
            self.translation,
            self.source_file,
            self.source_path,
        )

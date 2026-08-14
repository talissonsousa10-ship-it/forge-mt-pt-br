from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from pathlib import Path


class FieldKind(str, Enum):
    LOCALIZABLE_EXISTING_HOOK = "localizable_existing_hook"
    LOCALIZABLE_NEEDS_HOOK = "localizable_needs_hook"
    PROTECTED = "protected"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    plane: str
    relative_file: Path
    json_path: str
    resource_type: str


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    source_id: str
    location: SourceLocation
    field_name: str
    source_text: str
    source_hash: str
    kind: FieldKind
    tokens: tuple[str, ...] = ()


@dataclass(slots=True)
class ScanReport:
    entries: list[InventoryEntry] = field(default_factory=list)
    scanned_files: int = 0
    unsupported_files: list[str] = field(default_factory=list)

    @property
    def unknown_entries(self) -> list[InventoryEntry]:
        return [entry for entry in self.entries if entry.kind is FieldKind.UNKNOWN]


def source_text_hash(source_text: str) -> str:
    return sha256(source_text.encode("utf-8")).hexdigest()


def stable_source_id(location: SourceLocation, source_text: str) -> str:
    identity = "|".join(
        [location.plane, location.relative_file.as_posix(), location.json_path, location.resource_type]
    )
    digest = sha256(identity.encode("utf-8")).hexdigest()[:20]
    return f"src_{digest}"

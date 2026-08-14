from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TranslationStatus(str, Enum):
    NEW = "new"
    AUTO = "auto"
    REVIEW = "review"
    APPROVED = "approved"
    CHANGED = "changed"
    OBSOLETE = "obsolete"


@dataclass(slots=True)
class CatalogEntry:
    source_id: str
    localization_key: str
    plane: str
    resource_type: str
    relative_file: str
    json_path: str
    field_name: str
    source_text: str
    source_hash: str
    tokens: tuple[str, ...] = ()
    translation: str = ""
    status: TranslationStatus = TranslationStatus.NEW
    quality_score: int | None = None
    quality_flags: tuple[str, ...] = ()
    translator: str | None = None
    reviewed: bool = False

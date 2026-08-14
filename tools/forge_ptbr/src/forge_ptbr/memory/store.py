from __future__ import annotations

import json
from pathlib import Path

from forge_ptbr.catalog.model import CatalogEntry, TranslationStatus
from forge_ptbr.memory.model import MemoryRecord


def _to_dict(record: MemoryRecord) -> dict[str, object]:
    return {
        "source_text": record.source_text,
        "translation": record.translation,
        "plane": record.plane,
        "resource_type": record.resource_type,
        "context": record.context,
        "source_file": record.source_file,
        "source_path": record.source_path,
        "source_hash": record.source_hash,
        "translator": record.translator,
        "reviewed": record.reviewed,
    }


def _from_dict(payload: dict[str, object]) -> MemoryRecord:
    return MemoryRecord(
        source_text=str(payload["source_text"]),
        translation=str(payload["translation"]),
        plane=str(payload.get("plane", "")),
        resource_type=str(payload.get("resource_type", "")),
        context=str(payload.get("context", "")),
        source_file=str(payload.get("source_file", "")),
        source_path=str(payload.get("source_path", "")),
        source_hash=str(payload.get("source_hash", "")),
        translator=str(payload.get("translator", "human")),
        reviewed=bool(payload.get("reviewed", False)),
    )


def load_memory(path: Path) -> list[MemoryRecord]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported memory schema in {path}")
    return sorted((_from_dict(item) for item in payload.get("records", [])), key=lambda r: r.sort_key())


def write_memory(path: Path, records: list[MemoryRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records, key=lambda record: record.sort_key())
    payload = {"schema_version": 1, "records": [_to_dict(record) for record in ordered]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def promote_approved(entries: list[CatalogEntry], existing: list[MemoryRecord]) -> list[MemoryRecord]:
    records = list(existing)
    for entry in entries:
        if entry.status is not TranslationStatus.APPROVED or not entry.reviewed or not entry.translation:
            continue
        records.append(
            MemoryRecord(
                source_text=entry.source_text,
                translation=entry.translation,
                plane=entry.plane,
                resource_type=entry.resource_type,
                context=f"{entry.resource_type}:{entry.field_name}",
                source_file=entry.relative_file,
                source_path=entry.json_path,
                source_hash=entry.source_hash,
                translator=entry.translator or "human",
                reviewed=True,
            )
        )
    dedup: dict[tuple[str, str, str, str, str], MemoryRecord] = {}
    for record in sorted(records, key=lambda r: r.sort_key()):
        key = (record.source_text, record.translation, record.plane, record.resource_type, record.context)
        dedup.setdefault(key, record)
    return sorted(dedup.values(), key=lambda r: r.sort_key())

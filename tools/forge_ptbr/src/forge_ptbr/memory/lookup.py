from __future__ import annotations

from forge_ptbr.catalog.model import CatalogEntry
from forge_ptbr.memory.model import MemoryRecord


def _compatible(expected: str, actual: str) -> bool:
    return not expected or expected == actual


def find_reviewed_translation(
    records: list[MemoryRecord],
    source_text: str,
    *,
    plane: str,
    resource_type: str,
    context: str,
) -> MemoryRecord | None:
    candidates: list[tuple[int, MemoryRecord]] = []
    for record in records:
        if not record.reviewed or record.source_text != source_text:
            continue
        if not _compatible(record.plane, plane):
            continue
        if not _compatible(record.resource_type, resource_type):
            continue
        if not _compatible(record.context, context):
            continue
        specificity = sum(bool(value) for value in (record.plane, record.resource_type, record.context))
        candidates.append((specificity, record))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1].sort_key()))
    return candidates[0][1]


def lookup_for_entry(records: list[MemoryRecord], entry: CatalogEntry) -> MemoryRecord | None:
    return find_reviewed_translation(
        records,
        entry.source_text,
        plane=entry.plane,
        resource_type=entry.resource_type,
        context=f"{entry.resource_type}:{entry.field_name}",
    )

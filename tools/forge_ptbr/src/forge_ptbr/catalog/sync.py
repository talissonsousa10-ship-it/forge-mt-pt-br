from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from forge_ptbr.catalog.keys import make_localization_key
from forge_ptbr.catalog.model import CatalogEntry, TranslationStatus
from forge_ptbr.catalog.store import catalog_path, load_all_catalogs, write_catalog
from forge_ptbr.model import FieldKind, InventoryEntry, ScanReport


_LOCALIZABLE = {
    FieldKind.LOCALIZABLE_EXISTING_HOOK,
    FieldKind.LOCALIZABLE_NEEDS_HOOK,
}


@dataclass(frozen=True, slots=True)
class SyncSummary:
    new: int = 0
    changed: int = 0
    obsolete: int = 0
    approved: int = 0
    total: int = 0


def _from_inventory(source: InventoryEntry) -> CatalogEntry:
    return CatalogEntry(
        source_id=source.source_id,
        localization_key=make_localization_key(
            source.source_id,
            source.location.plane,
            source.location.resource_type,
            source.field_name,
        ),
        plane=source.location.plane,
        resource_type=source.location.resource_type,
        relative_file=source.location.relative_file.as_posix(),
        json_path=source.location.json_path,
        field_name=source.field_name,
        source_text=source.source_text,
        source_hash=source.source_hash,
        tokens=source.tokens,
    )


def _refresh_changed(existing: CatalogEntry, source: InventoryEntry) -> None:
    existing.plane = source.location.plane
    existing.resource_type = source.location.resource_type
    existing.relative_file = source.location.relative_file.as_posix()
    existing.json_path = source.location.json_path
    existing.field_name = source.field_name
    existing.source_text = source.source_text
    existing.source_hash = source.source_hash
    existing.tokens = source.tokens
    existing.status = TranslationStatus.CHANGED
    existing.reviewed = False
    existing.quality_score = None
    existing.quality_flags = ()


def _mark_obsolete(entry: CatalogEntry, *, safety_flag: bool) -> None:
    entry.status = TranslationStatus.OBSOLETE
    entry.reviewed = False
    if safety_flag and "source_not_localizable" not in entry.quality_flags:
        entry.quality_flags = (*entry.quality_flags, "source_not_localizable")


def sync_catalogs(report: ScanReport, catalogs_dir: Path) -> SyncSummary:
    catalogs = load_all_catalogs(catalogs_dir)
    existing_by_id: dict[str, CatalogEntry] = {
        entry.source_id: entry
        for entries in catalogs.values()
        for entry in entries
    }
    seen_ids = {entry.source_id for entry in report.entries}
    nonlocalizable_ids = {
        entry.source_id for entry in report.entries if entry.kind not in _LOCALIZABLE
    }

    for source in report.entries:
        if source.kind not in _LOCALIZABLE:
            existing = existing_by_id.get(source.source_id)
            if existing is not None:
                _mark_obsolete(existing, safety_flag=True)
            continue

        existing = existing_by_id.get(source.source_id)
        if existing is None:
            created = _from_inventory(source)
            catalogs.setdefault(source.location.plane, []).append(created)
            existing_by_id[source.source_id] = created
            continue

        if existing.source_hash != source.source_hash:
            _refresh_changed(existing, source)

    for source_id, existing in existing_by_id.items():
        if source_id not in seen_ids:
            _mark_obsolete(existing, safety_flag=False)
        elif source_id in nonlocalizable_ids:
            _mark_obsolete(existing, safety_flag=True)

    for plane, entries in catalogs.items():
        write_catalog(catalog_path(catalogs_dir, plane), plane, entries)

    all_entries = [entry for entries in catalogs.values() for entry in entries]
    return SyncSummary(
        new=sum(entry.status is TranslationStatus.NEW for entry in all_entries),
        changed=sum(entry.status is TranslationStatus.CHANGED for entry in all_entries),
        obsolete=sum(entry.status is TranslationStatus.OBSOLETE for entry in all_entries),
        approved=sum(entry.status is TranslationStatus.APPROVED for entry in all_entries),
        total=len(all_entries),
    )

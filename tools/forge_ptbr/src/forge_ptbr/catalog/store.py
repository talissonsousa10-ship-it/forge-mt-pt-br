from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from forge_ptbr.catalog.keys import slugify_key_part
from forge_ptbr.catalog.model import CatalogEntry, TranslationStatus


SCHEMA_VERSION = 1


def catalog_path(catalogs_dir: Path, plane: str) -> Path:
    return catalogs_dir / f"{slugify_key_part(plane)}.json"


def _entry_to_dict(entry: CatalogEntry) -> dict[str, object]:
    return {
        "source_id": entry.source_id,
        "localization_key": entry.localization_key,
        "plane": entry.plane,
        "resource_type": entry.resource_type,
        "relative_file": entry.relative_file,
        "json_path": entry.json_path,
        "field_name": entry.field_name,
        "source_text": entry.source_text,
        "source_hash": entry.source_hash,
        "tokens": list(entry.tokens),
        "translation": entry.translation,
        "status": entry.status.value,
        "quality_score": entry.quality_score,
        "quality_flags": list(entry.quality_flags),
        "translator": entry.translator,
        "reviewed": entry.reviewed,
    }


def _entry_from_dict(payload: dict[str, object]) -> CatalogEntry:
    return CatalogEntry(
        source_id=str(payload["source_id"]),
        localization_key=str(payload["localization_key"]),
        plane=str(payload["plane"]),
        resource_type=str(payload["resource_type"]),
        relative_file=str(payload["relative_file"]),
        json_path=str(payload["json_path"]),
        field_name=str(payload["field_name"]),
        source_text=str(payload["source_text"]),
        source_hash=str(payload["source_hash"]),
        tokens=tuple(str(value) for value in payload.get("tokens", [])),
        translation=str(payload.get("translation", "")),
        status=TranslationStatus(str(payload.get("status", TranslationStatus.NEW.value))),
        quality_score=(
            int(payload["quality_score"])
            if payload.get("quality_score") is not None
            else None
        ),
        quality_flags=tuple(str(value) for value in payload.get("quality_flags", [])),
        translator=(str(payload["translator"]) if payload.get("translator") is not None else None),
        reviewed=bool(payload.get("reviewed", False)),
    )


def load_catalog(path: Path) -> tuple[str, list[CatalogEntry]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported catalog schema in {path}")
    plane = str(payload["plane"])
    entries = [_entry_from_dict(item) for item in payload.get("entries", [])]
    entries.sort(key=lambda entry: entry.source_id)
    return plane, entries


def write_catalog(path: Path, plane: str, entries: list[CatalogEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(entries, key=lambda entry: entry.source_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "plane": plane,
        "entries": [_entry_to_dict(entry) for entry in ordered],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_all_catalogs(catalogs_dir: Path) -> dict[str, list[CatalogEntry]]:
    if not catalogs_dir.exists():
        return {}
    catalogs: dict[str, list[CatalogEntry]] = {}
    for path in sorted(catalogs_dir.glob("*.json"), key=lambda p: p.name.casefold()):
        plane, entries = load_catalog(path)
        catalogs[plane] = entries
    return catalogs

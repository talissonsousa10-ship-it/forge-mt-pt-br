from __future__ import annotations

import json
from pathlib import Path

from forge_ptbr.model import (
    InventoryEntry,
    ScanReport,
    SourceLocation,
    source_text_hash,
    stable_source_id,
)
from forge_ptbr.paths import adventure_root
from forge_ptbr.scanner.discovery import discover_resources
from forge_ptbr.scanner.json_walk import walk_json_strings
from forge_ptbr.scanner.rules import classify_json_field
from forge_ptbr.tokens import extract_tokens


def scan_adventure(repo_root: Path) -> ScanReport:
    report = ScanReport()
    root = adventure_root(repo_root)

    for resource in discover_resources(root):
        report.scanned_files += 1
        if resource.suffix != ".json":
            report.unsupported_files.append(
                f"{resource.plane}/{resource.relative_file.as_posix()}"
            )
            continue

        try:
            document = json.loads(resource.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            resource_name = f"{resource.plane}/{resource.relative_file.as_posix()}"
            raise ValueError(f"{resource_name}: {exc}") from exc

        for field in walk_json_strings(document):
            if not field.value:
                continue
            location = SourceLocation(
                plane=resource.plane,
                relative_file=resource.relative_file,
                json_path=field.json_path,
                resource_type=resource.relative_file.stem,
            )
            report.entries.append(
                InventoryEntry(
                    source_id=stable_source_id(location, field.value),
                    location=location,
                    field_name=field.key,
                    source_text=field.value,
                    source_hash=source_text_hash(field.value),
                    kind=classify_json_field(resource.relative_file, field),
                    tokens=extract_tokens(field.value),
                )
            )

    report.entries.sort(
        key=lambda entry: (
            entry.location.plane.casefold(),
            entry.location.relative_file.as_posix().casefold(),
            entry.location.json_path,
        )
    )
    report.unsupported_files.sort(key=str.casefold)
    return report

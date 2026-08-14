from __future__ import annotations

import json
from pathlib import Path

from forge_ptbr.model import FieldKind, ScanReport


def report_to_dict(report: ScanReport) -> dict[str, object]:
    counts = {kind: 0 for kind in FieldKind}
    for entry in report.entries:
        counts[entry.kind] += 1

    return {
        "schema_version": 1,
        "summary": {
            "scanned_files": report.scanned_files,
            "entries": len(report.entries),
            "localizable_existing_hook": counts[FieldKind.LOCALIZABLE_EXISTING_HOOK],
            "localizable_needs_hook": counts[FieldKind.LOCALIZABLE_NEEDS_HOOK],
            "protected": counts[FieldKind.PROTECTED],
            "unknown": counts[FieldKind.UNKNOWN],
            "unsupported_files": len(report.unsupported_files),
        },
        "unsupported_files": report.unsupported_files,
        "entries": [
            {
                "source_id": entry.source_id,
                "plane": entry.location.plane,
                "relative_file": entry.location.relative_file.as_posix(),
                "json_path": entry.location.json_path,
                "resource_type": entry.location.resource_type,
                "field_name": entry.field_name,
                "source_text": entry.source_text,
                "source_hash": entry.source_hash,
                "kind": entry.kind.value,
                "tokens": list(entry.tokens),
            }
            for entry in report.entries
        ],
    }


def write_json_report(report: ScanReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report_to_dict(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

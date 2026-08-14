from __future__ import annotations

import json
from pathlib import Path

from forge_ptbr.glossary.model import GlossaryTerm


def load_glossary(path: Path) -> list[GlossaryTerm]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported glossary schema in {path}")
    terms = [
        GlossaryTerm(
            source=str(item["source"]),
            target=str(item["target"]),
            case_sensitive=bool(item.get("case_sensitive", False)),
            whole_word=bool(item.get("whole_word", True)),
            contexts=tuple(str(value) for value in item.get("contexts", [])),
            notes=str(item.get("notes", "")),
        )
        for item in payload.get("terms", [])
    ]
    return sorted(terms, key=lambda term: (term.source.casefold(), term.target.casefold()))

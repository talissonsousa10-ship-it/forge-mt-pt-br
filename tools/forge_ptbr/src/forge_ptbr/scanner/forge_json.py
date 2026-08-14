from __future__ import annotations

import json
import re


_MEMBER_RE = re.compile(r'^\s*"[^"\\]*(?:\\.[^"\\]*)*"\s*:')


def _insert_missing_member_commas(text: str) -> str:
    lines = text.splitlines()
    previous_significant: int | None = None

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        if previous_significant is not None:
            previous = lines[previous_significant].rstrip()
            previous_stripped = previous.strip()
            missing_member_comma = bool(_MEMBER_RE.match(line)) and (
                bool(previous_stripped)
                and not previous_stripped.endswith((",", "{", "[", ":"))
                and not previous_stripped.startswith(("//", "/*", "*"))
            )
            missing_array_object_comma = (
                stripped.startswith(("{", "["))
                and previous_stripped.endswith(("}", "]"))
                and not previous_stripped.endswith(("},", "],"))
            )
            if missing_member_comma or missing_array_object_comma:
                lines[previous_significant] = previous + ","

        previous_significant = index

    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + suffix


def loads_forge_json(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError as strict_error:
        normalized = _insert_missing_member_commas(text)
        if normalized == text:
            raise strict_error
        try:
            return json.loads(normalized)
        except json.JSONDecodeError:
            raise strict_error

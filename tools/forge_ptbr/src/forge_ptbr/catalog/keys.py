from __future__ import annotations

import re
import unicodedata


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def slugify_key_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = _NON_ALNUM_RE.sub("_", ascii_value).strip("_")
    return slug or "value"


def make_localization_key(
    source_id: str,
    plane: str,
    resource_type: str,
    field_name: str,
) -> str:
    identity = source_id.removeprefix("src_")
    suffix = identity[-12:]
    return ".".join(
        [
            "adv",
            slugify_key_part(plane),
            slugify_key_part(resource_type),
            slugify_key_part(field_name),
            suffix,
        ]
    )

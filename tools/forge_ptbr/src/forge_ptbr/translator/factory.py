from __future__ import annotations

from forge_ptbr.translator.base import TranslationProvider
from forge_ptbr.translator.providers.argos import ArgosProvider


def make_provider(name: str) -> TranslationProvider:
    normalized = name.strip().casefold()
    if normalized == "argos":
        return ArgosProvider()
    raise ValueError(f"Unknown translation provider: {name}")

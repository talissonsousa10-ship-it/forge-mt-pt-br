from __future__ import annotations

from forge_ptbr.catalog.model import CatalogEntry, TranslationStatus
from forge_ptbr.glossary.apply import apply_glossary
from forge_ptbr.glossary.model import GlossaryTerm
from forge_ptbr.memory.lookup import lookup_for_entry
from forge_ptbr.memory.model import MemoryRecord
from forge_ptbr.quality.checks import evaluate_quality
from forge_ptbr.tokens import mask_tokens, restore_tokens
from forge_ptbr.translator.base import TranslationProvider


_TRANSLATABLE_STATUSES = {
    TranslationStatus.NEW,
    TranslationStatus.CHANGED,
    TranslationStatus.REVIEW,
}


def translate_catalog_entry(
    entry: CatalogEntry,
    provider: TranslationProvider,
    memory_records: list[MemoryRecord],
    glossary_terms: list[GlossaryTerm],
    *,
    source_lang: str = "en",
    target_lang: str = "pt-BR",
) -> bool:
    if entry.status not in _TRANSLATABLE_STATUSES:
        return False

    memory_match = lookup_for_entry(memory_records, entry)
    from_memory = memory_match is not None

    if memory_match is not None:
        candidate = memory_match.translation
        translator_name = "memory"
    else:
        masked = mask_tokens(entry.source_text)
        provider_output = provider.translate(masked.text, source_lang, target_lang)
        candidate = restore_tokens(provider_output, masked.tokens)
        translator_name = provider.name

    glossary_result = apply_glossary(
        entry.source_text,
        candidate,
        glossary_terms,
        context="adventure",
    )
    quality = evaluate_quality(
        entry.source_text,
        glossary_result.text,
        glossary_flags=glossary_result.flags,
    )

    new_status = TranslationStatus.AUTO
    if from_memory or quality.score < 80 or quality.flags:
        new_status = TranslationStatus.REVIEW

    entry.translation = glossary_result.text
    entry.translator = translator_name
    entry.quality_score = quality.score
    entry.quality_flags = quality.flags
    entry.status = new_status
    entry.reviewed = False
    return True

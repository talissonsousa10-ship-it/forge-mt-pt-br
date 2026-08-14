from forge_ptbr.catalog.model import CatalogEntry, TranslationStatus
from forge_ptbr.glossary.model import GlossaryTerm
from forge_ptbr.memory.model import MemoryRecord
from forge_ptbr.translator.service import translate_catalog_entry


class FakeProvider:
    name = "fake"

    def __init__(self, result: str = "Tradução") -> None:
        self.result = result
        self.calls: list[str] = []

    def is_ready(self) -> bool:
        return True

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        self.calls.append(text)
        return self.result


def _entry(text: str = "Defeat $(enemy_1).") -> CatalogEntry:
    return CatalogEntry(
        source_id="src_1234567890abcdef1234",
        localization_key="adv.shandalar.quests.description.90abcdef1234",
        plane="Shandalar",
        resource_type="quests",
        relative_file="world/quests.json",
        json_path="$[0].description",
        field_name="description",
        source_text=text,
        source_hash="hash",
        tokens=("$(enemy_1)",) if "$(enemy_1)" in text else (),
    )


def test_memory_hit_avoids_provider_and_enters_review() -> None:
    entry = _entry("Hello")
    memory = [MemoryRecord(
        source_text="Hello",
        translation="Olá",
        plane="Shandalar",
        resource_type="quests",
        context="quests:description",
        source_file="world/quests.json",
        source_path="$[0].description",
        source_hash="hash",
        translator="human",
        reviewed=True,
    )]
    provider = FakeProvider("NÃO USAR")

    changed = translate_catalog_entry(entry, provider, memory, [])

    assert changed is True
    assert provider.calls == []
    assert entry.translation == "Olá"
    assert entry.translator == "memory"
    assert entry.status is TranslationStatus.REVIEW


def test_provider_receives_masked_tokens_and_output_restores_them() -> None:
    entry = _entry()
    provider = FakeProvider("Derrote __FORGE_TOKEN_0__.")

    translate_catalog_entry(entry, provider, [], [])

    assert provider.calls == ["Defeat __FORGE_TOKEN_0__."]
    assert entry.translation == "Derrote $(enemy_1)."
    assert entry.status is TranslationStatus.AUTO
    assert entry.reviewed is False


def test_quality_failure_enters_review_never_approved() -> None:
    entry = _entry()
    provider = FakeProvider("Derrote o inimigo.")

    translate_catalog_entry(entry, provider, [], [])

    assert entry.status is TranslationStatus.REVIEW
    assert entry.quality_score == 0
    assert any(flag.startswith("missing_token:") for flag in entry.quality_flags)


def test_glossary_is_applied_after_provider() -> None:
    entry = _entry("A creature with Flying attacks.")
    provider = FakeProvider("Uma criatura com Flying ataca.")
    glossary = [GlossaryTerm("Flying", "Voar")]

    translate_catalog_entry(entry, provider, [], glossary)

    assert entry.translation == "Uma criatura com Voar ataca."
    assert entry.status is TranslationStatus.AUTO


def test_approved_unchanged_entry_is_skipped() -> None:
    entry = _entry("Hello")
    entry.translation = "Olá"
    entry.status = TranslationStatus.APPROVED
    entry.reviewed = True
    provider = FakeProvider()

    changed = translate_catalog_entry(entry, provider, [], [])

    assert changed is False
    assert provider.calls == []
    assert entry.translation == "Olá"

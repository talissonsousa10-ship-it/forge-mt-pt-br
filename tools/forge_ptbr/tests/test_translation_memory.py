from pathlib import Path

from forge_ptbr.catalog.model import CatalogEntry, TranslationStatus
from forge_ptbr.memory.lookup import find_reviewed_translation, lookup_for_entry
from forge_ptbr.memory.model import MemoryRecord
from forge_ptbr.memory.store import load_memory, promote_approved, write_memory


def _record(translation: str, *, resource_type: str = "quests", reviewed: bool = True) -> MemoryRecord:
    return MemoryRecord(
        source_text="Draw",
        translation=translation,
        plane="Shandalar",
        resource_type=resource_type,
        context=f"{resource_type}:name",
        source_file="world/quests.json",
        source_path="$[0].name",
        source_hash="hash",
        translator="human",
        reviewed=reviewed,
    )


def test_contextual_reviewed_match_wins_and_unreviewed_is_ignored() -> None:
    records = [
        _record("Ignorar", reviewed=False),
        _record("Empate", resource_type="events"),
        _record("Comprar"),
    ]

    match = find_reviewed_translation(
        records,
        "Draw",
        plane="Shandalar",
        resource_type="quests",
        context="quests:name",
    )

    assert match is not None
    assert match.translation == "Comprar"


def test_memory_store_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "memory.json"
    records = [_record("Comprar"), _record("Empate", resource_type="events")]
    write_memory(path, records)
    first = path.read_bytes()
    write_memory(path, list(reversed(records)))

    assert path.read_bytes() == first
    assert load_memory(path) == sorted(records, key=lambda record: record.sort_key())


def test_only_approved_reviewed_catalog_entries_are_promoted_and_deduplicated() -> None:
    approved = CatalogEntry(
        source_id="src_1",
        localization_key="adv.shandalar.quests.name.1",
        plane="Shandalar",
        resource_type="quests",
        relative_file="world/quests.json",
        json_path="$[0].name",
        field_name="name",
        source_text="Hello",
        source_hash="hash",
        translation="Olá",
        status=TranslationStatus.APPROVED,
        reviewed=True,
        translator="human",
    )
    automatic = CatalogEntry(
        source_id="src_2",
        localization_key="adv.shandalar.quests.name.2",
        plane="Shandalar",
        resource_type="quests",
        relative_file="world/quests.json",
        json_path="$[1].name",
        field_name="name",
        source_text="Automatic",
        source_hash="hash2",
        translation="Automático",
        status=TranslationStatus.AUTO,
        reviewed=False,
    )

    records = promote_approved([approved, approved, automatic], [])

    assert len(records) == 1
    assert records[0].translation == "Olá"
    assert records[0].reviewed is True


def test_lookup_for_catalog_entry_uses_resource_context() -> None:
    entry = CatalogEntry(
        source_id="src_1",
        localization_key="adv.shandalar.quests.name.1",
        plane="Shandalar",
        resource_type="quests",
        relative_file="world/quests.json",
        json_path="$[0].name",
        field_name="name",
        source_text="Draw",
        source_hash="hash",
    )

    match = lookup_for_entry([_record("Comprar"), _record("Empate", resource_type="events")], entry)
    assert match is not None
    assert match.translation == "Comprar"

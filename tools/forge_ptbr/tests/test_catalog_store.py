from pathlib import Path

from forge_ptbr.catalog.model import CatalogEntry, TranslationStatus
from forge_ptbr.catalog.store import load_catalog, write_catalog


def _entry(source_id: str, text: str) -> CatalogEntry:
    return CatalogEntry(
        source_id=source_id,
        localization_key=f"adv.shandalar.quests.name.{source_id[-12:]}",
        plane="Shandalar",
        resource_type="quests",
        relative_file="world/quests.json",
        json_path="$[0].name",
        field_name="name",
        source_text=text,
        source_hash="hash",
        translation="Missão",
        status=TranslationStatus.APPROVED,
        reviewed=True,
    )


def test_catalog_round_trip_preserves_types_and_utf8(tmp_path: Path) -> None:
    path = tmp_path / "shandalar.json"
    write_catalog(path, "Shandalar", [_entry("src_bbbbbbbbbbbbbbbbbbbb", "Ação")])

    plane, entries = load_catalog(path)

    assert plane == "Shandalar"
    assert entries[0].source_text == "Ação"
    assert entries[0].status is TranslationStatus.APPROVED
    assert entries[0].reviewed is True


def test_catalog_write_is_byte_stable_and_sorted(tmp_path: Path) -> None:
    path = tmp_path / "shandalar.json"
    entries = [
        _entry("src_bbbbbbbbbbbbbbbbbbbb", "B"),
        _entry("src_aaaaaaaaaaaaaaaaaaaa", "A"),
    ]

    write_catalog(path, "Shandalar", entries)
    first = path.read_bytes()
    write_catalog(path, "Shandalar", list(reversed(entries)))

    assert path.read_bytes() == first
    assert path.read_text(encoding="utf-8").endswith("\n")

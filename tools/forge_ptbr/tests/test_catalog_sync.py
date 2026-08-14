from pathlib import Path

import pytest

from forge_ptbr.catalog.model import TranslationStatus
from forge_ptbr.catalog.store import load_catalog, write_catalog
from forge_ptbr.catalog.sync import sync_catalogs
from forge_ptbr.model import FieldKind, InventoryEntry, ScanReport, SourceLocation, source_text_hash


def _inventory(
    source_id: str,
    text: str,
    *,
    kind: FieldKind = FieldKind.LOCALIZABLE_NEEDS_HOOK,
    plane: str = "Shandalar",
    tokens: tuple[str, ...] = (),
) -> InventoryEntry:
    return InventoryEntry(
        source_id=source_id,
        location=SourceLocation(
            plane=plane,
            relative_file=Path("world/quests.json"),
            json_path="$[0].name",
            resource_type="quests",
        ),
        field_name="name",
        source_text=text,
        source_hash=source_text_hash(text),
        kind=kind,
        tokens=tokens,
    )


def test_first_sync_creates_only_localizable_entries(tmp_path: Path) -> None:
    report = ScanReport(entries=[
        _inventory("src_11111111111111111111", "Visible"),
        _inventory("src_22222222222222222222", "Logic", kind=FieldKind.PROTECTED),
        _inventory("src_33333333333333333333", "Unknown", kind=FieldKind.UNKNOWN),
    ])

    summary = sync_catalogs(report, tmp_path)
    _, entries = load_catalog(tmp_path / "shandalar.json")

    assert [entry.source_id for entry in entries] == ["src_11111111111111111111"]
    assert entries[0].status is TranslationStatus.NEW
    assert summary.new == 1


def test_identical_sync_preserves_approved_translation_byte_for_byte(tmp_path: Path) -> None:
    source = _inventory("src_11111111111111111111", "Visible")
    report = ScanReport(entries=[source])
    sync_catalogs(report, tmp_path)
    _, entries = load_catalog(tmp_path / "shandalar.json")
    entries[0].translation = "Visível"
    entries[0].status = TranslationStatus.APPROVED
    entries[0].reviewed = True
    write_catalog(tmp_path / "shandalar.json", "Shandalar", entries)
    before = (tmp_path / "shandalar.json").read_bytes()

    sync_catalogs(report, tmp_path)
    _, synced = load_catalog(tmp_path / "shandalar.json")

    assert synced[0].translation == "Visível"
    assert synced[0].status is TranslationStatus.APPROVED
    assert synced[0].reviewed is True
    assert (tmp_path / "shandalar.json").read_bytes() == before


def test_same_source_hash_refreshes_scanner_metadata_without_losing_review(tmp_path: Path) -> None:
    source = _inventory("src_11111111111111111111", "Hello {playerName}", tokens=())
    sync_catalogs(ScanReport(entries=[source]), tmp_path)
    _, entries = load_catalog(tmp_path / "shandalar.json")
    entries[0].translation = "Olá {playerName}"
    entries[0].status = TranslationStatus.APPROVED
    entries[0].reviewed = True
    write_catalog(tmp_path / "shandalar.json", "Shandalar", entries)

    rescanned = _inventory(
        "src_11111111111111111111",
        "Hello {playerName}",
        tokens=("{playerName}",),
    )
    sync_catalogs(ScanReport(entries=[rescanned]), tmp_path)
    _, synced = load_catalog(tmp_path / "shandalar.json")

    assert synced[0].tokens == ("{playerName}",)
    assert synced[0].translation == "Olá {playerName}"
    assert synced[0].status is TranslationStatus.APPROVED
    assert synced[0].reviewed is True


def test_changed_english_marks_entry_changed_and_keeps_candidate(tmp_path: Path) -> None:
    old = _inventory("src_11111111111111111111", "Old English")
    sync_catalogs(ScanReport(entries=[old]), tmp_path)
    _, entries = load_catalog(tmp_path / "shandalar.json")
    entries[0].translation = "Português anterior"
    entries[0].status = TranslationStatus.APPROVED
    entries[0].reviewed = True
    write_catalog(tmp_path / "shandalar.json", "Shandalar", entries)

    new = _inventory("src_11111111111111111111", "Changed English")
    sync_catalogs(ScanReport(entries=[new]), tmp_path)
    _, synced = load_catalog(tmp_path / "shandalar.json")

    assert synced[0].source_text == "Changed English"
    assert synced[0].translation == "Português anterior"
    assert synced[0].status is TranslationStatus.CHANGED
    assert synced[0].reviewed is False
    assert synced[0].quality_score is None


def test_removed_or_newly_protected_source_becomes_obsolete(tmp_path: Path) -> None:
    visible = _inventory("src_11111111111111111111", "Visible")
    sync_catalogs(ScanReport(entries=[visible]), tmp_path)

    protected = _inventory(
        "src_11111111111111111111",
        "Visible",
        kind=FieldKind.PROTECTED,
    )
    sync_catalogs(ScanReport(entries=[protected]), tmp_path)
    _, entries = load_catalog(tmp_path / "shandalar.json")
    assert entries[0].status is TranslationStatus.OBSOLETE
    assert "source_not_localizable" in entries[0].quality_flags

    sync_catalogs(ScanReport(entries=[]), tmp_path)
    _, entries = load_catalog(tmp_path / "shandalar.json")
    assert entries[0].status is TranslationStatus.OBSOLETE


def test_duplicate_localization_keys_fail_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "forge_ptbr.catalog.sync.make_localization_key",
        lambda source_id, plane, resource_type, field_name: "adv.collision",
    )
    report = ScanReport(entries=[
        _inventory("src_11111111111111111111", "One"),
        _inventory("src_22222222222222222222", "Two"),
    ])

    with pytest.raises(ValueError, match="Duplicate localization key"):
        sync_catalogs(report, tmp_path)

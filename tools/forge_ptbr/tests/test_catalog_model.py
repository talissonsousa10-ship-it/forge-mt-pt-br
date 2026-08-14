from forge_ptbr.catalog.model import CatalogEntry, TranslationStatus


def test_translation_status_values_are_stable_lowercase() -> None:
    assert [status.value for status in TranslationStatus] == [
        "new",
        "auto",
        "review",
        "approved",
        "changed",
        "obsolete",
    ]


def test_catalog_entry_defaults_to_new_unreviewed_translation() -> None:
    entry = CatalogEntry(
        source_id="src_1234567890abcdef1234",
        localization_key="adv.shandalar.quests.name.90abcdef1234",
        plane="Shandalar",
        resource_type="quests",
        relative_file="world/quests.json",
        json_path="$[0].name",
        field_name="name",
        source_text="A New Quest",
        source_hash="abc123",
    )

    assert entry.translation == ""
    assert entry.status is TranslationStatus.NEW
    assert entry.reviewed is False
    assert entry.quality_score is None
    assert entry.quality_flags == ()
    assert entry.tokens == ()

from pathlib import Path

from forge_ptbr.model import FieldKind, SourceLocation, stable_source_id


def test_source_id_is_context_based_not_translation_based() -> None:
    location = SourceLocation(
        plane="Shandalar",
        relative_file=Path("world/quests.json"),
        json_path="$[0].offerDialog.text",
        resource_type="quest",
    )

    first = stable_source_id(location, "Hello $(playername)")
    second = stable_source_id(location, "Hello $(playername)")

    assert first == second
    assert first.startswith("src_")
    assert FieldKind.UNKNOWN.value == "unknown"

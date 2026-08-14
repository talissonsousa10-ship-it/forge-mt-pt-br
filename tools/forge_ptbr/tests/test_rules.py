import json
from pathlib import Path

from forge_ptbr.model import FieldKind, SourceLocation, source_text_hash, stable_source_id
from forge_ptbr.scanner.json_walk import walk_json_strings
from forge_ptbr.scanner.rules import classify_json_field


FIXTURES = Path(__file__).parent / "fixtures"


def test_source_id_is_context_based_not_translation_based() -> None:
    location = SourceLocation(
        plane="Shandalar",
        relative_file=Path("world/quests.json"),
        json_path="$[0].offerDialog.text",
        resource_type="quest",
    )

    first = stable_source_id(location, "Hello $(playername)")
    second = stable_source_id(location, "Changed upstream English")

    assert first == second
    assert source_text_hash("Hello $(playername)") != source_text_hash("Changed upstream English")
    assert first.startswith("src_")
    assert FieldKind.UNKNOWN.value == "unknown"


def _classified(filename: str):
    data = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
    relative = Path("world") / filename.replace("_sample", "")
    return {
        field.json_path: classify_json_field(relative, field)
        for field in walk_json_strings(data)
        if field.value
    }


def test_quest_rules_separate_visible_text_from_logic() -> None:
    fields = _classified("quests_sample.json")
    assert fields["$[0].name"] is FieldKind.LOCALIZABLE_NEEDS_HOOK
    assert fields["$[0].description"] is FieldKind.LOCALIZABLE_NEEDS_HOOK
    assert fields["$[0].offerDialog.text"] is FieldKind.LOCALIZABLE_EXISTING_HOOK
    assert fields["$[0].offerDialog.options[0].name"] is FieldKind.LOCALIZABLE_EXISTING_HOOK
    assert fields["$[0].offerDialog.options[0].action[0].setQuestFlag.key"] is FieldKind.PROTECTED
    assert fields["$[0].stages[0].objective"] is FieldKind.PROTECTED


def test_shop_card_selector_is_never_localized() -> None:
    fields = _classified("shops_sample.json")
    assert fields["$[0].name"] is FieldKind.PROTECTED
    assert fields["$[0].description"] is FieldKind.LOCALIZABLE_NEEDS_HOOK
    assert fields["$[0].rewards[0].cardText"] is FieldKind.PROTECTED
    assert fields["$[0].rewards[1].cardName"] is FieldKind.PROTECTED


def test_item_dialog_uses_existing_dialog_hook_but_item_metadata_needs_hook() -> None:
    fields = _classified("items_sample.json")
    assert fields["$[0].name"] is FieldKind.LOCALIZABLE_NEEDS_HOOK
    assert fields["$[0].description"] is FieldKind.LOCALIZABLE_NEEDS_HOOK
    assert fields["$[0].iconName"] is FieldKind.PROTECTED
    assert fields["$[0].dialogOnUse.text"] is FieldKind.LOCALIZABLE_EXISTING_HOOK
    assert fields["$[0].dialogOnUse.options[0].condition[0].checkQuestFlag"] is FieldKind.PROTECTED

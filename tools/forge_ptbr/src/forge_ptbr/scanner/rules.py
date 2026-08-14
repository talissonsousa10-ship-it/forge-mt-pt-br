from pathlib import Path

from forge_ptbr.model import FieldKind
from forge_ptbr.scanner.json_walk import JsonStringField


PROTECTED_KEYS = {
    "id", "objective", "issueQuest", "advanceQuestFlag", "advanceMapFlag",
    "checkQuestFlag", "checkMapFlag", "POIReference", "POIToken", "sourceID",
    "mapFlag", "sprite", "spriteAtlas", "overlaySprite", "iconName", "cardText",
    "cardName", "commandOnUse", "equipmentSlot", "type",
}
PROTECTED_CONTAINER_KEYS = {
    "setQuestFlag", "setMapFlag", "questSourceTags", "questEnemyTags", "questPOITags",
    "enemyTags", "enemyExcludeTags", "POITags", "itemNames", "equipNames", "editions",
    "action", "condition", "rewards",
}
DIALOG_CONTEXTS = {
    "offerDialog", "prologue", "epilogue", "failureDialog", "declinedDialog",
    "dialogOnUse", "options",
}


def _inside_dialog(field: JsonStringField) -> bool:
    return any(part in DIALOG_CONTEXTS for part in field.ancestors)


def classify_json_field(relative_file: Path, field: JsonStringField) -> FieldKind:
    filename = relative_file.name

    if field.key in PROTECTED_KEYS or any(
        part in PROTECTED_CONTAINER_KEYS for part in field.ancestors
    ):
        return FieldKind.PROTECTED

    if _inside_dialog(field) and field.key in {"text", "name"}:
        return FieldKind.LOCALIZABLE_EXISTING_HOOK

    if filename == "quests.json" and field.key in {"name", "description", "rewardDescription"}:
        return FieldKind.LOCALIZABLE_NEEDS_HOOK

    if filename == "items.json" and field.key in {"name", "description"}:
        return FieldKind.LOCALIZABLE_NEEDS_HOOK

    if filename == "shops.json":
        if field.key == "description":
            return FieldKind.LOCALIZABLE_NEEDS_HOOK
        if field.key == "name":
            return FieldKind.PROTECTED

    return FieldKind.UNKNOWN

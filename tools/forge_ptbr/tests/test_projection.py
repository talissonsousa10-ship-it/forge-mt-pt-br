import copy
import json
from pathlib import Path

from forge_ptbr.validator.projection import protected_projection
from forge_ptbr.validator.structural import compare_protected


FIXTURES = Path(__file__).parent / "fixtures"


def test_projection_ignores_localizable_text_but_keeps_logic() -> None:
    source = json.loads((FIXTURES / "quests_sample.json").read_text(encoding="utf-8"))
    translated = copy.deepcopy(source)
    translated[0]["offerDialog"]["text"] = "Texto em português"

    before = protected_projection(Path("world/quests.json"), source)
    after = protected_projection(Path("world/quests.json"), translated)

    assert compare_protected(before, after) == []


def test_projection_detects_quest_flag_mutation() -> None:
    source = json.loads((FIXTURES / "quests_sample.json").read_text(encoding="utf-8"))
    changed = copy.deepcopy(source)
    changed[0]["offerDialog"]["options"][0]["action"][0]["setQuestFlag"]["key"] = "BROKEN_FLAG"

    differences = compare_protected(
        protected_projection(Path("world/quests.json"), source),
        protected_projection(Path("world/quests.json"), changed),
    )

    assert len(differences) == 1
    assert "setQuestFlag.key" in differences[0].path


def test_projection_detects_shop_regex_mutation() -> None:
    source = json.loads((FIXTURES / "shops_sample.json").read_text(encoding="utf-8"))
    changed = copy.deepcopy(source)
    changed[0]["rewards"][0]["cardText"] = "traduzido"

    assert compare_protected(
        protected_projection(Path("world/shops.json"), source),
        protected_projection(Path("world/shops.json"), changed),
    )


def test_projection_detects_numeric_id_mutation() -> None:
    source = json.loads((FIXTURES / "quests_sample.json").read_text(encoding="utf-8"))
    changed = copy.deepcopy(source)
    changed[0]["id"] = 99

    differences = compare_protected(
        protected_projection(Path("world/quests.json"), source),
        protected_projection(Path("world/quests.json"), changed),
    )

    assert len(differences) == 1
    assert differences[0].path == "$[0].id"

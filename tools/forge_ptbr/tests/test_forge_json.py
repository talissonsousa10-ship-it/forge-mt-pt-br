from forge_ptbr.scanner.forge_json import loads_forge_json


def test_loads_forge_json_recovers_missing_member_comma_without_changing_input() -> None:
    source = """{
      \"type\": \"Table\",
      \"height\": 413
      \"fontColor\": \"black\"
    }"""
    original = source

    parsed = loads_forge_json(source)

    assert parsed == {"type": "Table", "height": 413, "fontColor": "black"}
    assert source == original


def test_loads_forge_json_recovers_missing_comma_between_array_objects() -> None:
    source = '''[
      {"name": "quests"}
      {"name": "toggleAward"}
    ]'''

    parsed = loads_forge_json(source)

    assert parsed == [{"name": "quests"}, {"name": "toggleAward"}]

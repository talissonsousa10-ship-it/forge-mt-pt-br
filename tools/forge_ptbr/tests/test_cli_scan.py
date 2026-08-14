import json
from pathlib import Path

from forge_ptbr.cli import main


def test_scan_writes_inventory_and_strict_mode_flags_unknown(tmp_path: Path) -> None:
    repo = tmp_path / "forge"
    adventure = repo / "forge-gui" / "res" / "adventure" / "Shandalar" / "world"
    adventure.mkdir(parents=True)
    (repo / "pom.xml").write_text("<project/>", encoding="utf-8")
    (adventure / "quests.json").write_text(
        json.dumps([
            {
                "id": 1,
                "name": "Quest",
                "description": "Description",
                "offerDialog": {"text": "Hello $(playername)"},
                "newUpstreamTextField": "Needs classification",
            }
        ]),
        encoding="utf-8",
    )
    output = tmp_path / "inventory.json"

    exit_code = main(["scan", "--repo", str(repo), "--output", str(output), "--strict"])
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 2
    assert payload["summary"]["unknown"] == 1
    assert any(entry["source_text"] == "Hello $(playername)" for entry in payload["entries"])


def test_scan_parse_error_names_the_resource(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "forge"
    adventure = repo / "forge-gui" / "res" / "adventure" / "Crystal_Kingdoms" / "world"
    adventure.mkdir(parents=True)
    (repo / "pom.xml").write_text("<project/>", encoding="utf-8")
    (adventure / "broken.json").write_text('{"a": 1 "b": 2}', encoding="utf-8")

    exit_code = main(["scan", "--repo", str(repo), "--output", str(tmp_path / "out.json")])
    stderr = capsys.readouterr().err

    assert exit_code == 1
    assert "Crystal_Kingdoms/world/broken.json" in stderr

import json
from pathlib import Path

from forge_ptbr.cli import main


def _mini_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "forge"
    world = repo / "forge-gui" / "res" / "adventure" / "Shandalar" / "world"
    world.mkdir(parents=True)
    (repo / "pom.xml").write_text("<project/>", encoding="utf-8")
    (world / "quests.json").write_text(
        json.dumps([{"id": 1, "name": "Quest", "description": "Defeat the enemy."}]),
        encoding="utf-8",
    )
    return repo


def test_catalog_sync_writes_localizable_catalog_without_provider(tmp_path: Path) -> None:
    repo = _mini_repo(tmp_path)
    catalogs = tmp_path / "catalogs"

    exit_code = main(["catalog-sync", "--repo", str(repo), "--catalogs-dir", str(catalogs)])

    assert exit_code == 0
    payload = json.loads((catalogs / "shandalar.json").read_text(encoding="utf-8"))
    assert len(payload["entries"]) == 2
    assert {entry["status"] for entry in payload["entries"]} == {"new"}

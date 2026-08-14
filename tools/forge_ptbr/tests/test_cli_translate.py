import json
from pathlib import Path

from forge_ptbr.cli import main


class FakeProvider:
    name = "fake"

    def __init__(self, ready: bool = True) -> None:
        self.ready = ready

    def is_ready(self) -> bool:
        return self.ready

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        return "Tradução"


def _mini_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "forge"
    world = repo / "forge-gui" / "res" / "adventure" / "Shandalar" / "world"
    world.mkdir(parents=True)
    (repo / "pom.xml").write_text("<project/>", encoding="utf-8")
    (world / "quests.json").write_text(
        json.dumps([{"id": 1, "name": "Quest", "description": "Defeat the enemy."}]),
        encoding="utf-8",
    )
    glossary = repo / "translations" / "glossary" / "mtg-pt-BR.json"
    glossary.parent.mkdir(parents=True)
    glossary.write_text('{"schema_version":1,"terms":[]}', encoding="utf-8")
    catalogs = repo / "translations" / "catalogs"
    assert main(["catalog-sync", "--repo", str(repo), "--catalogs-dir", str(catalogs)]) == 0
    return repo, catalogs, glossary


def test_translate_uses_provider_and_never_auto_approves(tmp_path: Path, monkeypatch) -> None:
    repo, catalogs, glossary = _mini_repo(tmp_path)
    monkeypatch.setattr("forge_ptbr.cli.make_provider", lambda name: FakeProvider())

    exit_code = main([
        "translate", "--repo", str(repo), "--catalogs-dir", str(catalogs),
        "--glossary", str(glossary), "--provider", "fake",
    ])

    assert exit_code == 0
    payload = json.loads((catalogs / "shandalar.json").read_text(encoding="utf-8"))
    assert all(entry["translation"] == "Tradução" for entry in payload["entries"])
    assert all(entry["status"] in {"auto", "review"} for entry in payload["entries"])
    assert all(entry["status"] != "approved" for entry in payload["entries"])


def test_unready_provider_returns_3_without_mutating_catalog(tmp_path: Path, monkeypatch) -> None:
    repo, catalogs, glossary = _mini_repo(tmp_path)
    path = catalogs / "shandalar.json"
    before = path.read_bytes()
    monkeypatch.setattr("forge_ptbr.cli.make_provider", lambda name: FakeProvider(ready=False))

    exit_code = main([
        "translate", "--repo", str(repo), "--catalogs-dir", str(catalogs),
        "--glossary", str(glossary), "--provider", "fake",
    ])

    assert exit_code == 3
    assert path.read_bytes() == before

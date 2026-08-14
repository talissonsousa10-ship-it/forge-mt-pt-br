from pathlib import Path

from forge_ptbr.scanner.discovery import discover_resources


def test_discovery_is_sorted_and_keeps_plane_context(tmp_path: Path) -> None:
    root = tmp_path / "adventure"
    (root / "Shandalar" / "world").mkdir(parents=True)
    (root / "common" / "world").mkdir(parents=True)
    (root / "Shandalar" / "world" / "quests.json").write_text("[]", encoding="utf-8")
    (root / "Shandalar" / "world" / "town_names.txt").write_text("Town", encoding="utf-8")
    (root / "common" / "world" / "items.json").write_text("[]", encoding="utf-8")
    (root / "Shandalar" / "world" / "icon.png").write_bytes(b"png")

    resources = discover_resources(root)

    assert [(r.plane, r.relative_file.as_posix()) for r in resources] == [
        ("common", "world/items.json"),
        ("Shandalar", "world/quests.json"),
        ("Shandalar", "world/town_names.txt"),
    ]

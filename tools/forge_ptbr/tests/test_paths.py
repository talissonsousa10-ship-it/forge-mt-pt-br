from pathlib import Path

import pytest

from forge_ptbr.paths import adventure_root, find_repo_root


def test_find_repo_root_walks_up_to_forge_marker(tmp_path: Path) -> None:
    repo = tmp_path / "forge"
    nested = repo / "tools" / "forge_ptbr" / "work"
    (repo / "forge-gui" / "res" / "adventure").mkdir(parents=True)
    (repo / "pom.xml").write_text("<project/>", encoding="utf-8")
    nested.mkdir(parents=True)

    assert find_repo_root(nested) == repo
    assert adventure_root(repo) == repo / "forge-gui" / "res" / "adventure"


def test_find_repo_root_fails_outside_forge_repository(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Forge repository root"):
        find_repo_root(tmp_path)

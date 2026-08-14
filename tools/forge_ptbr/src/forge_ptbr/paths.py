from pathlib import Path


def _is_forge_root(path: Path) -> bool:
    return (path / "pom.xml").is_file() and (
        path / "forge-gui" / "res" / "adventure"
    ).is_dir()


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if _is_forge_root(candidate):
            return candidate
    raise FileNotFoundError(f"Forge repository root not found from {start}")


def adventure_root(repo_root: Path) -> Path:
    path = repo_root / "forge-gui" / "res" / "adventure"
    if not path.is_dir():
        raise FileNotFoundError(f"Adventure resource root not found: {path}")
    return path

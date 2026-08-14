from dataclasses import dataclass
from pathlib import Path


SUPPORTED_TEXT_SUFFIXES = {".json", ".txt", ".tmx", ".xml"}


@dataclass(frozen=True, slots=True)
class ResourceFile:
    plane: str
    path: Path
    relative_file: Path
    suffix: str


def discover_resources(adventure_dir: Path) -> list[ResourceFile]:
    resources: list[ResourceFile] = []
    plane_dirs = sorted(
        (p for p in adventure_dir.iterdir() if p.is_dir()),
        key=lambda p: p.name.casefold(),
    )
    for plane_dir in plane_dirs:
        for path in sorted(plane_dir.rglob("*"), key=lambda p: p.as_posix().casefold()):
            if path.is_file() and path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES:
                resources.append(
                    ResourceFile(
                        plane=plane_dir.name,
                        path=path,
                        relative_file=path.relative_to(plane_dir),
                        suffix=path.suffix.lower(),
                    )
                )
    return resources

from pathlib import Path

from forge_ptbr.model import FieldKind
from forge_ptbr.scanner.json_walk import JsonStringField
from forge_ptbr.scanner.rules import classify_json_field


_LOCALIZABLE = {
    FieldKind.LOCALIZABLE_EXISTING_HOOK,
    FieldKind.LOCALIZABLE_NEEDS_HOOK,
}


def protected_projection(relative_file: Path, document: object) -> dict[str, object]:
    projection: dict[str, object] = {}

    def visit(node: object, path: str, ancestors: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                child_path = f"{path}.{key}"
                if isinstance(child, str):
                    field = JsonStringField(child_path, key, child, ancestors)
                    if classify_json_field(relative_file, field) not in _LOCALIZABLE:
                        projection[child_path] = child
                elif isinstance(child, (dict, list)):
                    visit(child, child_path, ancestors + (key,))
                else:
                    projection[child_path] = child
        elif isinstance(node, list):
            for index, child in enumerate(node):
                child_path = f"{path}[{index}]"
                if isinstance(child, (dict, list)):
                    visit(child, child_path, ancestors)
                else:
                    projection[child_path] = child

    visit(document, "$", ())
    return projection

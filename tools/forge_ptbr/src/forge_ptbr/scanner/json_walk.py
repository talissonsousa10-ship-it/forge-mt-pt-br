from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JsonStringField:
    json_path: str
    key: str
    value: str
    ancestors: tuple[str, ...]


def walk_json_strings(value: object) -> list[JsonStringField]:
    found: list[JsonStringField] = []

    def visit(node: object, path: str, ancestors: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                child_path = f"{path}.{key}"
                if isinstance(child, str):
                    found.append(JsonStringField(child_path, key, child, ancestors))
                else:
                    visit(child, child_path, ancestors + (key,))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, f"{path}[{index}]", ancestors)

    visit(value, "$", ())
    return found

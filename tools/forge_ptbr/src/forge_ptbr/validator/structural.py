from dataclasses import dataclass


_MISSING = object()


@dataclass(frozen=True, slots=True)
class StructuralDifference:
    path: str
    before: object
    after: object


def compare_protected(
    before: dict[str, object],
    after: dict[str, object],
) -> list[StructuralDifference]:
    differences: list[StructuralDifference] = []
    for path in sorted(set(before) | set(after)):
        before_value = before.get(path, _MISSING)
        after_value = after.get(path, _MISSING)
        if before_value != after_value:
            differences.append(
                StructuralDifference(
                    path,
                    None if before_value is _MISSING else before_value,
                    None if after_value is _MISSING else after_value,
                )
            )
    return differences

# Forge PT-BR Core Scanner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first safe, testable PT-BR tooling slice: a cross-platform Python package and CLI that discovers Forge Adventure JSON resources, classifies player-visible versus functional fields, inventories translatable text, protects runtime tokens, and proves that protected game logic remains unchanged.

**Architecture:** The tooling lives under `tools/forge_ptbr/` and uses a small shared domain model plus resource-specific classifiers. The scanner never rewrites Forge resources in this plan; it only reads and reports. Safety is enforced by typed field classification, an UNKNOWN default, token-preservation utilities, and protected structural projections that later generators must preserve.

**Tech Stack:** Python 3.11+, standard library (`argparse`, `dataclasses`, `enum`, `json`, `pathlib`, `hashlib`, `re`), `pytest` for tests, GitHub Actions matrix on Windows/Linux/macOS.

## Global Constraints

- **Do not corrupt game logic.** Translation must never alter identifiers, quest flags, regexes, filenames, script commands, card selectors, tags, resource paths, objective enums, card names used as functional identifiers, or other logic-bearing values.
- **English remains the source fallback.** The original Forge English text must remain available wherever possible.
- **Localization is data-driven.** New localization keys are preferred over destructive replacement of source strings.
- **Translation source is separate from generated Forge artifacts.** Human-reviewed translation data is the source of truth; patched Forge resources are reproducible build output.
- **Upstream maintenance is first-class.** New and changed Forge text must be detected incrementally rather than forcing full retranslation.
- **Mandatory cost is R$ 0.** The core workflow works locally/offline after initial model setup. Paid/cloud AI providers are optional review plugins only.
- **Cross-platform from the start.** Windows, Linux and macOS are supported design targets.
- **CLI and GUI share one engine.** The GUI is a thin frontend over the same application services exposed by the CLI.
- Work only on `ptbr-adventure`; do not add PT-BR implementation commits to `master`.
- This plan performs no mass translation and no Java-side localization changes.

## Plan Sequence

The approved specification is intentionally broader than one safe implementation batch. Split execution into four independently reviewable plans:

1. **This plan — Core Scanner & Safety Foundation:** Python package, resource discovery, typed JSON classification, token protection, inventory report, structural safety validator, CI.
2. **Translation Engine & Review Data:** deterministic keys, translation-memory schema, Magic glossary, Argos provider adapter, quality flags, lifecycle states.
3. **Forge Localization Integration & Shandalar Vertical Slice:** `loctext`/`locname` generation, minimal Java localization hooks for unsupported types, generated `pt-BR.properties`, one end-to-end Shandalar slice.
4. **User Workflow & Scale:** `doctor`, build/apply flow, review GUI, upstream delta detection, all-plane expansion.

The next plan should be written only after this scanner contract is implemented and reviewed, because later plans depend on the exact inventory and safety interfaces defined here.

## File Structure for This Plan

```text
tools/forge_ptbr/
├── pyproject.toml
├── src/forge_ptbr/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── model.py
│   ├── paths.py
│   ├── tokens.py
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── discovery.py
│   │   ├── json_walk.py
│   │   ├── rules.py
│   │   └── service.py
│   ├── reporting/
│   │   ├── __init__.py
│   │   └── json_report.py
│   └── validator/
│       ├── __init__.py
│       ├── projection.py
│       └── structural.py
└── tests/
    ├── fixtures/
    │   ├── quests_sample.json
    │   ├── shops_sample.json
    │   └── items_sample.json
    ├── test_paths.py
    ├── test_discovery.py
    ├── test_rules.py
    ├── test_tokens.py
    ├── test_projection.py
    └── test_cli_scan.py

.github/workflows/ptbr-tools.yml
```

Responsibilities are intentionally narrow: `rules.py` owns semantic classification, `json_walk.py` owns traversal, `service.py` orchestrates scanning, `projection.py` extracts protected data, and the CLI is only an adapter.

---

### Task 1: Create the installable Python tooling skeleton and repository discovery

**Files:**
- Create: `tools/forge_ptbr/pyproject.toml`
- Create: `tools/forge_ptbr/src/forge_ptbr/__init__.py`
- Create: `tools/forge_ptbr/src/forge_ptbr/__main__.py`
- Create: `tools/forge_ptbr/src/forge_ptbr/paths.py`
- Create: `tools/forge_ptbr/tests/test_paths.py`

**Interfaces:**
- Produces: `forge_ptbr.paths.find_repo_root(start: pathlib.Path) -> pathlib.Path`
- Produces: `forge_ptbr.paths.adventure_root(repo_root: pathlib.Path) -> pathlib.Path`
- Later tasks consume these functions rather than duplicating path assumptions.

- [ ] **Step 1: Write the failing repository-discovery tests**

```python
# tools/forge_ptbr/tests/test_paths.py
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
```

- [ ] **Step 2: Run the focused test and verify failure**

Run from repository root:

```bash
python -m pip install -e tools/forge_ptbr
python -m pytest tools/forge_ptbr/tests/test_paths.py -v
```

Expected before implementation: import/build failure because `pyproject.toml` and `forge_ptbr.paths` do not exist.

- [ ] **Step 3: Add the package metadata and minimal path implementation**

```toml
# tools/forge_ptbr/pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "forge-ptbr"
version = "0.1.0"
description = "Safe Brazilian Portuguese localization tooling for Forge Adventure"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8"]

[project.scripts]
forge-ptbr = "forge_ptbr.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```python
# tools/forge_ptbr/src/forge_ptbr/paths.py
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
```

`__init__.py` contains only `__version__ = "0.1.0"`. `__main__.py` imports `main` from `forge_ptbr.cli` and exits with `raise SystemExit(main())`; create a temporary `cli.py` whose `main()` returns `0` so editable installation succeeds.

- [ ] **Step 4: Install in editable mode and run the tests**

```bash
python -m pip install -e "tools/forge_ptbr[dev]"
python -m pytest tools/forge_ptbr/tests/test_paths.py -v
```

Expected: 2 tests pass on the current platform.

- [ ] **Step 5: Commit the independently usable package skeleton**

```bash
git add tools/forge_ptbr
git commit -m "feat(ptbr): add cross-platform tooling skeleton"
```

---

### Task 2: Define the scanner domain model and stable source identity

**Files:**
- Create: `tools/forge_ptbr/src/forge_ptbr/model.py`
- Create: `tools/forge_ptbr/tests/test_rules.py` with model identity tests first; classification assertions are added in Task 4.

**Interfaces:**
- Produces: `FieldKind`
- Produces: `SourceLocation`
- Produces: `InventoryEntry`
- Produces: `ScanReport`
- Produces: `stable_source_id(location: SourceLocation, source_text: str) -> str`
- Later translation/update plans rely on the stable ID and `source_hash` contract.

- [ ] **Step 1: Write failing model tests**

```python
# initial content in tools/forge_ptbr/tests/test_rules.py
from pathlib import Path

from forge_ptbr.model import FieldKind, SourceLocation, stable_source_id


def test_source_id_is_context_based_not_translation_based() -> None:
    location = SourceLocation(
        plane="Shandalar",
        relative_file=Path("world/quests.json"),
        json_path="$[0].offerDialog.text",
        resource_type="quest",
    )

    first = stable_source_id(location, "Hello $(playername)")
    second = stable_source_id(location, "Hello $(playername)")

    assert first == second
    assert first.startswith("src_")
    assert FieldKind.UNKNOWN.value == "unknown"
```

- [ ] **Step 2: Run and verify the test fails**

```bash
python -m pytest tools/forge_ptbr/tests/test_rules.py -v
```

Expected: FAIL because `forge_ptbr.model` is missing.

- [ ] **Step 3: Implement the domain model**

```python
# tools/forge_ptbr/src/forge_ptbr/model.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from pathlib import Path


class FieldKind(str, Enum):
    LOCALIZABLE_EXISTING_HOOK = "localizable_existing_hook"
    LOCALIZABLE_NEEDS_HOOK = "localizable_needs_hook"
    PROTECTED = "protected"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    plane: str
    relative_file: Path
    json_path: str
    resource_type: str


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    source_id: str
    location: SourceLocation
    field_name: str
    source_text: str
    source_hash: str
    kind: FieldKind
    tokens: tuple[str, ...] = ()


@dataclass(slots=True)
class ScanReport:
    entries: list[InventoryEntry] = field(default_factory=list)
    scanned_files: int = 0
    unsupported_files: list[str] = field(default_factory=list)

    @property
    def unknown_entries(self) -> list[InventoryEntry]:
        return [entry for entry in self.entries if entry.kind is FieldKind.UNKNOWN]


def source_text_hash(source_text: str) -> str:
    return sha256(source_text.encode("utf-8")).hexdigest()


def stable_source_id(location: SourceLocation, source_text: str) -> str:
    identity = "|".join(
        [location.plane, location.relative_file.as_posix(), location.json_path, location.resource_type]
    )
    digest = sha256(identity.encode("utf-8")).hexdigest()[:20]
    return f"src_{digest}"
```

Note: `source_text` is intentionally not included in the stable ID; changed English text keeps the same identity and receives a different `source_hash` in later upstream-delta logic.

- [ ] **Step 4: Run the focused tests**

```bash
python -m pytest tools/forge_ptbr/tests/test_rules.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit the scanner contract**

```bash
git add tools/forge_ptbr/src/forge_ptbr/model.py tools/forge_ptbr/tests/test_rules.py
git commit -m "feat(ptbr): define scanner inventory model"
```

---

### Task 3: Discover Adventure resource files without interpreting them

**Files:**
- Create: `tools/forge_ptbr/src/forge_ptbr/scanner/__init__.py`
- Create: `tools/forge_ptbr/src/forge_ptbr/scanner/discovery.py`
- Create: `tools/forge_ptbr/tests/test_discovery.py`

**Interfaces:**
- Produces: `ResourceFile(plane: str, path: Path, relative_file: Path, suffix: str)`
- Produces: `discover_resources(adventure_dir: Path) -> list[ResourceFile]`
- Discovery does not decide whether a string is translatable.

- [ ] **Step 1: Write the failing discovery test**

```python
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
        ("Shandalar", "world/quests.json"),
        ("Shandalar", "world/town_names.txt"),
        ("common", "world/items.json"),
    ]
```

- [ ] **Step 2: Verify failure**

```bash
python -m pytest tools/forge_ptbr/tests/test_discovery.py -v
```

Expected: FAIL because discovery module does not exist.

- [ ] **Step 3: Implement deterministic resource discovery**

```python
# tools/forge_ptbr/src/forge_ptbr/scanner/discovery.py
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
    for plane_dir in sorted((p for p in adventure_dir.iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
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
```

- [ ] **Step 4: Run discovery tests**

```bash
python -m pytest tools/forge_ptbr/tests/test_discovery.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit discovery separately from semantic parsing**

```bash
git add tools/forge_ptbr/src/forge_ptbr/scanner tools/forge_ptbr/tests/test_discovery.py
git commit -m "feat(ptbr): discover Adventure text resources"
```

---

### Task 4: Implement typed JSON traversal and safe resource-specific field rules

**Files:**
- Create: `tools/forge_ptbr/src/forge_ptbr/scanner/json_walk.py`
- Create: `tools/forge_ptbr/src/forge_ptbr/scanner/rules.py`
- Modify: `tools/forge_ptbr/tests/test_rules.py`
- Create: `tools/forge_ptbr/tests/fixtures/quests_sample.json`
- Create: `tools/forge_ptbr/tests/fixtures/shops_sample.json`
- Create: `tools/forge_ptbr/tests/fixtures/items_sample.json`

**Interfaces:**
- Produces: `JsonStringField(json_path: str, key: str, value: str, ancestors: tuple[str, ...])`
- Produces: `walk_json_strings(value: object) -> list[JsonStringField]`
- Produces: `classify_json_field(relative_file: Path, field: JsonStringField) -> FieldKind`
- UNKNOWN is the mandatory fallback for non-empty strings not covered by an explicit rule.

- [ ] **Step 1: Add minimal fixtures copied from the real Forge shapes and write failing classification tests**

`quests_sample.json` must contain one quest with `id`, `name`, `description`, `offerDialog.text`, an option `name`, `setQuestFlag.key`, `issueQuest`, a stage `name`, stage `description`, `objective`, and `enemyTags`. `shops_sample.json` must contain `name`, `description`, `sprite`, `cardText`, and `cardName`. `items_sample.json` must contain item `name`, `description`, `iconName`, `dialogOnUse.text`, option `name`, and `checkQuestFlag`.

```python
# append to tools/forge_ptbr/tests/test_rules.py
import json
from pathlib import Path

from forge_ptbr.scanner.json_walk import walk_json_strings
from forge_ptbr.scanner.rules import classify_json_field


FIXTURES = Path(__file__).parent / "fixtures"


def _classified(filename: str):
    data = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
    relative = Path("world") / filename.replace("_sample", "")
    return {
        field.json_path: classify_json_field(relative, field)
        for field in walk_json_strings(data)
        if field.value
    }


def test_quest_rules_separate_visible_text_from_logic() -> None:
    fields = _classified("quests_sample.json")
    assert fields["$[0].name"] is FieldKind.LOCALIZABLE_NEEDS_HOOK
    assert fields["$[0].description"] is FieldKind.LOCALIZABLE_NEEDS_HOOK
    assert fields["$[0].offerDialog.text"] is FieldKind.LOCALIZABLE_EXISTING_HOOK
    assert fields["$[0].offerDialog.options[0].name"] is FieldKind.LOCALIZABLE_EXISTING_HOOK
    assert fields["$[0].offerDialog.options[0].action[0].setQuestFlag.key"] is FieldKind.PROTECTED
    assert fields["$[0].stages[0].objective"] is FieldKind.PROTECTED


def test_shop_card_selector_is_never_localized() -> None:
    fields = _classified("shops_sample.json")
    assert fields["$[0].name"] is FieldKind.PROTECTED
    assert fields["$[0].description"] is FieldKind.LOCALIZABLE_NEEDS_HOOK
    assert fields["$[0].rewards[0].cardText"] is FieldKind.PROTECTED
    assert fields["$[0].rewards[1].cardName"] is FieldKind.PROTECTED


def test_item_dialog_uses_existing_dialog_hook_but_item_metadata_needs_hook() -> None:
    fields = _classified("items_sample.json")
    assert fields["$[0].name"] is FieldKind.LOCALIZABLE_NEEDS_HOOK
    assert fields["$[0].description"] is FieldKind.LOCALIZABLE_NEEDS_HOOK
    assert fields["$[0].iconName"] is FieldKind.PROTECTED
    assert fields["$[0].dialogOnUse.text"] is FieldKind.LOCALIZABLE_EXISTING_HOOK
    assert fields["$[0].dialogOnUse.options[0].condition[0].checkQuestFlag"] is FieldKind.PROTECTED
```

- [ ] **Step 2: Run and confirm semantic tests fail**

```bash
python -m pytest tools/forge_ptbr/tests/test_rules.py -v
```

Expected: FAIL due to missing walker/rules.

- [ ] **Step 3: Implement the generic JSON string walker**

```python
# tools/forge_ptbr/src/forge_ptbr/scanner/json_walk.py
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
```

- [ ] **Step 4: Implement explicit resource rules with PROTECTED and UNKNOWN defaults**

`rules.py` must use the resource filename plus path context; do not classify solely by key name.

```python
# tools/forge_ptbr/src/forge_ptbr/scanner/rules.py
from pathlib import Path

from forge_ptbr.model import FieldKind
from forge_ptbr.scanner.json_walk import JsonStringField


PROTECTED_KEYS = {
    "id", "objective", "issueQuest", "advanceQuestFlag", "advanceMapFlag",
    "checkQuestFlag", "checkMapFlag", "POIReference", "POIToken", "sourceID",
    "mapFlag", "sprite", "spriteAtlas", "overlaySprite", "iconName", "cardText",
    "cardName", "commandOnUse", "equipmentSlot", "type",
}
PROTECTED_CONTAINER_KEYS = {
    "setQuestFlag", "setMapFlag", "questSourceTags", "questEnemyTags", "questPOITags",
    "enemyTags", "enemyExcludeTags", "POITags", "itemNames", "equipNames", "editions",
    "action", "condition", "rewards",
}
DIALOG_CONTEXTS = {"offerDialog", "prologue", "epilogue", "failureDialog", "declinedDialog", "dialogOnUse", "options"}


def _inside_dialog(field: JsonStringField) -> bool:
    return any(part in DIALOG_CONTEXTS for part in field.ancestors)


def classify_json_field(relative_file: Path, field: JsonStringField) -> FieldKind:
    filename = relative_file.name

    if field.key in PROTECTED_KEYS or any(part in PROTECTED_CONTAINER_KEYS for part in field.ancestors):
        return FieldKind.PROTECTED

    if _inside_dialog(field) and field.key in {"text", "name"}:
        return FieldKind.LOCALIZABLE_EXISTING_HOOK

    if filename == "quests.json":
        if field.key in {"name", "description", "rewardDescription"}:
            return FieldKind.LOCALIZABLE_NEEDS_HOOK

    if filename == "items.json":
        if field.key in {"name", "description"}:
            return FieldKind.LOCALIZABLE_NEEDS_HOOK

    if filename == "shops.json":
        if field.key == "description":
            return FieldKind.LOCALIZABLE_NEEDS_HOOK
        if field.key == "name":
            return FieldKind.PROTECTED

    return FieldKind.UNKNOWN
```

The test fixtures must verify that `action`/`condition` logic cannot be accidentally promoted to localizable merely because nested objects contain a key named `name` or `text`.

Run:

```bash
python -m pytest tools/forge_ptbr/tests/test_rules.py -v
```

Expected: all classification tests pass.

- [ ] **Step 5: Commit the semantic safety boundary**

```bash
git add tools/forge_ptbr/src/forge_ptbr/scanner tools/forge_ptbr/tests/test_rules.py tools/forge_ptbr/tests/fixtures
git commit -m "feat(ptbr): classify Adventure JSON fields safely"
```

---

### Task 5: Protect and validate Forge runtime tokens

**Files:**
- Create: `tools/forge_ptbr/src/forge_ptbr/tokens.py`
- Create: `tools/forge_ptbr/tests/test_tokens.py`

**Interfaces:**
- Produces: `extract_tokens(text: str) -> tuple[str, ...]`
- Produces: `mask_tokens(text: str) -> MaskedText`
- Produces: `restore_tokens(masked_text: str, tokens: tuple[str, ...]) -> str`
- Produces: `validate_token_equivalence(source: str, candidate: str) -> list[str]`

- [ ] **Step 1: Write failing tests for Adventure and formatter tokens**

```python
from forge_ptbr.tokens import extract_tokens, mask_tokens, restore_tokens, validate_token_equivalence


def test_extracts_adventure_and_format_tokens_in_order() -> None:
    text = "Defeat $(enemy_1), meet $(playername), gain {0} gold, then show %s.\\nDone."
    assert extract_tokens(text) == ("$(enemy_1)", "$(playername)", "{0}", "%s", "\\n")


def test_mask_and_restore_round_trip() -> None:
    source = "Return to $(poi_2) with {0} shards."
    masked = mask_tokens(source)
    assert "$(poi_2)" not in masked.text
    assert restore_tokens(masked.text, masked.tokens) == source


def test_validation_reports_missing_or_added_tokens() -> None:
    source = "Defeat $(enemy_1) and gain {0}."
    candidate = "Derrote o inimigo e ganhe {0}."
    errors = validate_token_equivalence(source, candidate)
    assert errors == ["missing token: $(enemy_1)"]
```

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tools/forge_ptbr/tests/test_tokens.py -v
```

- [ ] **Step 3: Implement deterministic token handling**

```python
# tools/forge_ptbr/src/forge_ptbr/tokens.py
from collections import Counter
from dataclasses import dataclass
import re

TOKEN_RE = re.compile(r"\$\([A-Za-z0-9_]+\)|\{\d+\}|%(?:s|d)|\\n")


@dataclass(frozen=True, slots=True)
class MaskedText:
    text: str
    tokens: tuple[str, ...]


def extract_tokens(text: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in TOKEN_RE.finditer(text))


def mask_tokens(text: str) -> MaskedText:
    tokens: list[str] = []

    def replace(match: re.Match[str]) -> str:
        index = len(tokens)
        tokens.append(match.group(0))
        return f"__FORGE_TOKEN_{index}__"

    return MaskedText(TOKEN_RE.sub(replace, text), tuple(tokens))


def restore_tokens(masked_text: str, tokens: tuple[str, ...]) -> str:
    restored = masked_text
    for index, token in enumerate(tokens):
        restored = restored.replace(f"__FORGE_TOKEN_{index}__", token)
    return restored


def validate_token_equivalence(source: str, candidate: str) -> list[str]:
    source_counts = Counter(extract_tokens(source))
    candidate_counts = Counter(extract_tokens(candidate))
    errors: list[str] = []
    for token, count in source_counts.items():
        for _ in range(max(0, count - candidate_counts[token])):
            errors.append(f"missing token: {token}")
    for token, count in candidate_counts.items():
        for _ in range(max(0, count - source_counts[token])):
            errors.append(f"added token: {token}")
    return errors
```

- [ ] **Step 4: Run token tests**

```bash
python -m pytest tools/forge_ptbr/tests/test_tokens.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit token protection as an independent safety primitive**

```bash
git add tools/forge_ptbr/src/forge_ptbr/tokens.py tools/forge_ptbr/tests/test_tokens.py
git commit -m "feat(ptbr): protect Adventure runtime tokens"
```

---

### Task 6: Build protected structural projections and a hard-fail comparator

**Files:**
- Create: `tools/forge_ptbr/src/forge_ptbr/validator/__init__.py`
- Create: `tools/forge_ptbr/src/forge_ptbr/validator/projection.py`
- Create: `tools/forge_ptbr/src/forge_ptbr/validator/structural.py`
- Create: `tools/forge_ptbr/tests/test_projection.py`

**Interfaces:**
- Produces: `protected_projection(relative_file: Path, document: object) -> dict[str, object]`
- Produces: `StructuralDifference(path: str, before: object, after: object)`
- Produces: `compare_protected(before: dict[str, object], after: dict[str, object]) -> list[StructuralDifference]`
- Later build/doctor plans must call this comparator before applying generated resources.

- [ ] **Step 1: Write failing tests proving that dialogue changes are allowed but quest flags/regex changes are detected**

```python
import copy
import json
from pathlib import Path

from forge_ptbr.validator.projection import protected_projection
from forge_ptbr.validator.structural import compare_protected


FIXTURES = Path(__file__).parent / "fixtures"


def test_projection_ignores_localizable_text_but_keeps_logic() -> None:
    source = json.loads((FIXTURES / "quests_sample.json").read_text(encoding="utf-8"))
    translated = copy.deepcopy(source)
    translated[0]["offerDialog"]["text"] = "Texto em português"

    before = protected_projection(Path("world/quests.json"), source)
    after = protected_projection(Path("world/quests.json"), translated)

    assert compare_protected(before, after) == []


def test_projection_detects_quest_flag_mutation() -> None:
    source = json.loads((FIXTURES / "quests_sample.json").read_text(encoding="utf-8"))
    changed = copy.deepcopy(source)
    changed[0]["offerDialog"]["options"][0]["action"][0]["setQuestFlag"]["key"] = "BROKEN_FLAG"

    differences = compare_protected(
        protected_projection(Path("world/quests.json"), source),
        protected_projection(Path("world/quests.json"), changed),
    )

    assert len(differences) == 1
    assert "setQuestFlag.key" in differences[0].path


def test_projection_detects_shop_regex_mutation() -> None:
    source = json.loads((FIXTURES / "shops_sample.json").read_text(encoding="utf-8"))
    changed = copy.deepcopy(source)
    changed[0]["rewards"][0]["cardText"] = "traduzido"

    assert compare_protected(
        protected_projection(Path("world/shops.json"), source),
        protected_projection(Path("world/shops.json"), changed),
    )
```

- [ ] **Step 2: Run and verify failures**

```bash
python -m pytest tools/forge_ptbr/tests/test_projection.py -v
```

- [ ] **Step 3: Implement projection using the same classifier contract**

```python
# tools/forge_ptbr/src/forge_ptbr/validator/projection.py
from pathlib import Path

from forge_ptbr.model import FieldKind
from forge_ptbr.scanner.json_walk import walk_json_strings
from forge_ptbr.scanner.rules import classify_json_field


def protected_projection(relative_file: Path, document: object) -> dict[str, object]:
    projection: dict[str, object] = {}
    for field in walk_json_strings(document):
        if classify_json_field(relative_file, field) is FieldKind.PROTECTED:
            projection[field.json_path] = field.value
    return projection
```

```python
# tools/forge_ptbr/src/forge_ptbr/validator/structural.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StructuralDifference:
    path: str
    before: object
    after: object


def compare_protected(before: dict[str, object], after: dict[str, object]) -> list[StructuralDifference]:
    differences: list[StructuralDifference] = []
    for path in sorted(set(before) | set(after)):
        if before.get(path) != after.get(path):
            differences.append(StructuralDifference(path, before.get(path), after.get(path)))
    return differences
```

- [ ] **Step 4: Run projection tests plus all safety tests so far**

```bash
python -m pytest tools/forge_ptbr/tests/test_projection.py tools/forge_ptbr/tests/test_rules.py tools/forge_ptbr/tests/test_tokens.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit the structural safety gate**

```bash
git add tools/forge_ptbr/src/forge_ptbr/validator tools/forge_ptbr/tests/test_projection.py
git commit -m "feat(ptbr): validate protected Adventure structure"
```

---

### Task 7: Orchestrate scanning into a stable JSON inventory report

**Files:**
- Create: `tools/forge_ptbr/src/forge_ptbr/scanner/service.py`
- Create: `tools/forge_ptbr/src/forge_ptbr/reporting/__init__.py`
- Create: `tools/forge_ptbr/src/forge_ptbr/reporting/json_report.py`
- Modify: `tools/forge_ptbr/src/forge_ptbr/cli.py`
- Create: `tools/forge_ptbr/tests/test_cli_scan.py`

**Interfaces:**
- Produces: `scan_adventure(repo_root: Path) -> ScanReport`
- Produces: `report_to_dict(report: ScanReport) -> dict[str, object]`
- CLI: `forge-ptbr scan [--repo PATH] [--output PATH] [--strict]`
- `--strict` exits `2` when a non-empty JSON string is classified UNKNOWN; parse/read errors exit `1`; successful scan exits `0`.

- [ ] **Step 1: Write a failing CLI integration test against a miniature repository**

```python
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
```

- [ ] **Step 2: Run and verify failure**

```bash
python -m pytest tools/forge_ptbr/tests/test_cli_scan.py -v
```

- [ ] **Step 3: Implement scanner orchestration**

`scan_adventure()` must:

1. call `adventure_root()` and `discover_resources()`;
2. parse `.json` files with `json.loads(..., encoding UTF-8)`;
3. add `.txt`, `.tmx`, `.xml` paths to `unsupported_files` for this first plan instead of guessing their semantics;
4. walk each JSON string;
5. skip empty strings from the translation inventory but keep protected non-empty strings;
6. derive `SourceLocation`, `FieldKind`, `source_hash`, stable ID, and extracted tokens;
7. sort entries by `(plane.casefold(), relative_file.as_posix(), json_path)` before returning.

Core creation code:

```python
location = SourceLocation(
    plane=resource.plane,
    relative_file=resource.relative_file,
    json_path=field.json_path,
    resource_type=resource.relative_file.stem,
)
entry = InventoryEntry(
    source_id=stable_source_id(location, field.value),
    location=location,
    field_name=field.key,
    source_text=field.value,
    source_hash=source_text_hash(field.value),
    kind=classify_json_field(resource.relative_file, field),
    tokens=extract_tokens(field.value),
)
```

- [ ] **Step 4: Implement deterministic JSON reporting and the thin CLI adapter**

Report schema:

```json
{
  "schema_version": 1,
  "summary": {
    "scanned_files": 3,
    "entries": 42,
    "localizable_existing_hook": 10,
    "localizable_needs_hook": 8,
    "protected": 20,
    "unknown": 4,
    "unsupported_files": 2
  },
  "unsupported_files": ["Shandalar/world/town_names_black.txt"],
  "entries": []
}
```

`cli.py` must expose `main(argv: list[str] | None = None) -> int` and use `argparse`. Default `--repo` is repository discovery from `Path.cwd()`. Default output is `tools/forge_ptbr/build/inventory.json`; create parent directories before writing. `json_report.py` writes UTF-8, `ensure_ascii=False`, `indent=2`, trailing newline.

Run:

```bash
python -m pytest tools/forge_ptbr/tests/test_cli_scan.py -v
forge-ptbr scan --repo . --output tools/forge_ptbr/build/inventory.json
```

Expected on the real repository: command completes, produces a deterministic report, and does not modify any `forge-gui/res/adventure/**` file.

- [ ] **Step 5: Commit the usable scanner CLI**

```bash
git add tools/forge_ptbr/src/forge_ptbr tools/forge_ptbr/tests/test_cli_scan.py
git commit -m "feat(ptbr): add Adventure inventory scanner CLI"
```

Do not commit `tools/forge_ptbr/build/inventory.json`; generated reports remain local build output.

---

### Task 8: Add ignore rules, cross-platform CI, and real-repository smoke verification

**Files:**
- Modify: `.gitignore`
- Create: `.github/workflows/ptbr-tools.yml`
- No production code unless a platform-specific test exposes a defect.

**Interfaces:**
- CI becomes the cross-platform contract for the Python scanner.
- Required command: `python -m pytest tools/forge_ptbr/tests -q`
- Required smoke command: `forge-ptbr scan --repo . --output tools/forge_ptbr/build/inventory.json`

- [ ] **Step 1: Add a failing cleanliness assertion locally before ignore rules**

Run:

```bash
mkdir -p tools/forge_ptbr/build
printf '{}\n' > tools/forge_ptbr/build/inventory.json
git status --short tools/forge_ptbr/build
```

Expected before `.gitignore` change: generated inventory appears as an untracked file.

- [ ] **Step 2: Add scanner build/cache ignores**

Append to `.gitignore`:

```gitignore
# Forge PT-BR tooling generated output
tools/forge_ptbr/build/
tools/forge_ptbr/.pytest_cache/
tools/forge_ptbr/*.egg-info/
tools/forge_ptbr/src/*.egg-info/
```

Then run:

```bash
git status --short tools/forge_ptbr/build
```

Expected: no generated inventory is reported.

- [ ] **Step 3: Add the CI matrix**

```yaml
# .github/workflows/ptbr-tools.yml
name: PT-BR Tools

on:
  push:
    branches: [ptbr-adventure]
    paths:
      - "tools/forge_ptbr/**"
      - ".github/workflows/ptbr-tools.yml"
  pull_request:
    paths:
      - "tools/forge_ptbr/**"
      - ".github/workflows/ptbr-tools.yml"

jobs:
  scanner:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install PT-BR tooling
        run: python -m pip install -e "tools/forge_ptbr[dev]"
      - name: Run tests
        run: python -m pytest tools/forge_ptbr/tests -q
      - name: Smoke scan repository
        run: forge-ptbr scan --repo . --output tools/forge_ptbr/build/inventory.json
```

- [ ] **Step 4: Run the complete local verification gate**

```bash
python -m pip install -e "tools/forge_ptbr[dev]"
python -m pytest tools/forge_ptbr/tests -q
forge-ptbr scan --repo . --output tools/forge_ptbr/build/inventory.json
python -m json.tool tools/forge_ptbr/build/inventory.json > /dev/null
```

On Windows PowerShell, replace the last line with:

```powershell
python -m json.tool tools/forge_ptbr/build/inventory.json | Out-Null
```

Expected: tests pass; real Forge scan succeeds; JSON report parses; `git status --short forge-gui/res/adventure` is empty.

- [ ] **Step 5: Commit CI and cleanliness rules**

```bash
git add .gitignore .github/workflows/ptbr-tools.yml
git commit -m "ci(ptbr): test scanner across desktop platforms"
```

---

## End-of-Plan Review Gate

Before declaring this plan complete, run exactly:

```bash
python -m pytest tools/forge_ptbr/tests -q
forge-ptbr scan --repo . --output tools/forge_ptbr/build/inventory.json
git diff --exit-code -- forge-gui/res/adventure
git status --short
```

Acceptance for this plan:

- Python package installs on Python 3.11+.
- All tests pass.
- `quests.json` dialogue text is classified as using an existing localization hook while quest metadata is classified as needing a hook.
- `shops.json.cardText`, functional shop `name`, card lookup names, flags and script/resource identifiers are PROTECTED.
- `items.json` display metadata is inventoried without being rewritten; `dialogOnUse` is recognized as existing-hook dialogue.
- unknown non-empty strings remain UNKNOWN and `--strict` returns exit code `2`.
- runtime tokens including `$(enemy_1)`, `$(poi_2)`, `$(playername)`, `{0}`, `%s`, `%d` and `\\n` can be validated without loss.
- structural comparison catches deliberately changed protected values.
- the real-repository smoke scan does not modify Forge Adventure source files.
- CI runs the scanner test suite on Ubuntu, Windows and macOS.

## Self-Review Against the Approved Specification

**Covered by this plan:** repository/tool skeleton; safe scanner; resource inventory; typed classification; UNKNOWN policy; token protection; protected structural validator; first CLI command; cross-platform CI; foundation for incremental source hashes and stable identities.

**Intentionally deferred to the next dedicated plans:** deterministic localization keys beyond stable source identity; translation memory persistence; Magic glossary; Argos Translate; translation quality scoring; lifecycle/review persistence; Java localization extensions; generated `pt-BR.properties`; Shandalar runtime slice; `doctor`; GUI; upstream delta merge behavior; all-plane translation.

There are no implementation placeholders in this plan: every task has explicit files, interfaces, test commands, expected behavior and commit boundaries.
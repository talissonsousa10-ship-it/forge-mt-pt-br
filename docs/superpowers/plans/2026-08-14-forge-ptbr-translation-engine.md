# Forge PT-BR Translation Engine & Review Data Implementation Plan

> Execution mode: subagent-driven/TDD protocol, implemented task-by-task on an isolated feature branch and reviewed before integration.

**Goal:** Add the data and translation layer on top of the safe scanner: deterministic localization keys, persistent review lifecycle, contextual translation memory, versioned Magic glossary, local-provider abstraction with Argos Translate as an optional zero-paid-API provider, deterministic quality checks, and CLI commands to initialize/update/auto-translate catalogs without modifying Forge Adventure source resources.

**Base branch:** `ptbr-adventure`  
**Feature branch:** `ptbr/translation-engine`

## Constraints

- Core operation must have no mandatory paid service.
- Normal translation can work offline after the user installs a local model.
- Cloud/AI providers remain optional and are not required by tests or builds.
- Functional Forge data remains read-only in this phase.
- Only inventory entries classified `LOCALIZABLE_EXISTING_HOOK` or `LOCALIZABLE_NEEDS_HOOK` enter translation catalogs.
- `UNKNOWN` and `PROTECTED` entries are never sent to a translator.
- Runtime tokens must be masked before provider calls and restored/validated afterward.
- Machine output never becomes `APPROVED` automatically.
- Approved exact contextual memory takes precedence over machine translation.
- Translation keys must be deterministic and independent from Portuguese text.
- CI must remain green on Windows, Ubuntu, and macOS.

## Planned Structure

```text
tools/forge_ptbr/src/forge_ptbr/
├── catalog/
│   ├── model.py
│   ├── keys.py
│   ├── store.py
│   └── sync.py
├── glossary/
│   ├── model.py
│   ├── store.py
│   └── apply.py
├── memory/
│   ├── model.py
│   ├── store.py
│   └── lookup.py
├── quality/
│   └── checks.py
├── translator/
│   ├── base.py
│   ├── service.py
│   └── providers/
│       ├── __init__.py
│       └── argos.py
└── cli.py

translations/
├── glossary/
│   └── mtg-pt-BR.json
├── memory.json
└── catalogs/
    └── <plane>.json
```

Generated scanner inventory remains under `tools/forge_ptbr/build/` and is not committed.

---

## Task 1 — Translation lifecycle model and deterministic localization keys

**Create:**
- `tools/forge_ptbr/src/forge_ptbr/catalog/__init__.py`
- `tools/forge_ptbr/src/forge_ptbr/catalog/model.py`
- `tools/forge_ptbr/src/forge_ptbr/catalog/keys.py`
- `tools/forge_ptbr/tests/test_catalog_model.py`
- `tools/forge_ptbr/tests/test_keys.py`

### Required contract

```python
class TranslationStatus(str, Enum):
    NEW = "new"
    AUTO = "auto"
    REVIEW = "review"
    APPROVED = "approved"
    CHANGED = "changed"
    OBSOLETE = "obsolete"
```

`CatalogEntry` stores at least:

```text
source_id
localization_key
plane
resource_type
relative_file
json_path
field_name
source_text
source_hash
tokens
translation
status
quality_score
quality_flags
translator
reviewed
```

`localization_key(entry)` must be stable for the same `source_id` and context and must not contain Portuguese text.

Recommended format:

```text
adv.<plane-slug>.<resource-type-slug>.<field-slug>.<source-id-suffix>
```

Example:

```text
adv.shandalar.quests.description.81f2a60a42d7
```

Rules:
- lowercase ASCII slug;
- spaces and punctuation collapse to `_`;
- use a source-id suffix to guarantee uniqueness;
- no array/source text is embedded in the key.

### TDD cases

- same source identity => same key;
- changing Portuguese candidate => same key;
- plane with spaces => normalized key;
- two different source IDs => different keys;
- status serializes to stable lowercase values.

**Commit:** `feat(ptbr): add translation catalog model and keys`

---

## Task 2 — Persistent per-plane catalogs and inventory synchronization

**Create:**
- `tools/forge_ptbr/src/forge_ptbr/catalog/store.py`
- `tools/forge_ptbr/src/forge_ptbr/catalog/sync.py`
- `tools/forge_ptbr/tests/test_catalog_store.py`
- `tools/forge_ptbr/tests/test_catalog_sync.py`

### Storage format

One UTF-8 JSON catalog per plane:

```text
translations/catalogs/common.json
translations/catalogs/shandalar.json
translations/catalogs/innistrad.json
...
```

Top-level schema:

```json
{
  "schema_version": 1,
  "plane": "Shandalar",
  "entries": []
}
```

Writes must be deterministic: `ensure_ascii=false`, indentation, sorted entries, trailing newline.

### Sync rules

Given a `ScanReport` and existing catalogs:

- new localizable source => `NEW`;
- same `source_id` + same `source_hash` => preserve translation/review/status;
- same `source_id` + changed `source_hash` => `CHANGED`, keep prior Portuguese candidate for reviewer reference but clear `reviewed`;
- missing source previously present => `OBSOLETE`;
- source becomes `PROTECTED` or `UNKNOWN` => remove it from active translation queue and mark existing record `OBSOLETE` with a safety flag;
- machine data must never overwrite an `APPROVED` translation unless English source hash changed.

### TDD cases

- first sync creates NEW entries only from localizable kinds;
- PROTECTED/UNKNOWN excluded;
- second identical sync is byte-stable;
- approved translation survives unchanged scan;
- changed English marks CHANGED;
- removed source marks OBSOLETE.

**Commit:** `feat(ptbr): sync translation catalogs from scanner inventory`

---

## Task 3 — Contextual translation memory

**Create:**
- `tools/forge_ptbr/src/forge_ptbr/memory/__init__.py`
- `tools/forge_ptbr/src/forge_ptbr/memory/model.py`
- `tools/forge_ptbr/src/forge_ptbr/memory/store.py`
- `tools/forge_ptbr/src/forge_ptbr/memory/lookup.py`
- `tools/forge_ptbr/tests/test_translation_memory.py`

### Memory record

Minimum fields:

```text
source_text
translation
plane
resource_type
context
source_file
source_path
source_hash
translator
reviewed
```

Persistence: `translations/memory.json`, schema versioned and deterministic.

### Lookup precedence

1. exact reviewed match on source text + compatible resource context;
2. exact reviewed generic match when context is not contradictory;
3. no result.

No fuzzy matching in this phase. Fuzzy matching can be added later without changing persistence schema.

### Safety rule

Only `APPROVED` human-reviewed catalog entries are promoted into translation memory by default.

### TDD cases

- reviewed contextual match wins;
- unreviewed memory is ignored;
- same English term can have different translations in different contexts;
- duplicate approved records deduplicate deterministically.

**Commit:** `feat(ptbr): add contextual translation memory`

---

## Task 4 — Versioned Magic: The Gathering PT-BR glossary

**Create:**
- `translations/glossary/mtg-pt-BR.json`
- `tools/forge_ptbr/src/forge_ptbr/glossary/__init__.py`
- `tools/forge_ptbr/src/forge_ptbr/glossary/model.py`
- `tools/forge_ptbr/src/forge_ptbr/glossary/store.py`
- `tools/forge_ptbr/src/forge_ptbr/glossary/apply.py`
- `tools/forge_ptbr/tests/test_glossary.py`

### Initial glossary dataset

Seed only terms already approved in the project design, avoiding speculative bulk terminology:

```text
Flying -> Voar
Trample -> Atropelar
Haste -> Ímpeto
Deathtouch -> Toque mortífero
Lifelink -> Vínculo com a vida
Creature -> criatura
Artifact -> artefato
Graveyard -> cemitério
Battlefield -> campo de batalha
Library -> grimório
Token -> ficha
Counter -> marcador
Mana -> mana
Planeswalker -> Planeswalker
```

Each glossary item should support:

```text
source
target
case_sensitive
whole_word
contexts (optional)
notes (optional)
```

### Application model

Do **not** blindly replace source English before translation in a way that sends mixed-language text to the provider.

Use two operations:

1. detect glossary terms and record expected canonical PT-BR terms;
2. validate/post-correct the translated candidate when the term use is unambiguous.

Ambiguous entries may be validation-only and flagged for review.

### TDD cases

- whole-word matching does not replace substrings;
- case-insensitive detection works where configured;
- canonical term validation returns warnings;
- deterministic post-correction for unambiguous terms;
- no mutation of protected tokens.

**Commit:** `feat(ptbr): add versioned Magic glossary`

---

## Task 5 — Deterministic translation quality checks

**Create:**
- `tools/forge_ptbr/src/forge_ptbr/quality/__init__.py`
- `tools/forge_ptbr/src/forge_ptbr/quality/checks.py`
- `tools/forge_ptbr/tests/test_quality.py`

### Result contract

```python
@dataclass(frozen=True)
class QualityResult:
    score: int
    flags: tuple[str, ...]
```

Score range: 0–100.

Required checks:

- token equivalence;
- blank candidate;
- suspiciously unchanged English;
- glossary compliance;
- extreme source/candidate length ratio;
- obvious placeholder artifacts such as `__FORGE_TOKEN_` remaining;
- malformed repeated whitespace/newline patterns.

Scoring is deterministic and transparent; it is not an ML confidence score.

Suggested severity:

- token loss/addition => score cap 0 and hard error flag;
- leaked mask placeholder => cap 0;
- blank => 0;
- glossary violation => penalty;
- unchanged long English => penalty/review;
- clean output => 100.

No score automatically changes status to APPROVED.

**Commit:** `feat(ptbr): add deterministic translation quality checks`

---

## Task 6 — Translator provider contract and local Argos adapter

**Modify:**
- `tools/forge_ptbr/pyproject.toml`

**Create:**
- `tools/forge_ptbr/src/forge_ptbr/translator/__init__.py`
- `tools/forge_ptbr/src/forge_ptbr/translator/base.py`
- `tools/forge_ptbr/src/forge_ptbr/translator/providers/__init__.py`
- `tools/forge_ptbr/src/forge_ptbr/translator/providers/argos.py`
- `tools/forge_ptbr/tests/test_translator_provider.py`
- `tools/forge_ptbr/tests/test_argos_provider.py`

### Provider interface

```python
class TranslationProvider(Protocol):
    name: str
    def is_ready(self) -> bool: ...
    def translate(self, text: str, source_lang: str, target_lang: str) -> str: ...
```

### Packaging

Argos is optional:

```toml
[project.optional-dependencies]
local-translate = ["argostranslate>=1.9"]
```

Core package/tests must import cleanly without Argos installed.

### Argos adapter requirements

- lazy import `argostranslate` only when provider is instantiated/used;
- clear actionable error when optional dependency is absent;
- `is_ready()` checks installed language/package availability without silently downloading anything;
- normal `translate()` never triggers model download;
- installation/model setup remains an explicit later CLI/setup action;
- tests monkeypatch a fake Argos module and require no network/model.

**Commit:** `feat(ptbr): add optional local Argos translation provider`

---

## Task 7 — Translation service: memory -> mask -> provider -> restore -> glossary -> quality

**Create:**
- `tools/forge_ptbr/src/forge_ptbr/translator/service.py`
- `tools/forge_ptbr/tests/test_translation_service.py`

### Pipeline

For every eligible `NEW`, `CHANGED`, or explicitly selected `REVIEW` entry:

```text
catalog entry
  -> approved exact translation-memory lookup
  -> if hit: candidate from memory, status REVIEW (unless explicit policy later changes)
  -> else mask tokens
  -> provider.translate(masked text)
  -> restore tokens
  -> canonical glossary post-check/correction
  -> quality checks
  -> persist candidate
  -> status AUTO for provider output
  -> status REVIEW if hard/important quality flags occur
```

Important:
- memory reuse must record `translator = "memory"`;
- provider output records provider name;
- token validation occurs after restoration;
- provider is never called for PROTECTED/UNKNOWN entries;
- provider is never called for APPROVED unchanged entries;
- provider failure leaves existing catalog data intact.

### TDD cases

- memory hit avoids provider call;
- provider receives masked tokens;
- output restores tokens exactly;
- hard quality failure becomes REVIEW;
- clean provider output becomes AUTO, never APPROVED;
- APPROVED unchanged entry is skipped;
- CHANGED English can be retranslated while keeping lifecycle semantics.

**Commit:** `feat(ptbr): orchestrate safe automatic translation pipeline`

---

## Task 8 — CLI commands for catalog sync and automatic translation

**Modify:**
- `tools/forge_ptbr/src/forge_ptbr/cli.py`

**Create:**
- `tools/forge_ptbr/tests/test_cli_catalog.py`
- `tools/forge_ptbr/tests/test_cli_translate.py`

### Commands

```bash
forge-ptbr catalog-sync --repo .
forge-ptbr translate --repo . --provider argos
```

`catalog-sync`:
- scans current repository using existing `scan_adventure()`;
- writes/updates `translations/catalogs/*.json`;
- prints compact counts NEW/CHANGED/OBSOLETE/APPROVED;
- returns `0` on success;
- does not require a translation provider.

`translate`:
- loads catalogs/memory/glossary;
- validates provider readiness before mutating catalogs;
- processes eligible entries;
- writes catalogs atomically only after successful per-entry processing decisions;
- returns `3` when selected provider is unavailable/not ready;
- never modifies `forge-gui/res/adventure/**`.

Tests use a fake provider injected through provider factory logic; CI must not download Argos models.

**Commit:** `feat(ptbr): add catalog sync and translation CLI`

---

## Task 9 — Seed real catalogs safely and extend cross-platform CI

**Modify:**
- `.github/workflows/ptbr-tools.yml`

**Create generated-but-versioned source data:**
- `translations/catalogs/common.json`
- one catalog for each Adventure plane discovered by scanner, containing source metadata and lifecycle state but **no mass machine translations**.

### Verification

Run:

```bash
python -m pytest tools/forge_ptbr/tests -q
forge-ptbr scan --repo . --output tools/forge_ptbr/build/inventory.json
forge-ptbr catalog-sync --repo .
git diff --exit-code -- forge-gui/res/adventure
```

CI matrix remains:

```text
ubuntu-latest
windows-latest
macos-latest
```

Add a catalog synchronization smoke test that writes into a temporary output root or verifies committed catalogs are parseable. Do not let CI rewrite committed catalogs and then silently ignore drift.

Acceptance:

- all tests pass;
- scanner still passes full repo;
- catalog sync completes on full repo;
- zero Adventure resource modifications;
- committed catalog JSON parses on every platform;
- no Argos/network requirement in CI.

**Commit:** `ci(ptbr): verify translation data pipeline across platforms`

---

# End-of-Phase Acceptance Gate

The phase is complete only when all of the following are demonstrated:

1. Translation catalogs contain only scanner-classified localizable entries.
2. Deterministic localization keys are stable across repeated syncs.
3. `source_hash` changes transition existing entries to CHANGED.
4. Removed sources become OBSOLETE rather than disappearing silently.
5. APPROVED unchanged translations survive scanner updates.
6. Contextual memory reuses only reviewed translations and can distinguish ambiguous terms by context.
7. Magic glossary is versioned and deterministic.
8. Runtime tokens are masked before provider calls and restored exactly.
9. Quality checks detect token loss, leaked masks, blank output, glossary violations, and suspicious untranslated text.
10. Argos is optional, lazy-loaded, and does not download models during normal translation.
11. Machine translation produces AUTO or REVIEW, never APPROVED.
12. CLI catalog sync works without Argos.
13. CLI translate reports unavailable local provider cleanly.
14. Full tests and smoke sync pass in Windows, Ubuntu, and macOS.
15. `forge-gui/res/adventure/**` remains unchanged by this phase.

# Deferred to Phase 3

- Java `locname` / `locdescription` extensions.
- Generator for final Forge `pt-BR.properties`.
- Injection of localization references into Forge resources.
- End-to-end Shandalar runtime slice.
- Actual bulk translation/review campaign.
- GUI reviewer.
- `doctor` full application health command.

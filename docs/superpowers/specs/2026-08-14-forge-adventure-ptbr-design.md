# Forge Adventure PT-BR — Design Specification

**Date:** 2026-08-14  
**Repository:** `talissonsousa10-ship-it/forge-mt-pt-br`  
**Integration branch:** `ptbr-adventure`  
**Upstream mirror branch:** `master`

## 1. Objective

Create a maintainable, zero-mandatory-cost, cross-platform Brazilian Portuguese localization system for Forge Adventure.

The project must localize the complete Adventure experience, including:

- NPC and player dialogue;
- quest titles, descriptions, objectives, rewards and status text;
- shop-facing labels and descriptions;
- items and equipment;
- tutorials;
- events;
- locations and other player-visible world text;
- existing Adventure UI strings in `pt-BR.properties`;
- other narrative or presentation text discovered by the scanner and classified as safely localizable.

The target writing style is natural Brazilian Portuguese, comparable to a professionally localized RPG, while preserving canonical Magic: The Gathering terminology whenever an official Brazilian Portuguese term exists.

## 2. Core principles

1. **Do not corrupt game logic.** Translation must never alter identifiers, quest flags, regexes, filenames, script commands, card selectors, tags, resource paths, objective enums, card names used as functional identifiers, or other logic-bearing values.
2. **English remains the source fallback.** The original Forge English text must remain available wherever possible.
3. **Localization is data-driven.** New localization keys are preferred over destructive replacement of source strings.
4. **Translation source is separate from generated Forge artifacts.** Human-reviewed translation data is the source of truth; patched Forge resources are reproducible build output.
5. **Upstream maintenance is first-class.** New and changed Forge text must be detected incrementally rather than forcing full retranslation.
6. **Mandatory cost is R$ 0.** The core workflow works locally/offline after initial model setup. Paid/cloud AI providers are optional review plugins only.
7. **Cross-platform from the start.** Windows, Linux and macOS are supported design targets.
8. **CLI and GUI share one engine.** The GUI is a thin frontend over the same application services exposed by the CLI.

## 3. Git strategy

### `master`

`master` is kept as a clean mirror of the official `Card-Forge/forge` upstream as far as practical.

No project-specific PT-BR implementation work should be developed directly on `master`.

### `ptbr-adventure`

Long-lived integration branch containing:

- localization tooling;
- glossary and translation memory;
- reviewed translation source data;
- minimal Forge localization extensions required for resource types that do not currently expose localization hooks;
- generated localization-key references required by the localized Adventure build.

Feature work may use short-lived branches later, for example:

- `ptbr/scanner`;
- `ptbr/i18n-items`;
- `ptbr/i18n-quests`;
- `ptbr/shandalar`.

They merge into `ptbr-adventure`, not directly into `master`.

## 4. High-level architecture

The translation system is implemented in Python and remains decoupled from Forge's Java runtime except for deliberately small localization extensions.

```text
Forge source resources
        |
        v
Resource discovery
        |
        v
Typed parsers / field classifier
        |
        +----> functional / unknown fields ----> protected, never translated
        |
        v
Localizable text inventory
        |
        v
Token protection + canonicalization
        |
        v
Translation memory
        |
        v
Magic glossary
        |
        v
Local translation provider
        |
        v
Post-processing + quality scoring
        |
        +----> review queue / optional AI review
        |
        v
Approved translation source
        |
        v
Generator
        |
        +----> `pt-BR.properties`
        +----> resource localization keys (`loctext`, `locname`, etc.)
        +----> reports
        |
        v
Structural validator / doctor
        |
        v
Forge Adventure PT-BR build
```

## 5. Proposed repository layout

```text
forge-mt-pt-br/
├── forge-gui/
│   └── res/
│       └── languages/
│           └── pt-BR.properties
├── tools/
│   └── forge_ptbr/
│       ├── cli/
│       ├── gui/
│       ├── scanner/
│       ├── parsers/
│       ├── extractor/
│       ├── translator/
│       │   └── providers/
│       ├── glossary/
│       ├── memory/
│       ├── reviewer/
│       ├── quality/
│       ├── generator/
│       ├── validator/
│       └── updater/
├── translations/
│   ├── common/
│   ├── Amonkhet/
│   ├── Crystal_Kingdoms/
│   ├── Innistrad/
│   ├── Realm_of_Legends/
│   ├── Shandalar/
│   └── Shandalar_Old_Border/
└── docs/
    └── superpowers/
        └── specs/
```

Exact Python packaging details are deferred to the implementation plan.

## 6. Hybrid localization-file architecture

Forge currently uses the normal language bundle, including `forge-gui/res/languages/pt-BR.properties`.

The project will not require translators to manually maintain one monolithic file containing the entire Adventure localization.

Instead, reviewed translation source is organized by plane/domain under `translations/`. A generator compiles approved entries into the Forge-compatible localization artifact.

Illustrative key scheme:

```properties
adv.common.item.challenge_coin.name=Moeda de Desafio
adv.shandalar.quest.go_forth_and_slay.name=Vá em Frente e Derrote-os
adv.shandalar.quest.go_forth_and_slay.offer.001=Ei, você! Sim, você...
adv.innistrad.dialog.town_guard.004=Não fique nas ruas depois do anoitecer.
```

Key requirements:

- stable across rebuilds;
- deterministic from source identity/context rather than translation text;
- unique;
- readable enough for debugging;
- independent of transient array ordering whenever a more stable identifier exists.

## 7. Localization extensions inside Forge

Dialogue already supports localization-key fields such as `loctext` and `locname`. These existing hooks should be used rather than replacing English dialogue text.

Some Adventure data types currently expose only direct user-visible strings. For those types, the project may add minimal localization fields and getters, for example:

```text
name            + locname
description     + locdescription
rewardDescription + locrewarddescription
```

Candidate types include items, quest metadata and quest-stage metadata.

Rules for Java-side changes:

- minimal surface area;
- English fallback preserved;
- no change to logical identifiers;
- no broad rewrite of Forge's `Localizer` unless proven necessary;
- prefer `Localizer.getMessageorUseDefault(...)`-style fallback behavior where appropriate;
- changes must be isolated and easy to rebase when upstream changes.

## 8. Safe scanner and typed parsing

The scanner must understand resource semantics. It must never translate all JSON strings indiscriminately.

### Examples of localizable fields

Depending on resource type and confirmed runtime usage:

- dialogue `text`;
- dialogue option `name`;
- quest `name`;
- quest `description`;
- quest `rewardDescription`;
- quest stage `name`;
- quest stage `description`;
- item display `name`;
- item `description`;
- shop display `description`;
- player-facing location/event/tutorial text.

### Examples of protected functional fields

- `id`;
- `objective`;
- `issueQuest`;
- `setQuestFlag` / `checkQuestFlag` / map flags;
- `questSourceTags`, `questEnemyTags`, `questPOITags`;
- `enemyTags`, `POITags`;
- `cardText` regex/card-selection expressions;
- `sprite`, `spriteAtlas`, `iconName`;
- file/resource paths;
- `editions`;
- command/script strings;
- enum-like values;
- card names when they are used as functional lookup identifiers;
- object references and keys.

### Unknown-field policy

If an upstream update introduces a field that the parser cannot classify safely, the field is **not translated**.

It is reported as `UNKNOWN` and requires explicit classification before translation can touch it.

Safety beats coverage.

## 9. Token and placeholder protection

Before translation, protected substrings are replaced by deterministic placeholders and restored afterward.

Protected examples include:

- `$(enemy_1)`;
- `$(poi_2)`;
- `$(playername)`;
- `{0}`, `{1}`;
- `%s`, `%d`;
- escaped newlines such as `\n`;
- markup/tags where translation of the tag itself would be unsafe;
- script fragments;
- explicit resource references.

A translation fails validation if the original and translated versions do not contain equivalent protected tokens.

## 10. Translation engine

### Core mode

Automatic translation followed by review.

### Mandatory-cost policy

Core translation must be usable with no paid API.

### Local provider

The initial preferred local provider is **Argos Translate**, isolated behind a provider interface so it can be replaced without changing scanner, memory, review or generator code.

The setup workflow should verify that a usable English-to-Portuguese local package is available before declaring the provider ready.

The translator must not depend on network access during normal batch translation after required local model assets are installed.

### Optional providers

Cloud/AI providers may be added for selected review tasks only, for example:

```text
translator/providers/
├── argos.py
├── openai.py
├── gemini.py
└── local_ai.py
```

No optional provider is required to build or use the PT-BR project.

## 11. Magic glossary

A canonical glossary is applied before/after machine translation as appropriate.

Rules:

- official Brazilian Portuguese Magic terminology has priority;
- proper nouns use an official localized form when one exists and is appropriate for the context;
- otherwise proper names are preserved;
- functional card lookup names remain untouched where changing them would alter behavior;
- ambiguous terms are context-sensitive.

Illustrative terms:

```text
Flying       -> Voar
Trample      -> Atropelar
Haste        -> Ímpeto
Deathtouch   -> Toque mortífero
Lifelink     -> Vínculo com a vida
Creature     -> criatura
Artifact     -> artefato
Graveyard    -> cemitério
Battlefield  -> campo de batalha
Library      -> grimório
Token        -> ficha
Counter      -> marcador
```

The glossary itself is versioned and reviewable.

## 12. Translation memory

The system maintains contextual translation memory rather than a flat string dictionary.

Minimum metadata for an entry:

```text
source_text
translation
plane
type
context
source_file
source_path
status
hash_original
translator
reviewed
```

This permits different translations for ambiguous strings such as `Draw` depending on whether the context is card rules, a match result or ordinary narrative.

Exact-match reviewed memory should take precedence over new automatic translation.

## 13. Translation lifecycle

Each inventory entry has a state:

```text
NEW       extracted but untranslated
AUTO      automatically translated
REVIEW    requires human review
APPROVED  accepted translation
CHANGED   upstream English source changed after approval
OBSOLETE  source no longer exists upstream
```

Potential additional machine-readable quality flags may coexist with the lifecycle state.

## 14. Quality scoring

Automatic translations receive a quality/confidence assessment based on deterministic signals such as:

- token preservation;
- glossary compliance;
- suspicious untranslated English;
- malformed markup;
- extreme length ratio;
- repeated punctuation/encoding problems;
- known translation-memory match;
- context ambiguity;
- source changes.

The numerical score is an aid, not proof of linguistic correctness.

High-confidence entries may be eligible for batch approval by explicit user action. They are not silently promoted to reviewed status solely because of the score.

## 15. Review experience

The GUI should support a focused reviewer workflow showing:

- plane/domain;
- resource type;
- original text;
- PT-BR candidate;
- source path/context;
- quality score and warnings;
- glossary/token status;
- actions to approve, edit or mark for deeper review;
- optional AI-review action when a provider is configured.

Filters should include:

- new;
- automatic;
- needs review;
- changed upstream;
- glossary warnings;
- token errors;
- plane;
- resource category.

Bulk operations are allowed only for safe, explicit user-selected cohorts.

## 16. CLI

Initial conceptual commands:

```bash
forge-ptbr setup
forge-ptbr scan
forge-ptbr translate
forge-ptbr review
forge-ptbr validate
forge-ptbr build
forge-ptbr update
forge-ptbr doctor
```

The implementation plan may refine command names and options.

The CLI and GUI must call the same application services rather than duplicating business logic.

## 17. GUI

The first GUI is intentionally small. Primary workflow:

```text
Scan -> Translate -> Review -> Validate -> Build/Apply
```

Additional panels may expose:

- translation progress;
- per-plane coverage;
- warnings/errors;
- upstream-change inventory;
- glossary editor;
- provider configuration;
- doctor report.

A visually elaborate UI is not an MVP requirement.

## 18. Upstream synchronization

Update flow:

```text
Card-Forge/forge upstream
        |
        v
fork master
        |
        v
compare previous source inventory with new source inventory
        |
        +--> unchanged -> retain approved translation
        +--> added     -> NEW
        +--> modified  -> CHANGED
        +--> removed   -> OBSOLETE
        |
        v
ptbr-adventure review/build
```

The scanner should hash normalized source text plus stable context so it can identify changes without retranslating the entire corpus.

Generated localization keys should remain stable whenever the logical source entity remains the same.

## 19. Generated artifacts and source of truth

`translations/` plus glossary/memory/review metadata are the source of truth.

Forge-specific generated artifacts must be rebuildable.

Conceptually:

```bash
forge-ptbr clean
forge-ptbr build
```

should recreate generated localization artifacts from reviewed project data without losing human work.

Generated files should clearly identify that they are generated when practical.

## 20. Validation

A build cannot be considered valid unless the structural validator passes.

Required checks include:

- valid JSON/XML/TMX/properties syntax for touched/generated resources;
- no duplicate localization keys;
- every emitted localization reference resolves appropriately;
- protected tokens preserved;
- quest/map flags unchanged;
- IDs unchanged;
- objective values unchanged;
- regex/card selectors unchanged;
- functional card lookup values unchanged;
- resource paths unchanged;
- script/command strings unchanged;
- no unexpected changes to protected fields;
- localization fallback remains usable;
- newly unknown fields are reported.

Where feasible, the validator compares normalized protected-data projections of source vs generated resource rather than relying only on hand-maintained field lists.

## 21. `doctor` command

`forge-ptbr doctor` is the human-facing health check.

Example output:

```text
Forge PT-BR Doctor

OK  repository detected
OK  expected branch/config detected
OK  translation database readable
OK  no quest flags changed
OK  no protected tokens lost
OK  generated JSON valid
OK  localization keys unique
WARN 38 translations await review

Adventure PT-BR build: READY
```

A failing structural-safety check must produce a non-zero CLI exit status.

## 22. Testing strategy

### Unit tests

- token protector;
- glossary transformation;
- translation-memory lookup;
- field classifiers;
- typed parsers;
- key generation;
- hash/change detection;
- quality checks.

### Structural tests

- quests;
- dialogues;
- items;
- shops;
- maps/resources that contain player-visible text.

### Integration tests

- scan known Adventure fixture;
- translate with deterministic mock provider;
- generate localization files;
- insert localization keys;
- validate output;
- verify English fallback behavior.

### Regression tests

Compare protected projections before/after generation to prove that translation did not alter game logic.

### Runtime smoke tests

Start with a small Shandalar end-to-end slice covering:

- one dialogue tree;
- one quest;
- one quest stage;
- one item;
- one shop-facing string;
- existing Adventure UI translation.

After runtime behavior is verified, expand to complete Shandalar and then every bundled plane.

## 23. MVP sequence

The first implementation should **not** begin by mass-translating all Adventure content.

Recommended sequence:

1. repository/tool skeleton and tests;
2. scanner and resource inventory;
3. typed classification + protected-field validator;
4. translation-source schema and deterministic key generator;
5. translation memory + Magic glossary;
6. local translation-provider adapter;
7. existing `pt-BR.properties` Adventure-gap inventory;
8. localization extension for one unsupported data type;
9. Shandalar vertical slice;
10. runtime smoke test;
11. CLI review/build/doctor loop;
12. minimal GUI;
13. expand resource coverage;
14. translate complete Shandalar;
15. expand to all bundled planes;
16. upstream-delta updater.

This sequence validates safety before scale.

## 24. Non-goals for the first version

The initial Adventure-localization MVP does not require:

- translating printed text baked into downloaded card scan images;
- replacing Forge's entire localization framework;
- dubbing/voice generation;
- distributing copyrighted music;
- translating functional card identifiers;
- automatic acceptance of every machine translation;
- building a general-purpose translation platform unrelated to Forge.

Card rules-text translation and custom music/voice tooling can be separate project phases after the Adventure pipeline is stable.

## 25. Acceptance criteria for the design

The implementation is on the intended path when it can demonstrate all of the following on a Shandalar vertical slice:

1. English Adventure resources remain logically intact.
2. The scanner extracts only classified player-visible text.
3. Functional fields are demonstrably unchanged.
4. Tokens such as `$(enemy_1)` survive translation intact.
5. A local zero-paid-API translation path works after setup.
6. Glossary rules are applied consistently.
7. Human review state persists.
8. Approved translations generate deterministic Forge localization artifacts.
9. Dialogue uses existing localization hooks.
10. At least one previously unsupported resource type uses the new fallback-safe localization extension.
11. `doctor` detects deliberately introduced structural corruption.
12. Updating the English source marks changed strings without invalidating unchanged approved translations.
13. The same core workflow is callable from CLI and the GUI frontend.
14. The design remains usable on Windows, Linux and macOS.

## 26. Approved project decisions

The following decisions were explicitly approved during design discussion:

- translate all Adventure planes;
- complete Adventure scope rather than dialogues only;
- natural PT-BR localization style;
- `master` kept clean and `ptbr-adventure` used as the localization integration branch;
- hybrid translation-file architecture with generated Forge bundle;
- automatic translation plus review;
- hybrid local translation with optional AI review;
- no mandatory paid service;
- cross-platform support;
- CLI + GUI using one shared engine;
- Python-based tooling kept separate from Forge's Java runtime;
- safe typed scanner rather than indiscriminate string replacement;
- minimal localization extensions for unsupported Adventure data;
- translation memory, Magic glossary and validation gates;
- incremental upstream change detection.

## 27. Next step

After review and approval of this written specification, create a detailed implementation plan with file-level tasks, test-first checkpoints and commit boundaries. No broad implementation should begin before that plan is reviewed.
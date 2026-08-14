from forge_ptbr.quality.checks import evaluate_quality


def test_clean_translation_scores_100() -> None:
    result = evaluate_quality("Defeat the dragon.", "Derrote o dragão.")
    assert result.score == 100
    assert result.flags == ()


def test_missing_token_is_hard_failure() -> None:
    result = evaluate_quality("Defeat $(enemy_1).", "Derrote o inimigo.")
    assert result.score == 0
    assert "missing_token:$(enemy_1)" in result.flags


def test_blank_or_leaked_mask_is_hard_failure() -> None:
    assert evaluate_quality("Hello", "   ").score == 0
    leaked = evaluate_quality("Hello $(playername)", "Olá __FORGE_TOKEN_0__")
    assert leaked.score == 0
    assert "leaked_token_mask" in leaked.flags


def test_unchanged_english_and_glossary_violation_require_review() -> None:
    unchanged = evaluate_quality("Return to the graveyard", "Return to the graveyard")
    assert unchanged.score < 100
    assert "suspicious_unchanged_source" in unchanged.flags

    glossary = evaluate_quality(
        "Return to the Graveyard",
        "Retorne ao descarte",
        glossary_flags=("glossary_missing:Graveyard",),
    )
    assert "glossary_missing:Graveyard" in glossary.flags
    assert glossary.score < 100

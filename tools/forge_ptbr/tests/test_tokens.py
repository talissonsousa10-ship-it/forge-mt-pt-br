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


def test_extract_tokens_preserves_decoded_newline_from_json() -> None:
    text = "First line\nSecond line"
    assert extract_tokens(text) == ("\n",)

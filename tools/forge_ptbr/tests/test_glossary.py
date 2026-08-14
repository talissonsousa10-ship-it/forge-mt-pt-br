from pathlib import Path

from forge_ptbr.glossary.apply import apply_glossary, detect_terms
from forge_ptbr.glossary.model import GlossaryTerm
from forge_ptbr.glossary.store import load_glossary


def test_whole_word_detection_avoids_substrings() -> None:
    term = GlossaryTerm("Mana", "mana", case_sensitive=False, whole_word=True)
    assert detect_terms("Gain Mana now", [term]) == [term]
    assert detect_terms("A manatee appears", [term]) == []


def test_unambiguous_english_term_left_in_candidate_is_corrected() -> None:
    term = GlossaryTerm("Flying", "Voar", case_sensitive=False, whole_word=True)
    result = apply_glossary("Flying creature", "Criatura com Flying", [term])
    assert result.text == "Criatura com Voar"
    assert result.flags == ()


def test_missing_canonical_term_is_flagged_for_review() -> None:
    term = GlossaryTerm("Graveyard", "cemitério", case_sensitive=False, whole_word=True)
    result = apply_glossary("Return from your Graveyard", "Retorne do seu descarte", [term])
    assert result.text == "Retorne do seu descarte"
    assert result.flags == ("glossary_missing:Graveyard",)


def test_context_restricted_term_is_not_forced_outside_context() -> None:
    term = GlossaryTerm(
        "Library",
        "grimório",
        case_sensitive=False,
        whole_word=True,
        contexts=("rules", "magic"),
    )
    result = apply_glossary("Go to the Library", "Vá para a biblioteca", [term], context="dialog")
    assert result.flags == ()


def test_seed_glossary_loads(tmp_path: Path) -> None:
    path = tmp_path / "glossary.json"
    path.write_text(
        '{"schema_version":1,"terms":[{"source":"Flying","target":"Voar","case_sensitive":false,"whole_word":true}]}',
        encoding="utf-8",
    )
    terms = load_glossary(path)
    assert terms[0].target == "Voar"

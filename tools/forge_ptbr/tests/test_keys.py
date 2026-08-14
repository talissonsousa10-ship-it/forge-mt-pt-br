from forge_ptbr.catalog.keys import make_localization_key, slugify_key_part


def test_key_is_deterministic_for_same_source_identity() -> None:
    first = make_localization_key(
        source_id="src_1234567890abcdef1234",
        plane="Shandalar",
        resource_type="quests",
        field_name="description",
    )
    second = make_localization_key(
        source_id="src_1234567890abcdef1234",
        plane="Shandalar",
        resource_type="quests",
        field_name="description",
    )

    assert first == second
    assert first == "adv.shandalar.quests.description.90abcdef1234"


def test_key_normalizes_plane_and_field_without_translation_text() -> None:
    key = make_localization_key(
        source_id="src_aaaaaaaaaaaaaaaaaaaa",
        plane="Realm of Legends",
        resource_type="quest stages",
        field_name="Reward Description",
    )

    assert key == "adv.realm_of_legends.quest_stages.reward_description.aaaaaaaaaaaa"


def test_different_source_ids_produce_different_keys() -> None:
    left = make_localization_key("src_11111111111111111111", "Shandalar", "quests", "name")
    right = make_localization_key("src_22222222222222222222", "Shandalar", "quests", "name")

    assert left != right


def test_slugify_key_part_is_ascii_and_collapses_punctuation() -> None:
    assert slugify_key_part("Shandalar Old Border") == "shandalar_old_border"
    assert slugify_key_part("Descrição / Reward") == "descricao_reward"

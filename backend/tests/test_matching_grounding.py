"""Unit tests for matching pair groundedness helpers."""

from __future__ import annotations

from backend.app.domain.models import MatchingPair
from backend.app.generation.matching_grounding import is_matching_pair_grounded
from backend.app.generation.matching_grounding import normalize_grounding_text


def test_normalize_grounding_text_collapses_whitespace_and_casefolds() -> None:
    assert normalize_grounding_text("  Цианобактерии  и  водоросли  ") == "цианобактерии и водоросли"


def test_grounded_pair_both_sides_present_in_source() -> None:
    source = normalize_grounding_text(
        "Световая стадия протекает на мембранах тилакоидов. "
        "Темновая стадия происходит в строме хлоропласта."
    )
    pair = MatchingPair(left="Световая стадия", right="протекает на мембранах тилакоидов")
    assert is_matching_pair_grounded(pair, source)


def test_grounded_pair_left_present_right_paraphrased_with_absent_terms() -> None:
    source = normalize_grounding_text(
        "Фотолиз воды приводит к образованию кислорода."
    )
    pair = MatchingPair(left="Фотолиз воды", right="выделяет кислород при расщеплении воды")
    assert not is_matching_pair_grounded(pair, source)


def test_grounded_pair_left_present_right_subset_of_source() -> None:
    source = normalize_grounding_text(
        "Фотолиз воды приводит к образованию кислорода."
    )
    pair = MatchingPair(left="Фотолиз воды", right="приводит к образованию кислорода")
    assert is_matching_pair_grounded(pair, source)


def test_ungrounded_pair_absent_significant_term() -> None:
    source = normalize_grounding_text(
        "Кислородный фотосинтез характерен для высших растений и водорослей. "
        "Бескислородный фотосинтез встречается у некоторых бактерий."
    )
    pair = MatchingPair(left="Цианобактерии", right="Кислородный фотосинтез")
    assert not is_matching_pair_grounded(pair, source)


def test_ungrounded_pair_both_sides_absent() -> None:
    source = normalize_grounding_text("Фотосинтез происходит в хлоропластах.")
    pair = MatchingPair(left="Хемосинтезирующие бактерии", right="Бескислородный фотосинтез")
    assert not is_matching_pair_grounded(pair, source)


def test_grounded_pair_short_terms_pass() -> None:
    source = normalize_grounding_text("АТФ запасает энергию в клетке.")
    pair = MatchingPair(left="АТФ", right="запасает энергию")
    assert is_matching_pair_grounded(pair, source)


def test_ungrounded_pair_long_absent_term_in_right() -> None:
    source = normalize_grounding_text("Растения используют свет для фотосинтеза.")
    pair = MatchingPair(left="Растения", right="хемосинтезирующие организмы")
    assert not is_matching_pair_grounded(pair, source)


def test_grounded_photosynthesis_stages_pass() -> None:
    source = normalize_grounding_text(
        "Световая стадия протекает на мембранах тилакоидов. "
        "Темновая стадия происходит в строме хлоропласта. "
        "Фотолиз воды приводит к образованию кислорода. "
        "Цикл Кальвина превращает углекислый газ в углеводы."
    )
    pairs = (
        MatchingPair(left="Световая стадия", right="протекает на мембранах тилакоидов"),
        MatchingPair(left="Темновая стадия", right="происходит в строме хлоропласта"),
        MatchingPair(left="Фотолиз воды", right="приводит к образованию кислорода"),
        MatchingPair(left="Цикл Кальвина", right="превращает углекислый газ в углеводы"),
    )
    assert all(is_matching_pair_grounded(pair, source) for pair in pairs)


def test_ungrounded_cyanobacteria_pair_fails() -> None:
    source = normalize_grounding_text(
        "Кислородный фотосинтез характерен для высших растений и водорослей. "
        "Бескислородный фотосинтез встречается у некоторых бактерий."
    )
    pair = MatchingPair(left="Цианобактерии (сине-зелёные водоросли)", right="Кислородный фотосинтез")
    assert not is_matching_pair_grounded(pair, source)


def test_ungrounded_chemosynthetic_pair_fails() -> None:
    source = normalize_grounding_text(
        "Кислородный фотосинтез характерен для высших растений и водорослей. "
        "Бескислородный фотосинтез встречается у некоторых бактерий."
    )
    pair = MatchingPair(left="Хемосинтезирующие бактерии", right="Бескислородный фотосинтез")
    assert not is_matching_pair_grounded(pair, source)


def test_empty_pair_values_not_grounded() -> None:
    source = normalize_grounding_text("Some source text.")
    assert not is_matching_pair_grounded(MatchingPair(left="", right="text"), source)
    assert not is_matching_pair_grounded(MatchingPair(left="text", right=""), source)


def test_empty_source_text_not_grounded() -> None:
    pair = MatchingPair(left="Световая стадия", right="протекает на мембранах тилакоидов")
    assert not is_matching_pair_grounded(pair, "")

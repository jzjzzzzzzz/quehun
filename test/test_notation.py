import json
from pathlib import Path

import pytest

from ai.notation import (
    NotationError,
    count_tiles,
    dora_from_indicators,
    format_compact_hand,
    format_unicode_hand,
    hand_key,
    is_honor,
    is_simple,
    is_terminal,
    next_dora,
    parse_compact_hand,
    sort_hand,
    summarize_hand,
    tile_distance,
    tile_neighbors,
    tile_rank,
    tile_suit,
    validate_hand,
)


CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "notation_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", CASES["tiles"], ids=lambda case: case["tile"])
def test_tile_contract(case):
    tile = case["tile"]
    assert parse_compact_hand(case["alias"]) == [tile]
    assert parse_compact_hand(case["compact"]) == [tile]
    assert parse_compact_hand(case["unicode"]) == [tile]
    assert format_compact_hand([tile]) == case["compact"]
    assert format_unicode_hand([tile]) == case["unicode"]
    assert tile_suit(tile) == case["suit"]
    assert tile_rank(tile) == case["rank"]
    assert is_terminal(tile) is case["terminal"]
    assert is_honor(tile) is case["honor"]
    assert is_simple(tile) is case["simple"]


@pytest.mark.parametrize("case", CASES["hands"], ids=lambda case: case["name"])
def test_hand_notation_contract(case):
    parsed = parse_compact_hand(case["notation"])
    assert parsed == case["tiles"]
    if "formatted" in case:
        assert format_compact_hand(parsed, sort_tiles=case.get("sort", True)) == case["formatted"]
    if case.get("roundtrip"):
        assert parse_compact_hand(format_compact_hand(parsed)) == sort_hand(parsed)


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda case: case["name"])
def test_invalid_notation_contract(case):
    with pytest.raises(NotationError, match=case.get("match", "")):
        parse_compact_hand(case["notation"])


@pytest.mark.parametrize("case", CASES["dora"], ids=lambda case: case["name"])
def test_dora_contract(case):
    assert next_dora(case["indicator"]) == case["dora"]
    assert dora_from_indicators([case["indicator"]]) == [case["dora"]]


@pytest.mark.parametrize("case", CASES["validation"], ids=lambda case: case["name"])
def test_validation_contract(case):
    result = validate_hand(case["tiles"], expected_sizes=case.get("expected_sizes", [13, 14]))
    assert result.valid is case["valid"]
    assert len(result.errors) == case.get("error_count", len(result.errors))
    if "warning_count" in case:
        assert len(result.warnings) == case["warning_count"]


def test_summary_counts_unique_shapes_once():
    summary = summarize_hand(parse_compact_hand("111122233m44z"))
    assert summary.total == 11
    assert summary.unique == 4
    assert summary.quads == ("characters-1",)
    assert summary.triplets == ("characters-1", "characters-2")
    assert summary.pairs == (
        "characters-1",
        "characters-2",
        "characters-3",
        "honors-north",
    )


def test_bonus_tile_is_not_accepted_as_a_playable_hand_tile():
    with pytest.raises(NotationError, match="unknown tile"):
        parse_compact_hand(["spring"])


@pytest.mark.parametrize("tile", ["bogus", "spring", None])
def test_compact_formatter_rejects_non_playable_tiles(tile):
    with pytest.raises(NotationError, match="unknown tile"):
        format_compact_hand([tile])


def test_count_tiles_canonicalizes_aliases_and_drops_noise():
    counts = count_tiles(["m1", "characters-1", "east", "bogus"])

    assert counts == {"characters-1": 2, "honors-east": 1}


def test_hand_key_is_independent_of_recognition_order():
    left = hand_key(["east", "p3", "m1", "m1"])
    right = hand_key(["characters-1", "m1", "dots-3", "honors-east"])

    assert left == right


def test_suited_neighbors_respect_edges_and_distance():
    assert tile_neighbors("m1") == ("characters-2", "characters-3")
    assert tile_neighbors("p5", distance=1) == ("dots-4", "dots-6")
    assert tile_neighbors("east") == ()
    assert tile_distance("s2", "bamboo-5") == 3
    assert tile_distance("m2", "p2") is None

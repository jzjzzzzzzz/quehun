"""Mahjong tile notation, ordering, metadata, and validation helpers.

The recognition pipeline uses descriptive tile names such as
``characters-1`` while humans usually type compact strings such as
``123m456p789s12344z``.  This module keeps the conversion rules in one place
so command-line tools, tests, and future replay importers share the same
behaviour.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re
from typing import Iterable, Sequence

from ai.tile_set import PLAYABLE_TILES, canonical_tile


COMPACT_SUITS = {
    "m": "characters",
    "p": "dots",
    "s": "bamboo",
}
SUIT_MARKERS = {name: marker for marker, name in COMPACT_SUITS.items()}
HONOR_DIGITS = {
    "1": "honors-east",
    "2": "honors-south",
    "3": "honors-west",
    "4": "honors-north",
    "5": "honors-white",
    "6": "honors-green",
    "7": "honors-red",
}
HONOR_MARKERS = {tile: digit for digit, tile in HONOR_DIGITS.items()}

UNICODE_TILES = {
    **{f"characters-{rank}": chr(0x1F006 + rank) for rank in range(1, 10)},
    **{f"bamboo-{rank}": chr(0x1F00F + rank) for rank in range(1, 10)},
    **{f"dots-{rank}": chr(0x1F018 + rank) for rank in range(1, 10)},
    "honors-east": chr(0x1F000),
    "honors-south": chr(0x1F001),
    "honors-west": chr(0x1F002),
    "honors-north": chr(0x1F003),
    "honors-red": chr(0x1F004),
    "honors-green": chr(0x1F005),
    "honors-white": chr(0x1F006),
}
UNICODE_TO_TILE = {symbol: tile for tile, symbol in UNICODE_TILES.items()}

_GROUP_RE = re.compile(r"([0-9]+)([mpsz])", re.IGNORECASE)
_SEPARATOR_RE = re.compile(r"[\s,;|/]+")


class NotationError(ValueError):
    """Raised when a hand notation string cannot be parsed exactly."""


@dataclass(frozen=True)
class TileSummary:
    """A compact, immutable summary of a canonicalized hand."""

    total: int
    unique: int
    suits: dict[str, int]
    pairs: tuple[str, ...]
    triplets: tuple[str, ...]
    quads: tuple[str, ...]
    honors: int
    terminals: int


@dataclass(frozen=True)
class HandValidation:
    """Validation result that is safe to show directly in CLI/UI diagnostics."""

    valid: bool
    tiles: tuple[str, ...]
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


def tile_suit(tile: str) -> str | None:
    """Return ``characters``, ``dots``, ``bamboo``, or ``honors``."""

    value = canonical_tile(tile)
    if value is None or value not in PLAYABLE_TILES:
        return None
    return value.split("-", 1)[0]


def tile_rank(tile: str) -> int | None:
    """Return a suited rank, or ``None`` for honors and invalid tiles."""

    value = canonical_tile(tile)
    if value is None or value.startswith("honors-"):
        return None
    try:
        return int(value.rsplit("-", 1)[1])
    except (TypeError, ValueError):
        return None


def is_honor(tile: str) -> bool:
    return tile_suit(tile) == "honors"


def is_suited(tile: str) -> bool:
    return tile_suit(tile) in {"characters", "dots", "bamboo"}


def is_terminal(tile: str) -> bool:
    return tile_rank(tile) in {1, 9}


def is_simple(tile: str) -> bool:
    rank = tile_rank(tile)
    return rank is not None and 2 <= rank <= 8


def is_terminal_or_honor(tile: str) -> bool:
    return is_honor(tile) or is_terminal(tile)


def same_suit(left: str, right: str) -> bool:
    """Return true only for two valid suited tiles from the same suit."""

    suit = tile_suit(left)
    return suit in {"characters", "dots", "bamboo"} and suit == tile_suit(right)


def tile_distance(left: str, right: str) -> int | None:
    """Return rank distance for two tiles in one suit, otherwise ``None``."""

    if not same_suit(left, right):
        return None
    return abs(tile_rank(left) - tile_rank(right))


def tile_sort_key(tile: str) -> tuple[int, int]:
    """Return a deterministic Japanese-mahjong display order key."""

    value = canonical_tile(tile)
    if value not in PLAYABLE_TILES:
        return (99, 99)
    return divmod(PLAYABLE_TILES.index(value), 9)


def sort_hand(hand: Iterable[str]) -> list[str]:
    """Canonicalize, discard invalid values, and sort a hand."""

    tiles = [canonical_tile(tile) for tile in hand or []]
    return sorted((tile for tile in tiles if tile in PLAYABLE_TILES), key=tile_sort_key)


def parse_compact_hand(value: str | Iterable[str]) -> list[str]:
    """Parse compact, Unicode, or separated alias notation.

    Standard compact suit suffixes are supported: ``m`` for characters,
    ``p`` for dots, ``s`` for bamboo, and ``z`` for honors.  Zero in a suited
    group is accepted as a red-five spelling and normalized to rank five.
    Honor digits follow the common ``ESWN白發中`` order 1 through 7.
    """

    if not isinstance(value, str):
        raw_tiles = list(value or [])
        parsed = [canonical_tile(tile) for tile in raw_tiles]
        if any(tile not in PLAYABLE_TILES for tile in parsed):
            raise NotationError("tile list contains an unknown tile")
        return parsed

    text = value.strip().lower()
    if not text:
        return []

    visible_chars = [char for char in text if not _SEPARATOR_RE.fullmatch(char)]
    if visible_chars and all(char in UNICODE_TO_TILE for char in visible_chars):
        return [UNICODE_TO_TILE[char] for char in visible_chars]

    tokens = [token for token in _SEPARATOR_RE.split(text) if token]
    aliases = [canonical_tile(token) for token in tokens]
    if tokens and all(tile in PLAYABLE_TILES for tile in aliases):
        return aliases

    compact = _SEPARATOR_RE.sub("", text)
    tiles: list[str] = []
    position = 0
    for match in _GROUP_RE.finditer(compact):
        if match.start() != position:
            raise NotationError(f"invalid notation near {compact[position:match.start()]!r}")
        digits, marker = match.groups()
        marker = marker.lower()
        for digit in digits:
            if marker == "z":
                tile = HONOR_DIGITS.get(digit)
                if tile is None:
                    raise NotationError(f"honor digit must be 1-7, got {digit!r}")
            else:
                if digit == "0":
                    digit = "5"
                if digit not in "123456789":
                    raise NotationError(f"suited digit must be 0-9, got {digit!r}")
                tile = f"{COMPACT_SUITS[marker]}-{digit}"
            tiles.append(tile)
        position = match.end()

    if not tiles or position != len(compact):
        raise NotationError(f"invalid hand notation: {value!r}")
    return tiles


def format_compact_hand(hand: Iterable[str], *, sort_tiles: bool = True) -> str:
    """Format tiles as grouped compact notation."""

    raw = list(hand or [])
    tiles = sort_hand(raw) if sort_tiles else [canonical_tile(tile) for tile in raw]
    if any(tile not in PLAYABLE_TILES for tile in tiles):
        raise NotationError("cannot format an unknown tile")

    groups: list[str] = []
    for suit in ("characters", "dots", "bamboo"):
        digits = "".join(str(tile_rank(tile)) for tile in tiles if tile_suit(tile) == suit)
        if digits:
            groups.append(f"{digits}{SUIT_MARKERS[suit]}")
    honors = "".join(HONOR_MARKERS[tile] for tile in tiles if is_honor(tile))
    if honors:
        groups.append(f"{honors}z")
    return "".join(groups)


def format_unicode_hand(hand: Iterable[str], *, separator: str = "") -> str:
    """Format a hand with Unicode Mahjong Tile symbols."""

    symbols = []
    for raw_tile in hand or []:
        tile = canonical_tile(raw_tile)
        if tile not in UNICODE_TILES:
            raise NotationError(f"cannot format unknown tile {raw_tile!r}")
        symbols.append(UNICODE_TILES[tile])
    return separator.join(symbols)


def next_dora(indicator: str) -> str | None:
    """Return the dora represented by one indicator tile."""

    tile = canonical_tile(indicator)
    rank = tile_rank(tile)
    if rank is not None:
        return f"{tile_suit(tile)}-{rank % 9 + 1}"

    cycles = (
        ("honors-east", "honors-south", "honors-west", "honors-north"),
        ("honors-white", "honors-green", "honors-red"),
    )
    for cycle in cycles:
        if tile in cycle:
            return cycle[(cycle.index(tile) + 1) % len(cycle)]
    return None


def dora_from_indicators(indicators: Iterable[str]) -> list[str]:
    return [dora for tile in indicators or [] if (dora := next_dora(tile)) is not None]


def summarize_hand(hand: Iterable[str]) -> TileSummary:
    tiles = sort_hand(hand)
    counts = Counter(tiles)
    return TileSummary(
        total=len(tiles),
        unique=len(counts),
        suits={
            suit: sum(count for tile, count in counts.items() if tile_suit(tile) == suit)
            for suit in ("characters", "dots", "bamboo", "honors")
        },
        pairs=tuple(tile for tile in counts if counts[tile] >= 2),
        triplets=tuple(tile for tile in counts if counts[tile] >= 3),
        quads=tuple(tile for tile in counts if counts[tile] == 4),
        honors=sum(count for tile, count in counts.items() if is_honor(tile)),
        terminals=sum(count for tile, count in counts.items() if is_terminal(tile)),
    )


def validate_hand(
    hand: Sequence[str] | Iterable[str],
    *,
    expected_sizes: Iterable[int] | None = (13, 14),
) -> HandValidation:
    """Validate names, physical copy limits, and optionally hand size."""

    raw_tiles = list(hand or [])
    canonical = [canonical_tile(tile) for tile in raw_tiles]
    errors: list[str] = []
    warnings: list[str] = []

    invalid = [str(raw) for raw, tile in zip(raw_tiles, canonical) if tile not in PLAYABLE_TILES]
    if invalid:
        errors.append(f"unknown tiles: {', '.join(invalid)}")

    tiles = tuple(tile for tile in canonical if tile in PLAYABLE_TILES)
    overfull = sorted(tile for tile, count in Counter(tiles).items() if count > 4)
    if overfull:
        errors.append(f"more than four copies: {', '.join(overfull)}")

    if expected_sizes is not None:
        sizes = tuple(sorted(set(int(size) for size in expected_sizes)))
        if len(raw_tiles) not in sizes:
            errors.append(
                f"hand has {len(raw_tiles)} tiles; expected "
                + " or ".join(str(size) for size in sizes)
            )

    if len(tiles) == 14 and len(set(tiles)) <= 5:
        warnings.append("hand has unusually few distinct tiles")

    return HandValidation(
        valid=not errors,
        tiles=tiles,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

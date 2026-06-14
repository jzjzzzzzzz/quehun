from collections import Counter

from ai.agari import is_win
from ai.shanten import simple_shanten
from ai.tile_set import PLAYABLE_TILES, canonical_hand


def build_pool():
    pool = []
    for tile in PLAYABLE_TILES:
        pool.extend([tile] * 4)
    return pool


POOL = build_pool()


def remaining_counts(visible_tiles):
    visible = Counter(canonical_hand(visible_tiles))
    return {tile: max(0, 4 - visible[tile]) for tile in PLAYABLE_TILES}


def effective_tiles(hand, visible_tiles=None):
    hand = canonical_hand(hand)
    visible = canonical_hand(visible_tiles) if visible_tiles is not None else hand
    remaining = remaining_counts(visible)
    base = simple_shanten(hand)
    effective = {}

    for tile, count in remaining.items():
        if count <= 0:
            continue

        test_hand = hand + [tile]
        next_shanten = simple_shanten(test_hand)
        if base == 0 and is_win(test_hand):
            effective[tile] = count
        elif base > 0 and next_shanten < base:
            effective[tile] = count

    return effective


def ukeire(hand, visible_tiles=None):
    return sum(effective_tiles(hand, visible_tiles=visible_tiles).values())

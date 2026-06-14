from ai.agari import winning_tiles
from ai.tile_set import PLAYABLE_TILES, canonical_hand
from ai.ukeire import remaining_counts


def draw_probability(effective_tiles, visible_tiles=None, draws=1):
    visible = canonical_hand(visible_tiles)
    remaining = remaining_counts(visible)
    total_remaining = sum(remaining.values())
    effective_count = sum(remaining.get(tile, 0) for tile in effective_tiles)

    if total_remaining <= 0 or effective_count <= 0 or draws <= 0:
        return 0.0

    miss_probability = 1.0
    for i in range(min(draws, total_remaining)):
        miss_probability *= max(0, total_remaining - effective_count - i) / (total_remaining - i)

    return 1.0 - miss_probability


def tenpai_probability(hand, visible_tiles=None, draws=1):
    waits = winning_tiles(hand, visible_tiles=visible_tiles)
    return draw_probability(waits, visible_tiles=visible_tiles or hand, draws=draws)


def remaining_summary(visible_tiles=None):
    remaining = remaining_counts(canonical_hand(visible_tiles))
    return {tile: count for tile, count in remaining.items() if count}

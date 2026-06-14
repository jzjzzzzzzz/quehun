from functools import lru_cache

from ai.tile_set import PLAYABLE_TILES, canonical_hand


ORPHANS = {
    "characters-1", "characters-9",
    "dots-1", "dots-9",
    "bamboo-1", "bamboo-9",
    "honors-east", "honors-south", "honors-west", "honors-north",
    "honors-red", "honors-green", "honors-white",
}


def clean_tile(tile):
    hand = canonical_hand([tile])
    return hand[0] if hand else None


def _counts(hand):
    counts = [0] * len(PLAYABLE_TILES)
    for tile in canonical_hand(hand):
        counts[PLAYABLE_TILES.index(tile)] += 1
    return tuple(counts)


@lru_cache(maxsize=None)
def _meld_taatsu(counts):
    counts = list(counts)

    try:
        i = next(idx for idx, count in enumerate(counts) if count)
    except StopIteration:
        return (0, 0)

    best_melds, best_taatsu = 0, 0

    counts[i] -= 1
    best_melds, best_taatsu = _meld_taatsu(tuple(counts))
    counts[i] += 1

    if counts[i] >= 3:
        counts[i] -= 3
        melds, taatsu = _meld_taatsu(tuple(counts))
        best_melds, best_taatsu = max((best_melds, best_taatsu), (melds + 1, taatsu))
        counts[i] += 3

    suit_start = (i // 9) * 9
    is_suited = i < 27
    rank = i - suit_start

    if is_suited and rank <= 6 and counts[i + 1] and counts[i + 2]:
        counts[i] -= 1
        counts[i + 1] -= 1
        counts[i + 2] -= 1
        melds, taatsu = _meld_taatsu(tuple(counts))
        best_melds, best_taatsu = max((best_melds, best_taatsu), (melds + 1, taatsu))
        counts[i] += 1
        counts[i + 1] += 1
        counts[i + 2] += 1

    if counts[i] >= 2:
        counts[i] -= 2
        melds, taatsu = _meld_taatsu(tuple(counts))
        best_melds, best_taatsu = max((best_melds, best_taatsu), (melds, taatsu + 1))
        counts[i] += 2

    if is_suited and rank <= 7 and counts[i + 1]:
        counts[i] -= 1
        counts[i + 1] -= 1
        melds, taatsu = _meld_taatsu(tuple(counts))
        best_melds, best_taatsu = max((best_melds, best_taatsu), (melds, taatsu + 1))
        counts[i] += 1
        counts[i + 1] += 1

    if is_suited and rank <= 6 and counts[i + 2]:
        counts[i] -= 1
        counts[i + 2] -= 1
        melds, taatsu = _meld_taatsu(tuple(counts))
        best_melds, best_taatsu = max((best_melds, best_taatsu), (melds, taatsu + 1))
        counts[i] += 1
        counts[i + 2] += 1

    return best_melds, best_taatsu


def standard_shanten(hand):
    counts = list(_counts(hand))
    best = 8

    pair_options = [None] + [idx for idx, count in enumerate(counts) if count >= 2]
    for pair_idx in pair_options:
        work = counts.copy()
        has_pair = 0

        if pair_idx is not None:
            work[pair_idx] -= 2
            has_pair = 1

        melds, taatsu = _meld_taatsu(tuple(work))
        taatsu = min(taatsu, 4 - melds)
        best = min(best, 8 - melds * 2 - taatsu - has_pair)

    return max(best, -1)


def seven_pairs_shanten(hand):
    hand = canonical_hand(hand)
    counts = _counts(hand)
    pairs = sum(1 for count in counts if count >= 2)
    unique = sum(1 for count in counts if count > 0)
    return max(-1, 6 - pairs + max(0, 7 - unique))


def thirteen_orphans_shanten(hand):
    hand = canonical_hand(hand)
    unique = len(set(hand) & ORPHANS)
    has_pair = any(hand.count(tile) >= 2 for tile in ORPHANS)
    return max(-1, 13 - unique - int(has_pair))


def simple_shanten(hand):
    hand = canonical_hand(hand)
    return min(
        standard_shanten(hand),
        seven_pairs_shanten(hand),
        thirteen_orphans_shanten(hand),
    )

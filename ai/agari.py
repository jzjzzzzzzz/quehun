from functools import lru_cache

from ai.tile_set import PLAYABLE_TILES, canonical_hand


def hand_counts(hand):
    counts = [0] * len(PLAYABLE_TILES)
    for tile in canonical_hand(hand):
        counts[PLAYABLE_TILES.index(tile)] += 1
    return tuple(counts)


@lru_cache(maxsize=None)
def _can_form_melds(counts):
    counts = list(counts)

    try:
        i = next(idx for idx, count in enumerate(counts) if count)
    except StopIteration:
        return True

    if counts[i] >= 3:
        counts[i] -= 3
        if _can_form_melds(tuple(counts)):
            return True
        counts[i] += 3

    if i < 27:
        suit_start = (i // 9) * 9
        rank = i - suit_start
        if rank <= 6 and counts[i + 1] and counts[i + 2]:
            counts[i] -= 1
            counts[i + 1] -= 1
            counts[i + 2] -= 1
            if _can_form_melds(tuple(counts)):
                return True

    return False


def is_standard_win(hand):
    hand = canonical_hand(hand)
    if len(hand) % 3 != 2:
        return False

    counts = list(hand_counts(hand))
    for pair_idx, count in enumerate(counts):
        if count < 2:
            continue

        work = counts.copy()
        work[pair_idx] -= 2
        if _can_form_melds(tuple(work)):
            return True

    return False


def is_seven_pairs(hand):
    hand = canonical_hand(hand)
    if len(hand) != 14:
        return False

    counts = hand_counts(hand)
    return sum(1 for count in counts if count == 2) == 7


def is_win(hand):
    return is_standard_win(hand) or is_seven_pairs(hand)


def winning_tiles(hand, visible_tiles=None):
    hand = canonical_hand(hand)
    visible = canonical_hand(visible_tiles) if visible_tiles is not None else hand
    waits = []

    for tile in PLAYABLE_TILES:
        if visible.count(tile) >= 4:
            continue
        if is_win(hand + [tile]):
            waits.append(tile)

    return waits

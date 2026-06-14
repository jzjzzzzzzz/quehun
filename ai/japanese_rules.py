from collections import Counter

from ai.agari import hand_counts, is_seven_pairs, is_standard_win, is_win
from ai.tile_set import PLAYABLE_TILES, canonical_hand


DRAGONS = {"honors-red", "honors-green", "honors-white"}
WINDS = {"honors-east", "honors-south", "honors-west", "honors-north"}
TERMINALS = {
    "characters-1", "characters-9",
    "dots-1", "dots-9",
    "bamboo-1", "bamboo-9",
}
HONORS = DRAGONS | WINDS


def is_simple(tile):
    return tile not in TERMINALS and tile not in HONORS


def suit_name(tile):
    if tile.startswith("characters-"):
        return "characters"
    if tile.startswith("dots-"):
        return "dots"
    if tile.startswith("bamboo-"):
        return "bamboo"
    return "honors"


def _remove_melds(counts):
    counts = list(counts)
    melds = []

    def search(work, out):
        try:
            i = next(idx for idx, count in enumerate(work) if count)
        except StopIteration:
            return out.copy()

        tile = PLAYABLE_TILES[i]
        if work[i] >= 3:
            work[i] -= 3
            result = search(work, out + [("triplet", [tile, tile, tile])])
            work[i] += 3
            if result is not None:
                return result

        if i < 27:
            suit_start = (i // 9) * 9
            rank = i - suit_start
            if rank <= 6 and work[i + 1] and work[i + 2]:
                tiles = [PLAYABLE_TILES[i], PLAYABLE_TILES[i + 1], PLAYABLE_TILES[i + 2]]
                work[i] -= 1
                work[i + 1] -= 1
                work[i + 2] -= 1
                result = search(work, out + [("sequence", tiles)])
                work[i] += 1
                work[i + 1] += 1
                work[i + 2] += 1
                if result is not None:
                    return result

        return None

    for pair_idx, count in enumerate(counts):
        if count < 2:
            continue
        work = counts.copy()
        pair_tile = PLAYABLE_TILES[pair_idx]
        work[pair_idx] -= 2
        melds = search(work, [])
        if melds is not None:
            return pair_tile, melds

    return None, []


def decompose_standard_hand(hand):
    hand = canonical_hand(hand)
    if not is_standard_win(hand):
        return None, []
    return _remove_melds(hand_counts(hand))


def yaku_for_win(hand, win_method="tsumo", seat_wind="east", round_wind="east", riichi=False):
    hand = canonical_hand(hand)
    if not is_win(hand):
        return []

    yaku = []
    counts = Counter(hand)

    if win_method == "tsumo":
        yaku.append("menzen_tsumo")

    if riichi:
        yaku.append("riichi")

    if all(is_simple(tile) for tile in hand):
        yaku.append("tanyao")

    if is_seven_pairs(hand):
        yaku.append("chiitoitsu")

    pair, melds = decompose_standard_hand(hand)
    if melds:
        triplets = [tiles for kind, tiles in melds if kind == "triplet"]
        sequences = [tiles for kind, tiles in melds if kind == "sequence"]

        for tiles in triplets:
            tile = tiles[0]
            if tile in DRAGONS:
                yaku.append(f"yakuhai_{tile.split('-')[1]}")
            if tile == f"honors-{seat_wind}":
                yaku.append("seat_wind")
            if tile == f"honors-{round_wind}":
                yaku.append("round_wind")

        if len(triplets) == 4:
            yaku.append("toitoi")

        if len(sequences) == 4 and pair not in DRAGONS:
            yaku.append("pinfu_shape")

    suits = {suit_name(tile) for tile in hand if suit_name(tile) != "honors"}
    has_honor = any(tile in HONORS for tile in hand)
    if len(suits) == 1 and has_honor:
        yaku.append("honitsu")
    elif len(suits) == 1 and not has_honor:
        yaku.append("chinitsu")

    return yaku


def has_yaku(hand, **kwargs):
    return bool(yaku_for_win(hand, **kwargs))


def estimate_points(yaku, dealer=False, win_method="ron"):
    if not yaku:
        return 0

    han = 0
    for name in yaku:
        if name in {"honitsu"}:
            han += 2
        elif name in {"chinitsu"}:
            han += 5
        elif name == "toitoi":
            han += 2
        elif name == "chiitoitsu":
            han += 2
        else:
            han += 1

    if han >= 5:
        return 12000 if dealer else 8000
    if han >= 3:
        return 7700 if dealer else 5200
    if han == 2:
        return 3900 if dealer else 2600
    return 1500 if dealer else 1000

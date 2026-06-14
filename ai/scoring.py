from collections import Counter

from ai.tile_set import canonical_hand


def tile_diversity(hand):
    suits = [tile.split("-")[0] for tile in canonical_hand(hand)]
    return len(set(suits))


def pair_count(hand):
    counts = Counter(canonical_hand(hand))
    return sum(1 for count in counts.values() if count >= 2)

from ai.scoring import pair_count, tile_diversity


def strategy_score(hand, shanten, ukeire_count):
    return (
        -shanten * 200
        + ukeire_count * 5
        + pair_count(hand) * 20
        + tile_diversity(hand) * 3
    )

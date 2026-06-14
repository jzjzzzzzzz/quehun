from ai.engine import decide


def evaluate_discard(hand, visible_tiles=None):
    result = decide(hand, visible_tiles=visible_tiles)
    return result["discard"], result["score"]

from ai.shanten import simple_shanten
from ai.strategy import strategy_score
from ai.tile_set import canonical_hand
from ai.ukeire import ukeire
from ai.agari import winning_tiles
from ai.probability import draw_probability
from ai.advisor import analyze_hand


def decide(hand, visible_tiles=None):
    hand = canonical_hand(hand)
    if not hand:
        return {
            "discard": None,
            "score": None,
            "shanten": None,
            "ukeire": 0,
            "candidates": [],
            "waits": [],
            "win_probability": 0.0,
        }

    candidates = []
    best = None
    visible = canonical_hand(visible_tiles) if visible_tiles is not None else hand

    for tile in sorted(set(hand)):
        after_discard = hand.copy()
        after_discard.remove(tile)

        shanten = simple_shanten(after_discard)
        ukeire_count = ukeire(after_discard, visible_tiles=visible)
        waits = winning_tiles(after_discard, visible_tiles=visible)
        win_probability = draw_probability(waits, visible_tiles=visible, draws=1)
        score = strategy_score(after_discard, shanten, ukeire_count) + int(win_probability * 1000)

        candidate = {
            "discard": tile,
            "score": score,
            "shanten": shanten,
            "ukeire": ukeire_count,
            "waits": waits,
            "win_probability": win_probability,
        }
        candidates.append(candidate)

        if best is None or (score, ukeire_count, -shanten) > (
            best["score"],
            best["ukeire"],
            -best["shanten"],
        ):
            best = candidate

    advisor = analyze_hand(hand, visible_tiles=visible, recognition_confidence=1.0)
    advice_by_tile = {
        choice.discard: choice
        for choice in advisor.top_choices
    }
    for candidate in candidates:
        advice = advice_by_tile.get(candidate["discard"])
        candidate["reasons"] = advice.reasons if advice else []

    candidates.sort(key=lambda item: (-item["score"], item["shanten"], -item["ukeire"]))
    return {
        "discard": best["discard"],
        "score": best["score"],
        "shanten": best["shanten"],
        "ukeire": best["ukeire"],
        "waits": best["waits"],
        "win_probability": best["win_probability"],
        "candidates": candidates,
        "top_choices": [choice.to_dict() for choice in advisor.top_choices],
        "yaku_tendencies": advisor.yaku_tendencies,
        "warnings": advisor.warnings,
    }

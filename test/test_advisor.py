import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.advisor import analyze_hand, tile_danger
from ai.shanten import seven_pairs_shanten, thirteen_orphans_shanten


def test_special_shanten():
    seven_pairs = ["m1", "m1", "m2", "m2", "p3", "p3", "p4", "p4", "s5", "s5", "east", "east", "red"]
    assert seven_pairs_shanten(seven_pairs) == 0
    orphans = ["m1", "m9", "p1", "p9", "s1", "s9", "east", "south", "west", "north", "white", "green", "red"]
    assert thirteen_orphans_shanten(orphans) == 0


def test_advisor_top_three_and_warning():
    hand = [
        "m1", "m2", "m3", "p5", "p6", "p7", "s7", "s8", "s9",
        "east", "east", "red", "green", "white",
    ]
    result = analyze_hand(hand, recognition_confidence=0.4)
    assert result.recommended_discard is not None
    assert len(result.top_choices) == 3
    assert all(choice.reasons for choice in result.top_choices)
    assert result.warnings
    assert tile_danger("east", discards={"left": ["east"]}) < 0.2


if __name__ == "__main__":
    test_special_shanten()
    test_advisor_top_three_and_warning()
    print("Advisor tests passed")

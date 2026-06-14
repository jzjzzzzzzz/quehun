import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.engine import decide
from ai.shanten import simple_shanten


def test_ai():
    hand = [
        "m1", "m2", "m3",
        "p5", "p6", "p7",
        "s7", "s8", "s9",
        "east", "east",
        "red", "green", "white",
    ]

    result = decide(hand)

    print("\nAI TEST RESULT")
    print("Recommended discard:", result["discard"])
    print("score:", result["score"])

    assert result["discard"] is not None
    assert result["shanten"] is not None
    assert isinstance(result["candidates"], list)
    assert simple_shanten(["m1", "m2", "m3", "p1", "p2", "p3", "s1", "s2", "s3", "east", "east", "red", "red", "red"]) <= 0

    print("AI test passed")


if __name__ == "__main__":
    test_ai()

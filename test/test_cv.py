import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cv.hand_parser import HandParser


def create_fake_frame():
    return np.zeros((256, 256, 3), dtype=np.uint8)


def test_cv():
    parser = HandParser()
    hand = parser.parse(create_fake_frame())

    print("\nCV TEST RESULT")
    print("Recognized hand:", hand)

    assert isinstance(hand, list)
    assert len(hand) == 14
    assert all("-" in tile for tile in hand)

    print("CV test passed")


if __name__ == "__main__":
    test_cv()

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.japanese_rules import estimate_points, yaku_for_win
from runtime.full_game import FullJapaneseGame


def test_basic_yaku_tsumo():
    hand = [
        "m2", "m3", "m4",
        "p2", "p3", "p4",
        "s3", "s4", "s5",
        "s6", "s7", "s8",
        "p5", "p5",
    ]

    yaku = yaku_for_win(hand, win_method="tsumo")
    assert "menzen_tsumo" in yaku
    assert "tanyao" in yaku
    assert estimate_points(yaku) > 0


def test_full_game_completes():
    game = FullJapaneseGame(seed=10, rounds=2)
    result = game.play_game()

    assert len(result["rounds"]) == 2
    assert len(result["scores"]) == 4
    assert sum(result["scores"].values()) == 100000
    assert result["log"]


if __name__ == "__main__":
    test_basic_yaku_tsumo()
    test_full_game_completes()
    print("Full game tests passed")

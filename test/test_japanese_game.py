import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.agari import is_win, winning_tiles
from runtime.japanese_game import JapaneseMahjongGame


def test_win_detection():
    hand = [
        "m1", "m2", "m3",
        "p1", "p2", "p3",
        "s1", "s2", "s3",
        "east", "east",
        "red", "red", "red",
    ]

    assert is_win(hand)


def test_winning_tiles():
    hand = [
        "m1", "m2", "m3",
        "p1", "p2", "p3",
        "s1", "s2", "s3",
        "east", "east",
        "red", "red",
    ]

    assert "honors-red" in winning_tiles(hand)


def test_game_step():
    game = JapaneseMahjongGame(seed=1)
    state = game.step()

    assert state["turn"] == 1
    assert len(state["hand"]) in (13, 14)
    assert state["wall_remaining"] == 122


def test_game_play():
    game = JapaneseMahjongGame(seed=2)
    history = game.play(max_turns=5)

    assert len(history) >= 1
    assert history[-1]["turn"] <= 5


if __name__ == "__main__":
    test_win_detection()
    test_winning_tiles()
    test_game_step()
    test_game_play()
    print("Japanese game tests passed")

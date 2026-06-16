import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.agari import THIRTEEN_ORPHANS, is_thirteen_orphans, is_win, winning_tiles
from ai.japanese_rules import estimate_points, yaku_for_win
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


def test_thirteen_orphans_win_and_thirteen_sided_wait():
    thirteen_unique = list(THIRTEEN_ORPHANS)
    completed = thirteen_unique + ["honors-east"]

    assert is_thirteen_orphans(completed)
    assert is_win(completed)
    assert not is_thirteen_orphans(thirteen_unique)
    assert set(winning_tiles(thirteen_unique)) == THIRTEEN_ORPHANS


def test_thirteen_orphans_yakuman_points():
    hand = list(THIRTEEN_ORPHANS) + ["honors-red"]
    yaku = yaku_for_win(hand, win_method="ron")

    assert "kokushi_musou" in yaku
    assert estimate_points(yaku, dealer=False) == 32000
    assert estimate_points(yaku, dealer=True) == 48000


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

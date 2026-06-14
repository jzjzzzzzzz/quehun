import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from state.game_state import GameState


def test_game_state_fields_and_compatibility():
    state = GameState(round_wind="east", seat_wind="south")
    state.update(
        ["m1", "m2"],
        visible_tiles=["m1", "m2", "east"],
        confidence=0.75,
        drawn_tile="m2",
        raw_debug_info={"source": "test"},
    )
    assert state.hand == ["m1", "m2"]
    assert state.get_hand() == ["m1", "m2"]
    assert state.drawn_tile == "m2"
    assert state.confidence == 0.75
    assert state.to_dict()["discards"]["self"] == []
    assert state.step == 1


if __name__ == "__main__":
    test_game_state_fields_and_compatibility()
    print("GameState tests passed")

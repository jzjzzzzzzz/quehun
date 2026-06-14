from ai.engine import decide
from ai.tile_set import canonical_hand
from cv.hand_parser import HandParser
from state.game_state import GameState
from state.sync import FrameSync


class Pipeline:
    def __init__(self, parser=None, sync=None, state=None):
        self.parser = parser or HandParser()
        self.sync = sync or FrameSync()
        self.state = state or GameState()

    def process(self, frame):
        hand = canonical_hand(self.parser.parse(frame))

        if len(hand) < 1:
            return None

        if not self.sync.update(hand):
            return None

        self.state.update(hand, visible_tiles=hand)
        result = decide(hand, visible_tiles=self.state.get_visible_tiles())
        result["hand"] = hand
        return result

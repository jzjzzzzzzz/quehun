from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class GameState:
    current_hand: list[str] = field(default_factory=list)
    drawn_tile: Optional[str] = None
    discards: dict[str, list[str]] = field(
        default_factory=lambda: {
            "self": [],
            "right": [],
            "opposite": [],
            "left": [],
        }
    )
    dora_indicators: list[str] = field(default_factory=list)
    round_wind: Optional[str] = None
    seat_wind: Optional[str] = None
    turn_info: Optional[str] = None
    confidence: float = 0.0
    raw_debug_info: dict[str, Any] = field(default_factory=dict)
    visible_tiles: list[str] = field(default_factory=list)
    history: list[list[str]] = field(default_factory=list)
    step: int = 0

    @property
    def hand(self):
        return self.current_hand

    @hand.setter
    def hand(self, value):
        self.current_hand = list(value or [])

    def update(
        self,
        new_hand,
        visible_tiles=None,
        confidence=None,
        drawn_tile=None,
        raw_debug_info=None,
        **fields,
    ):
        self.history.append(self.current_hand.copy())
        self.current_hand = list(new_hand or [])
        if visible_tiles is not None:
            self.visible_tiles = list(visible_tiles)
        if confidence is not None:
            self.confidence = max(0.0, min(1.0, float(confidence)))
        self.drawn_tile = drawn_tile
        if raw_debug_info is not None:
            self.raw_debug_info = dict(raw_debug_info)
        for name, value in fields.items():
            if hasattr(self, name):
                setattr(self, name, value)
        self.step += 1

    def get_hand(self):
        return self.current_hand.copy()

    def get_visible_tiles(self):
        return self.visible_tiles.copy()

    def to_dict(self):
        return asdict(self)

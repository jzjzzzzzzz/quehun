import random
from dataclasses import dataclass, field

from ai.agari import is_win, winning_tiles
from ai.engine import decide
from ai.shanten import simple_shanten
from ai.tile_set import PLAYABLE_TILES


@dataclass
class JapaneseMahjongGame:
    seed: int | None = None
    wall: list[str] = field(default_factory=list)
    hand: list[str] = field(default_factory=list)
    discards: list[str] = field(default_factory=list)
    turns: int = 0
    won: bool = False
    winning_tile: str | None = None

    def __post_init__(self):
        self.random = random.Random(self.seed)
        self.reset()

    def reset(self):
        self.wall = [tile for tile in PLAYABLE_TILES for _ in range(4)]
        self.random.shuffle(self.wall)
        self.hand = sorted(self.wall[:13])
        self.wall = self.wall[13:]
        self.discards = []
        self.turns = 0
        self.won = False
        self.winning_tile = None

    def visible_tiles(self):
        return self.hand + self.discards

    def draw(self):
        if not self.wall:
            return None

        tile = self.wall.pop(0)
        self.hand.append(tile)
        self.hand.sort()
        self.turns += 1
        return tile

    def discard(self, tile):
        self.hand.remove(tile)
        self.discards.append(tile)
        self.hand.sort()

    def step(self):
        drawn = self.draw()
        if drawn is None:
            return self.snapshot(event="draw_game")

        if is_win(self.hand):
            self.won = True
            self.winning_tile = drawn
            return self.snapshot(event="tsumo")

        decision = decide(self.hand, visible_tiles=self.visible_tiles())
        discard = decision["discard"]
        if discard is not None:
            self.discard(discard)

        result = self.snapshot(event="discard")
        result["decision"] = decision
        return result

    def play(self, max_turns=70):
        history = []

        while not self.won and self.wall and self.turns < max_turns:
            history.append(self.step())

        if not history:
            history.append(self.snapshot(event="draw_game"))

        return history

    def snapshot(self, event):
        waits = winning_tiles(self.hand, visible_tiles=self.visible_tiles())
        return {
            "event": event,
            "turn": self.turns,
            "hand": self.hand.copy(),
            "discards": self.discards.copy(),
            "wall_remaining": len(self.wall),
            "shanten": simple_shanten(self.hand),
            "waits": waits,
            "won": self.won,
            "winning_tile": self.winning_tile,
        }

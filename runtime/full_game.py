import random
from dataclasses import dataclass, field

from ai.agari import is_win
from ai.engine import decide
from ai.japanese_rules import estimate_points, yaku_for_win
from ai.shanten import simple_shanten
from ai.tile_set import PLAYABLE_TILES


SEAT_WINDS = ("east", "south", "west", "north")


@dataclass
class PlayerState:
    name: str
    seat_wind: str
    score: int = 25000
    hand: list[str] = field(default_factory=list)
    discards: list[str] = field(default_factory=list)
    riichi: bool = False

    def visible_tiles(self, table_discards):
        return self.hand + table_discards


class FullJapaneseGame:
    def __init__(self, seed=None, rounds=4, start_score=25000):
        self.seed = seed
        self.random = random.Random(seed)
        self.rounds = rounds
        self.start_score = start_score
        self.players = [
            PlayerState(f"Player {idx + 1}", SEAT_WINDS[idx], start_score)
            for idx in range(4)
        ]
        self.round_wind = "east"
        self.dealer = 0
        self.round_index = 0
        self.log = []

    def build_wall(self):
        wall = [tile for tile in PLAYABLE_TILES for _ in range(4)]
        self.random.shuffle(wall)
        return wall

    def reset_round(self):
        self.wall = self.build_wall()
        self.dead_wall = self.wall[-14:]
        self.wall = self.wall[:-14]
        self.table_discards = []

        for idx, player in enumerate(self.players):
            player.seat_wind = SEAT_WINDS[(idx - self.dealer) % 4]
            player.hand = []
            player.discards = []
            player.riichi = False

        for _ in range(13):
            for player in self.players:
                player.hand.append(self.wall.pop(0))

        for player in self.players:
            player.hand.sort()

        self.players[self.dealer].hand.append(self.wall.pop(0))
        self.players[self.dealer].hand.sort()

    def declare_riichi_if_ready(self, player):
        if not player.riichi and simple_shanten(player.hand) == 0:
            player.riichi = True
            return True
        return False

    def apply_ron_score(self, winner_idx, loser_idx, yaku):
        winner = self.players[winner_idx]
        loser = self.players[loser_idx]
        points = estimate_points(yaku, dealer=winner_idx == self.dealer, win_method="ron")
        winner.score += points
        loser.score -= points
        return points

    def apply_tsumo_score(self, winner_idx, yaku):
        winner = self.players[winner_idx]
        base = estimate_points(yaku, dealer=winner_idx == self.dealer, win_method="tsumo")
        payments = []

        for idx, player in enumerate(self.players):
            if idx == winner_idx:
                continue
            payment = max(500, base // 3)
            player.score -= payment
            winner.score += payment
            payments.append((idx, payment))

        return payments

    def check_ron(self, discard_tile, discarder_idx):
        winners = []

        for idx, player in enumerate(self.players):
            if idx == discarder_idx:
                continue

            test_hand = player.hand + [discard_tile]
            if not is_win(test_hand):
                continue

            yaku = yaku_for_win(
                test_hand,
                win_method="ron",
                seat_wind=player.seat_wind,
                round_wind=self.round_wind,
                riichi=player.riichi,
            )
            if yaku:
                points = self.apply_ron_score(idx, discarder_idx, yaku)
                winners.append((idx, yaku, points))

        return winners

    def play_round(self):
        self.reset_round()
        current = self.dealer
        first_dealer_discard = True

        self.log.append(f"Round {self.round_index + 1}: dealer={self.players[self.dealer].name}")

        while self.wall:
            player = self.players[current]

            if first_dealer_discard and current == self.dealer:
                first_dealer_discard = False
            else:
                drawn = self.wall.pop(0)
                player.hand.append(drawn)
                player.hand.sort()

                if is_win(player.hand):
                    yaku = yaku_for_win(
                        player.hand,
                        win_method="tsumo",
                        seat_wind=player.seat_wind,
                        round_wind=self.round_wind,
                        riichi=player.riichi,
                    )
                    if yaku:
                        payments = self.apply_tsumo_score(current, yaku)
                        self.log.append(
                            f"{player.name} wins by tsumo on {drawn}; yaku={','.join(yaku)}; payments={payments}"
                        )
                        return {"winner": current, "method": "tsumo", "yaku": yaku}

            decision = decide(player.hand, visible_tiles=player.visible_tiles(self.table_discards))
            discard = decision["discard"]
            player.hand.remove(discard)
            player.discards.append(discard)
            self.table_discards.append(discard)

            if self.declare_riichi_if_ready(player):
                self.log.append(f"{player.name} declares riichi")

            self.log.append(
                f"{player.name} discards {discard}; shanten={decision['shanten']}; ukeire={decision['ukeire']}"
            )

            ron_winners = self.check_ron(discard, current)
            if ron_winners:
                parts = [
                    f"{self.players[idx].name} yaku={','.join(yaku)} points={points}"
                    for idx, yaku, points in ron_winners
                ]
                self.log.append(f"Ron on {discard}: " + "; ".join(parts))
                return {"winner": ron_winners[0][0], "method": "ron", "winners": ron_winners}

            current = (current + 1) % 4

        self.log.append("Exhaustive draw")
        return {"winner": None, "method": "draw"}

    def rotate_dealer(self, dealer_won):
        if not dealer_won:
            self.dealer = (self.dealer + 1) % 4

    def play_game(self):
        results = []

        for round_index in range(self.rounds):
            self.round_index = round_index
            result = self.play_round()
            results.append(result)
            self.rotate_dealer(result.get("winner") == self.dealer)

        return {
            "rounds": results,
            "scores": {player.name: player.score for player in self.players},
            "log": self.log,
        }

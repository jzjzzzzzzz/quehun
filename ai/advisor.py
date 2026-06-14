from collections import Counter
from dataclasses import asdict, dataclass, field

from ai.japanese_rules import DRAGONS, HONORS, TERMINALS, suit_name
from ai.shanten import simple_shanten
from ai.tile_set import canonical_hand, canonical_tile
from ai.ukeire import effective_tiles


@dataclass
class DiscardAdvice:
    discard: str
    score: float
    shanten: int
    ukeire: int
    effective_tiles: dict[str, int] = field(default_factory=dict)
    danger: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class AdviceResult:
    recommended_discard: str | None
    top_choices: list[DiscardAdvice] = field(default_factory=list)
    yaku_tendencies: list[str] = field(default_factory=list)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "recommended_discard": self.recommended_discard,
            "top_choices": [choice.to_dict() for choice in self.top_choices],
            "yaku_tendencies": self.yaku_tendencies.copy(),
            "confidence": self.confidence,
            "warnings": self.warnings.copy(),
        }


def tile_danger(tile, discards=None, visible_tiles=None):
    tile = canonical_tile(tile)
    if tile is None:
        return 1.0
    discards = discards or {}
    all_discards = canonical_hand(
        tile_name
        for player_discards in discards.values()
        for tile_name in player_discards
    )
    visible = canonical_hand(visible_tiles)
    if tile in all_discards:
        return 0.05
    count = visible.count(tile) + all_discards.count(tile)
    danger = 0.55 - min(0.35, count * 0.10)
    if tile in HONORS:
        danger -= 0.08
    if tile in TERMINALS:
        danger -= 0.04
    return round(max(0.05, min(0.95, danger)), 3)


def yaku_tendencies(hand, seat_wind=None, round_wind=None):
    hand = canonical_hand(hand)
    counts = Counter(hand)
    tendencies = []
    simples = [tile for tile in hand if tile not in TERMINALS and tile not in HONORS]
    if len(simples) >= 10:
        tendencies.append("断幺九倾向：中张牌比例较高")
    pairs = sum(1 for count in counts.values() if count >= 2)
    if pairs >= 4:
        tendencies.append("七对子倾向：对子数量较多")
    triplet_shapes = sum(1 for count in counts.values() if count >= 2)
    if triplet_shapes >= 4:
        tendencies.append("对对和倾向：对子/刻子形较多")
    suits = Counter(suit_name(tile) for tile in hand if tile not in HONORS)
    if suits:
        main_suit, main_count = suits.most_common(1)[0]
        if main_count >= 9:
            tendencies.append(f"混一色倾向：{main_suit} 集中度较高")
    for dragon in DRAGONS:
        if counts[dragon] >= 2:
            tendencies.append(f"役牌倾向：保留 {dragon}")
    for wind in {seat_wind, round_wind}:
        wind_tile = canonical_tile(wind)
        if wind_tile and counts[wind_tile] >= 2:
            tendencies.append(f"役牌倾向：保留 {wind_tile}")
    return tendencies or ["当前以牌效率为主，未发现明显役种倾向"]


def analyze_hand(
    hand,
    visible_tiles=None,
    discards=None,
    recognition_confidence=1.0,
    seat_wind=None,
    round_wind=None,
    top_n=3,
):
    hand = canonical_hand(hand)
    visible = canonical_hand(visible_tiles) if visible_tiles is not None else hand
    confidence = max(0.0, min(1.0, float(recognition_confidence)))
    warnings = []
    if confidence < 0.65:
        warnings.append("识别置信度较低，建议可能不可靠")
    if len(hand) not in (13, 14):
        warnings.append(f"识别到 {len(hand)} 张牌，牌数异常")
    if len(hand) < 2:
        return AdviceResult(None, confidence=confidence, warnings=warnings)

    choices = []
    unique_discards = list(dict.fromkeys(hand))
    for discard in unique_discards:
        after = hand.copy()
        after.remove(discard)
        shanten = simple_shanten(after)
        effective = effective_tiles(after, visible_tiles=visible)
        ukeire = sum(effective.values())
        danger = tile_danger(discard, discards=discards, visible_tiles=visible)
        shape_value = _shape_value(discard, after)
        score = -shanten * 1000 + ukeire * 12 + shape_value - danger * 20
        choices.append(DiscardAdvice(
            discard=discard,
            score=round(score, 2),
            shanten=shanten,
            ukeire=ukeire,
            effective_tiles=effective,
            danger=danger,
        ))

    choices.sort(key=lambda item: (item.shanten, -item.ukeire, -item.score, item.discard))
    best_shanten = choices[0].shanten
    best_ukeire = max(item.ukeire for item in choices if item.shanten == best_shanten)
    for choice in choices:
        choice.reasons = _reasons(choice, hand, best_shanten, best_ukeire)

    top_choices = choices[:max(1, int(top_n))]
    return AdviceResult(
        recommended_discard=top_choices[0].discard if top_choices else None,
        top_choices=top_choices,
        yaku_tendencies=yaku_tendencies(
            hand,
            seat_wind=seat_wind,
            round_wind=round_wind,
        ),
        confidence=confidence,
        warnings=warnings,
    )


def _shape_value(discard, after):
    if discard in HONORS:
        count = after.count(discard)
        return 35 if count == 0 else -35
    suit, rank_text = discard.rsplit("-", 1)
    rank = int(rank_text)
    neighbors = {
        f"{suit}-{candidate}"
        for candidate in (rank - 2, rank - 1, rank + 1, rank + 2)
        if 1 <= candidate <= 9
    }
    connected = sum(after.count(tile) for tile in neighbors)
    terminal_bonus = 18 if rank in (1, 9) and connected == 0 else 0
    isolated_bonus = 28 if connected == 0 and after.count(discard) == 0 else 0
    return terminal_bonus + isolated_bonus - connected * 12


def _reasons(choice, original_hand, best_shanten, best_ukeire):
    reasons = []
    if choice.shanten == best_shanten:
        reasons.append(f"打出后保持最低向听数 {choice.shanten}")
    else:
        reasons.append(f"打出后为 {choice.shanten} 向听")
    if choice.ukeire == best_ukeire:
        reasons.append(f"有效进张最多，共 {choice.ukeire} 枚")
    else:
        reasons.append(f"有效进张约 {choice.ukeire} 枚")
    tile = choice.discard
    if tile in HONORS and original_hand.count(tile) == 1:
        reasons.append("孤张字牌连接能力较低")
    elif tile not in HONORS:
        suit, rank_text = tile.rsplit("-", 1)
        rank = int(rank_text)
        connected = any(
            f"{suit}-{candidate}" in original_hand
            for candidate in (rank - 2, rank - 1, rank + 1, rank + 2)
            if 1 <= candidate <= 9
        )
        if not connected:
            reasons.append("孤立牌价值较低")
        elif rank in (1, 9):
            reasons.append("边张延展性较低")
        else:
            reasons.append("兼顾现有搭子结构")
    reasons.append(f"基础危险度 {choice.danger:.0%}")
    return reasons

SUITS = ("characters", "dots", "bamboo")
HONORS = ("east", "south", "west", "north", "red", "green", "white")
BONUS = ("spring", "summer", "autumn", "winter")

SUITED_TILES = tuple(f"{suit}-{value}" for suit in SUITS for value in range(1, 10))
HONOR_TILES = tuple(f"honors-{name}" for name in HONORS)
BONUS_TILES = tuple(f"bonus-{name}" for name in BONUS)

PLAYABLE_TILES = SUITED_TILES + HONOR_TILES
TILE_SET = PLAYABLE_TILES + BONUS_TILES

ALIASES = {
    "east": "honors-east",
    "south": "honors-south",
    "west": "honors-west",
    "north": "honors-north",
    "red": "honors-red",
    "green": "honors-green",
    "white": "honors-white",
}

for value in range(1, 10):
    ALIASES[f"m{value}"] = f"characters-{value}"
    ALIASES[f"p{value}"] = f"dots-{value}"
    ALIASES[f"s{value}"] = f"bamboo-{value}"
    ALIASES[f"wan{value}"] = f"characters-{value}"
    ALIASES[f"dot{value}"] = f"dots-{value}"
    ALIASES[f"bam{value}"] = f"bamboo-{value}"


def canonical_tile(tile):
    if tile is None:
        return None

    value = str(tile).strip().lower().replace("_", "-")
    if not value:
        return None

    value = ALIASES.get(value, value)
    if value in TILE_SET:
        return value

    if value in HONORS:
        return f"honors-{value}"

    return None


def canonical_hand(hand, include_bonus=False):
    allowed = TILE_SET if include_bonus else PLAYABLE_TILES
    result = []

    for tile in hand or []:
        canonical = canonical_tile(tile)
        if canonical in allowed:
            result.append(canonical)

    return result


def tile_index(tile):
    canonical = canonical_tile(tile)
    if canonical not in PLAYABLE_TILES:
        return None
    return PLAYABLE_TILES.index(canonical)


def index_tile(index):
    if 0 <= index < len(PLAYABLE_TILES):
        return PLAYABLE_TILES[index]
    return None

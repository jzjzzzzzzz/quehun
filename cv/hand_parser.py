from ai.tile_set import canonical_hand


DEFAULT_HAND = [
    "characters-1",
    "characters-2",
    "characters-3",
    "dots-5",
    "dots-6",
    "dots-7",
    "bamboo-2",
    "bamboo-3",
    "bamboo-4",
    "honors-east",
    "honors-east",
    "honors-red",
    "honors-green",
    "honors-white",
]


class HandParser:
    def __init__(self, fallback_hand=None):
        self.fallback_hand = canonical_hand(fallback_hand or DEFAULT_HAND)

    def parse(self, frame=None):
        """
        Return a canonical hand list.

        The project does not currently have a Torch runtime installed, so this
        parser intentionally uses a deterministic fallback until a real tile
        classifier is wired in.
        """
        return self.fallback_hand.copy()

from ai.tile_set import TILE_SET, canonical_hand, canonical_tile


class TileEncoder:
    def __init__(self):
        self.tiles = list(TILE_SET)
        self.encode_map = {tile: idx for idx, tile in enumerate(self.tiles)}
        self.decode_map = {idx: tile for idx, tile in enumerate(self.tiles)}

    def encode(self, tile_list):
        return [
            self.encode_map[tile]
            for tile in canonical_hand(tile_list, include_bonus=True)
            if tile in self.encode_map
        ]

    def decode(self, idx_list):
        return [self.decode_map[idx] for idx in idx_list if idx in self.decode_map]

    def encode_one(self, tile):
        canonical = canonical_tile(tile)
        return self.encode_map.get(canonical, -1)

    def decode_one(self, idx):
        return self.decode_map.get(idx)

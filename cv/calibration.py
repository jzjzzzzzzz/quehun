import glob
import os
import shutil

from ai.tile_set import canonical_tile


DEFAULT_DEBUG_DIR = "debug/tiles/latest"
DEFAULT_OUTPUT_DIR = "templates/tiles"


def parse_labels(value):
    labels = [part.strip() for part in value.split(",") if part.strip()]
    canonical = []

    for label in labels:
        if label.lower() in {"skip", "none", "-"}:
            canonical.append(None)
            continue
        tile = canonical_tile(label)
        if tile is None:
            raise ValueError(f"Unknown tile label: {label!r}")
        canonical.append(tile)

    return canonical


def learn_debug_tiles(labels, debug_dir=DEFAULT_DEBUG_DIR, output_dir=DEFAULT_OUTPUT_DIR):
    tile_paths = sorted(glob.glob(os.path.join(debug_dir, "tile-*.png")))
    if not tile_paths:
        raise RuntimeError(f"No debug tile crops found in {debug_dir!r}.")

    if len(labels) != len(tile_paths):
        raise ValueError(
            f"Label count ({len(labels)}) must match tile crop count ({len(tile_paths)})."
        )

    written = []
    for index, (source, label) in enumerate(zip(tile_paths, labels)):
        if label is None:
            continue

        tile = canonical_tile(label)
        if tile is None:
            raise ValueError(f"Unknown tile label at index {index}: {label!r}")

        tile_dir = os.path.join(output_dir, tile)
        os.makedirs(tile_dir, exist_ok=True)
        existing = len(glob.glob(os.path.join(tile_dir, "*.png")))
        destination = os.path.join(tile_dir, f"{existing + 1:04d}.png")
        shutil.copy2(source, destination)
        written.append(destination)

    return written

import os
import sys
import tempfile

import cv2

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cv.action_buttons import ActionButtonDetector
from cv.game_regions import (
    ContourTileParser,
    PerspectiveTileClassifier,
    load_regions,
    scaled_region,
    update_region,
)


def test_scaled_region():
    region = {"left": 100, "top": 200, "width": 300, "height": 400}
    scaled = scaled_region(
        region,
        (540, 960, 3),
        {"width": 1920, "height": 1080},
    )
    assert scaled == {"left": 50, "top": 100, "width": 150, "height": 200}


def test_update_region_preserves_grid_metadata():
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "regions.json")
        source = load_regions()
        import json
        with open(path, "w", encoding="utf-8") as file:
            json.dump(source, file)
        updated = update_region(
            "discards_self",
            {"left": 50, "top": 60, "width": 70, "height": 80},
            (960, 540),
            path,
        )
        assert updated["left"] == 100
        assert updated["rows"] == 2


def test_real_action_templates():
    image_path = os.path.join(ROOT, ".tmp", "after-discard-final-live.png")
    if not os.path.exists(image_path):
        return
    frame = cv2.imread(image_path)
    actions = ActionButtonDetector().detect(
        frame,
        {"left": 820, "top": 700, "width": 650, "height": 180},
    )
    names = {item["action"] for item in actions}
    assert {"pon", "pass"} <= names


def test_perspective_template_learning():
    image_path = os.path.join(ROOT, ".tmp", "region-debug", "discards_self-0-0.png")
    if not os.path.exists(image_path):
        return
    image = cv2.imread(image_path)
    with tempfile.TemporaryDirectory() as directory:
        classifier = PerspectiveTileClassifier(templates_dir=directory)
        path = classifier.learn("m7", image)
        result = classifier.classify(image)
        assert path is not None
        assert result["tile"] == "characters-7"
        assert result["confidence"] == 1.0


if __name__ == "__main__":
    test_scaled_region()
    test_update_region_preserves_grid_metadata()
    test_real_action_templates()
    test_perspective_template_learning()
    print("Game region tests passed")

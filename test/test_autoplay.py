import os
import sys
import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cv.calibration import learn_debug_tiles, parse_labels
from cv.template_classifier import TemplateTileClassifier
from runtime.autoplay import AutoPlayController
from runtime.config import save_config


class FakeParser:
    def __init__(self, details):
        self.hand_region = {}
        self.tile_count = 14
        self.details = details

    def parse_with_details(self, _frame):
        return [item["tile"] for item in self.details if item["tile"]], self.details


class FakeClicker:
    def __init__(self):
        self.clicks = []

    def click(self, x, y):
        self.clicks.append((x, y))


def test_template_classifier_loads():
    classifier = TemplateTileClassifier()
    image = cv2.imread(os.path.join(ROOT, "dataset", "tiles-resized", "2.jpg"))
    result = classifier.classify(image)

    assert result["tile"] is not None
    assert result["confidence"] >= 0.0


def test_click_mapping():
    config = {
        "window_title": "",
        "region_mode": "absolute",
        "hand_region": {"left": 100, "top": 200, "width": 700, "height": 100},
        "tile_count": 14,
        "stable_frames": 1,
        "click_cooldown": 0.0,
        "click": {"enabled": False, "y_offset_ratio": 0.5},
        "min_confidence": 0.25,
        "delay": 0.1,
    }

    tmp_dir = os.path.join(ROOT, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, "autoplay-test.json")
    save_config(config, path)
    controller = AutoPlayController(config_path=path, dry_run=True)
    assert controller._tile_center(0) == (125, 250)
    assert controller._tile_center(13) == (775, 250)


def test_waits_on_13_tile_hand_with_empty_slot():
    config = {
        "window_title": "",
        "region_mode": "absolute",
        "focus_window": False,
        "hand_region": {"left": 0, "top": 0, "width": 140, "height": 20},
        "tile_slots": 14,
        "tile_count": 14,
        "actionable_tile_counts": [14],
        "waiting_tile_counts": [13],
        "stable_frames": 1,
        "click_cooldown": 0.0,
        "click": {"enabled": False, "y_offset_ratio": 0.5},
        "min_confidence": 0.25,
        "delay": 0.1,
    }

    tmp_dir = os.path.join(ROOT, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, "autoplay-wait-test.json")
    save_config(config, path)

    details = [
        {"index": idx, "tile": "characters-1", "confidence": 0.9, "error": 0.01}
        for idx in range(13)
    ]
    details.append({"index": 13, "tile": "characters-9", "confidence": 0.01, "error": 0.5})

    controller = AutoPlayController(config_path=path, dry_run=True)
    controller.parser = FakeParser(details)

    result = controller.step(frame=np.zeros((20, 140, 3), dtype=np.uint8))
    assert result["action"] == "wait"
    assert result["reason"] == "recognized 13 tiles; waiting for draw"
    assert result["low_confidence_count"] == 1


def test_out_of_bounds_hand_region_skips_without_crashing():
    config = {
        "window_title": "",
        "region_mode": "absolute",
        "focus_window": False,
        "hand_region": {"left": 1000, "top": 1000, "width": 140, "height": 20},
        "tile_count": 14,
        "action_prompt": {"enabled": False},
        "click": {"enabled": False},
    }

    tmp_dir = os.path.join(ROOT, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, "autoplay-out-of-bounds-test.json")
    save_config(config, path)

    controller = AutoPlayController(config_path=path, dry_run=True)
    result = controller.step(frame=np.zeros((100, 100, 3), dtype=np.uint8))

    assert result["action"] == "skip"
    assert result["reason"] == "no tiles recognized"
    assert result["details"] == []


def test_learns_debug_tiles():
    tmp_dir = os.path.join(ROOT, ".tmp", "learn-test")
    debug_dir = os.path.join(tmp_dir, "debug")
    output_dir = os.path.join(tmp_dir, "calibrated")
    os.makedirs(debug_dir, exist_ok=True)

    for filename in os.listdir(debug_dir):
        os.remove(os.path.join(debug_dir, filename))

    cv2.imwrite(os.path.join(debug_dir, "tile-00-unknown.png"), np.zeros((16, 16, 3), dtype=np.uint8))
    cv2.imwrite(os.path.join(debug_dir, "tile-01-unknown.png"), np.ones((16, 16, 3), dtype=np.uint8) * 255)

    labels = parse_labels("m1,p9")
    written = learn_debug_tiles(labels, debug_dir=debug_dir, output_dir=output_dir)

    assert len(written) == 2
    assert os.path.exists(os.path.join(output_dir, "characters-1", "0001.png"))
    assert os.path.exists(os.path.join(output_dir, "dots-9", "0001.png"))


def test_classifier_prefers_calibrated_tiles():
    tmp_dir = os.path.join(ROOT, ".tmp", "classifier-calibrated")
    tile_dir = os.path.join(tmp_dir, "characters-1")
    os.makedirs(tile_dir, exist_ok=True)
    path = os.path.join(tile_dir, "0001.png")
    sample = np.ones((32, 32, 3), dtype=np.uint8) * 255
    cv2.imwrite(path, sample)

    classifier = TemplateTileClassifier(calibrated_dir=tmp_dir)
    result = classifier.classify(sample)

    assert result["tile"] == "characters-1"
    assert result["confidence"] == 1.0


def test_configured_click_enable_controls_dry_run():
    from runtime.loop import run_autoplay

    class Args:
        config = None
        enable_click = False
        auto_play_debug_dir = None
        iterations = 0
        auto_play_image = None
        startup_delay = 0.0

    tmp_dir = os.path.join(ROOT, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, "autoplay-click-enabled-test.json")
    save_config({
        "window_title": "",
        "region_mode": "absolute",
        "hand_region": {"left": 0, "top": 0, "width": 140, "height": 20},
        "tile_count": 14,
        "click": {"enabled": True},
    }, path)

    args = Args()
    args.config = path

    original_run = AutoPlayController.run
    seen = {}

    def fake_run(self, iterations=None, image_path=None, startup_delay=0.0):
        seen["dry_run"] = self.dry_run

    AutoPlayController.run = fake_run
    try:
        run_autoplay(args)
    finally:
        AutoPlayController.run = original_run

    assert seen["dry_run"] is False


def test_discard_click_can_confirm_region():
    config = {
        "window_title": "",
        "region_mode": "absolute",
        "focus_window": False,
        "hand_region": {"left": 0, "top": 0, "width": 140, "height": 20},
        "tile_slots": 14,
        "tile_count": 14,
        "actionable_tile_counts": [14],
        "stable_frames": 1,
        "click_cooldown": 0.0,
        "click": {"enabled": True, "y_offset_ratio": 0.5, "repeat": 1},
        "discard_confirm": {
            "enabled": True,
            "delay": 0.0,
            "region": {"left": 200, "top": 300, "width": 80, "height": 40},
        },
        "min_confidence": 0.25,
        "delay": 0.1,
    }

    tmp_dir = os.path.join(ROOT, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, "autoplay-confirm-test.json")
    save_config(config, path)

    details = [
        {"index": idx, "tile": tile, "confidence": 0.9, "error": 0.01}
        for idx, tile in enumerate([
            "characters-1", "characters-2", "characters-3",
            "dots-5", "dots-6", "dots-7",
            "bamboo-2", "bamboo-3", "bamboo-4",
            "honors-east", "honors-east", "honors-red",
            "honors-green", "honors-white",
        ])
    ]

    clicker = FakeClicker()
    controller = AutoPlayController(config_path=path, dry_run=False, clicker=clicker)
    controller.parser = FakeParser(details)

    result = controller.step(frame=np.zeros((20, 140, 3), dtype=np.uint8))

    assert result["action"] == "click"
    assert clicker.clicks[0] == (125, 10)
    assert clicker.clicks[1] == (240, 320)
    assert result["confirm_click"] == {"x": 240, "y": 320}


def test_waiting_hand_can_auto_pass():
    config = {
        "window_title": "",
        "region_mode": "absolute",
        "focus_window": False,
        "hand_region": {"left": 0, "top": 0, "width": 140, "height": 20},
        "tile_slots": 14,
        "tile_count": 14,
        "actionable_tile_counts": [14],
        "waiting_tile_counts": [13],
        "stable_frames": 1,
        "click_cooldown": 0.0,
        "click": {"enabled": True, "y_offset_ratio": 0.5, "repeat": 1},
        "auto_pass": True,
        "action_regions": {
            "pass": {"left": 300, "top": 400, "width": 100, "height": 50},
        },
        "min_confidence": 0.25,
        "delay": 0.1,
    }

    tmp_dir = os.path.join(ROOT, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, "autoplay-pass-test.json")
    save_config(config, path)

    details = [
        {"index": idx, "tile": "characters-1", "confidence": 0.9, "error": 0.01}
        for idx in range(13)
    ]
    details.append({"index": 13, "tile": "characters-9", "confidence": 0.01, "error": 0.5})

    clicker = FakeClicker()
    controller = AutoPlayController(config_path=path, dry_run=False, clicker=clicker)
    controller.parser = FakeParser(details)

    result = controller.step(frame=np.zeros((20, 140, 3), dtype=np.uint8))

    assert result["action"] == "pass_click"
    assert clicker.clicks == [(350, 425)]


def test_visible_prompt_clicks_default_pass_before_hand_parse():
    config = {
        "window_title": "",
        "region_mode": "absolute",
        "focus_window": False,
        "hand_region": {"left": 0, "top": 0, "width": 140, "height": 20},
        "tile_slots": 14,
        "tile_count": 14,
        "stable_frames": 1,
        "click_cooldown": 0.0,
        "click": {"enabled": True, "repeat": 1},
        "action_prompt": {
            "enabled": True,
            "detect_regions": ["chi", "pass"],
            "edge_threshold": 0.01,
            "stable_frames": 1,
            "default_action": "pass",
        },
        "action_regions": {
            "chi": {"left": 10, "top": 10, "width": 40, "height": 30},
            "pass": {"left": 80, "top": 10, "width": 40, "height": 30},
        },
        "min_confidence": 0.25,
        "delay": 0.1,
    }

    tmp_dir = os.path.join(ROOT, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, "autoplay-visible-prompt-test.json")
    save_config(config, path)

    frame = np.zeros((60, 140, 3), dtype=np.uint8)
    cv2.putText(frame, "X", (16, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    clicker = FakeClicker()
    controller = AutoPlayController(config_path=path, dry_run=False, clicker=clicker)

    result = controller.step(frame=frame)

    assert result["action"] == "pass_click"
    assert clicker.clicks == [(100, 25)]


if __name__ == "__main__":
    test_template_classifier_loads()
    test_click_mapping()
    test_waits_on_13_tile_hand_with_empty_slot()
    test_out_of_bounds_hand_region_skips_without_crashing()
    test_learns_debug_tiles()
    test_classifier_prefers_calibrated_tiles()
    test_configured_click_enable_controls_dry_run()
    test_discard_click_can_confirm_region()
    test_waiting_hand_can_auto_pass()
    test_visible_prompt_clicks_default_pass_before_hand_parse()
    print("Autoplay tests passed")

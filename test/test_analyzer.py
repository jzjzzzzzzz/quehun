import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cv.screen_state import ScreenState, ScreenStateResult
from runtime.analyzer import AnalysisController
from runtime.config import save_config


HAND = [
    "characters-1", "characters-2", "characters-3",
    "dots-5", "dots-6", "dots-7",
    "bamboo-7", "bamboo-8", "bamboo-9",
    "honors-east", "honors-east", "honors-red",
    "honors-green", "honors-white",
]


class FakeParser:
    hand_region = {}
    tile_count = 14

    def parse_with_details(self, _frame):
        details = [
            {
                "index": index,
                "tile": tile,
                "confidence": 0.95,
                "error": 0.01,
                "occupancy": 1.0,
            }
            for index, tile in enumerate(HAND)
        ]
        return HAND.copy(), details


class FakeDetector:
    def detect(self, _frame, hand_region=None):
        return ScreenStateResult(ScreenState.IN_GAME, 0.9, text="East")


class FakeClicker:
    def __init__(self):
        self.clicks = []

    def click(self, x, y):
        self.clicks.append((x, y))


def make_controller(auto_click):
    directory = tempfile.TemporaryDirectory()
    path = os.path.join(directory.name, "config.json")
    save_config({
        "window_title": "test",
        "region_mode": "window",
        "hand_region": {"left": 0, "top": 0, "width": 140, "height": 40},
        "tile_slots": 14,
        "tile_count": 14,
        "stable_frames": 1,
        "click_cooldown": 0.0,
        "min_confidence": 0.25,
        "click": {
            "min_confidence": 0.8,
            "require_in_game": True,
            "require_foreground": False,
            "y_offset_ratio": 0.5,
        },
    }, path)
    clicker = FakeClicker()
    controller = AnalysisController(
        config_path=path,
        auto_click=auto_click,
        clicker=clicker,
        state_detector=FakeDetector(),
    )
    controller.parser = FakeParser()
    controller._test_directory = directory
    return controller, clicker


def test_read_only_never_clicks():
    controller, clicker = make_controller(False)
    result = controller.step(
        frame=np.zeros((80, 160, 3), dtype=np.uint8),
        window={"hwnd": 1, "left": 100, "top": 200, "width": 160, "height": 80},
    )
    assert result["discard"] is not None
    assert not clicker.clicks


def test_safe_auto_click():
    controller, clicker = make_controller(True)
    result = controller.step(
        frame=np.zeros((80, 160, 3), dtype=np.uint8),
        window={"hwnd": 1, "left": 100, "top": 200, "width": 160, "height": 80},
    )
    assert result["action"] == "clicked"
    assert len(clicker.clicks) == 1


if __name__ == "__main__":
    test_read_only_never_clicks()
    test_safe_auto_click()
    print("Analyzer tests passed")

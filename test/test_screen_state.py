import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cv.screen_state import OCRReader, QueHunScreenStateDetector, ScreenState


class FakeOCR:
    available = True

    def read(self, _frame):
        return "Create Room Room Settings Friend"


def test_room_state_from_ocr():
    detector = QueHunScreenStateDetector(ocr=FakeOCR())
    result = detector.detect(np.ones((200, 300, 3), dtype=np.uint8) * 120)
    assert result.state == ScreenState.ROOM_CREATION
    assert result.confidence >= 0.5


def test_project_ocr_languages_available():
    reader = OCRReader()
    if not reader.available:
        pytest.skip("Tesseract OCR is not installed or not discoverable")
    assert reader.available
    assert "eng" in reader.languages


if __name__ == "__main__":
    test_room_state_from_ocr()
    test_project_ocr_languages_available()
    print("Screen state tests passed")

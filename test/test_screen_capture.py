import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from capture.screen import ScreenCapture


def test_debug_retention():
    with tempfile.TemporaryDirectory() as directory:
        capture = ScreenCapture(debug=True, debug_dir=directory, max_debug_files=3)
        frame = np.zeros((20, 20, 3), dtype=np.uint8)
        for index in range(6):
            capture.save_debug(frame, label=str(index))
        images = [name for name in os.listdir(directory) if name.endswith(".png")]
        assert len(images) == 3


if __name__ == "__main__":
    test_debug_retention()
    print("Screen capture tests passed")

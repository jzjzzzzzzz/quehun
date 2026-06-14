import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from runtime.pipeline import Pipeline


def fake_frame():
    return np.zeros((256, 256, 3), dtype=np.uint8)


def test_pipeline():
    pipeline = Pipeline()

    print("\nPIPELINE TEST START")

    result = None
    for i in range(3):
        result = pipeline.process(fake_frame())
        print(f"frame {i} -> {result}")

    assert result is not None
    assert result["discard"] is not None
    assert "hand" in result

    print("Pipeline test passed")


if __name__ == "__main__":
    test_pipeline()

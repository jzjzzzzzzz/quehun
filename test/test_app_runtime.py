import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from runtime.autoplay_runner import format_result


def test_result_formatting():
    text = format_result({
        "action": "dry_run",
        "discard": "characters-9",
        "tile_index": 3,
        "click": {"x": 10, "y": 20},
        "low_confidence_count": 0,
        "reason": None,
        "hand": ["characters-1", "characters-9"],
    })

    assert "dry_run" in text
    assert "discard=characters-9" in text
    assert "hand=[characters-1,characters-9]" in text


if __name__ == "__main__":
    test_result_formatting()
    print("App runtime tests passed")

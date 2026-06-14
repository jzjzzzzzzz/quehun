import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_ui_import():
    from ui.app import QueHunApp, display_tile

    assert QueHunApp is not None
    assert display_tile("characters-1") == "1m"


if __name__ == "__main__":
    test_ui_import()
    print("UI import tests passed")

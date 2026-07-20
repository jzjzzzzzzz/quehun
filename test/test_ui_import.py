def test_ui_import():
    from ui.app import QueHunApp, display_tile

    assert QueHunApp is not None
    assert display_tile("characters-1") == "1m"


if __name__ == "__main__":
    test_ui_import()
    print("UI import tests passed")

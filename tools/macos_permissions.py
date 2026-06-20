import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from capture.screen import capture_screen
from capture.windows_api import list_windows
from runtime.clicker import MacClicker


def check_windows():
    windows = list_windows()
    if not windows:
        return False, "No windows returned. Grant Accessibility permission."
    return True, f"Found {len(windows)} visible windows."


def check_screen():
    frame = capture_screen()
    if frame is None or frame.size == 0:
        return False, "No screen pixels returned."
    return True, f"Captured screen frame {frame.shape[1]}x{frame.shape[0]}."


def check_click(x=None, y=None):
    if x is None or y is None:
        return None, "Skipped click test. Pass --click x y to test Accessibility clicking."
    MacClicker().click(x, y)
    return True, f"Clicked at ({x}, {y})."


def main():
    parser = argparse.ArgumentParser(description="Check macOS permissions for QueHun.")
    parser.add_argument("--click", nargs=2, type=int, metavar=("X", "Y"))
    args = parser.parse_args()

    checks = [
        ("Accessibility window listing", check_windows),
        ("Screen Recording capture", check_screen),
    ]
    if args.click:
        checks.append(("Accessibility mouse click", lambda: check_click(*args.click)))
    else:
        checks.append(("Accessibility mouse click", check_click))

    failed = False
    for name, func in checks:
        try:
            ok, message = func()
        except Exception as exc:
            ok, message = False, str(exc)
        label = "SKIP" if ok is None else "OK" if ok else "FAIL"
        print(f"{label}: {name}: {message}")
        failed = failed or ok is False

    if failed:
        print()
        print("Open System Settings > Privacy & Security and grant permissions to")
        print("Terminal, Python, or the app/IDE you use to launch QueHun.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

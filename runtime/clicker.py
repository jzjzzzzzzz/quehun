import ctypes
import sys
import time


INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

_DPI_AWARE = False


def _require_windows():
    if not sys.platform.startswith("win") or not hasattr(ctypes, "windll"):
        raise RuntimeError("Mouse clicking requires Windows.")
    return ctypes.windll.user32


def enable_dpi_awareness():
    global _DPI_AWARE
    if _DPI_AWARE:
        return

    user32 = _require_windows()
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            try:
                user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass
    _DPI_AWARE = True


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class InputUnion(ctypes.Union):
    _fields_ = [("mi", MouseInput)]


class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", InputUnion),
    ]


class WindowsClicker:
    def __init__(self):
        enable_dpi_awareness()

    def _send_mouse_event(self, flags):
        user32 = _require_windows()
        extra = ctypes.c_ulong(0)
        event = Input(
            type=INPUT_MOUSE,
            union=InputUnion(
                mi=MouseInput(
                    dx=0,
                    dy=0,
                    mouseData=0,
                    dwFlags=flags,
                    time=0,
                    dwExtraInfo=ctypes.pointer(extra),
                )
            ),
        )
        sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event))
        if sent != 1:
            raise ctypes.WinError()

    def click(self, x, y):
        user32 = _require_windows()
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.05)
        self._send_mouse_event(MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.05)
        self._send_mouse_event(MOUSEEVENTF_LEFTUP)

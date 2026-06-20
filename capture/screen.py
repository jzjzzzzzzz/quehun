import os
import subprocess
import time
from pathlib import Path
from tempfile import NamedTemporaryFile


def _is_macos():
    return os.sys.platform == "darwin"


def capture_screen(region=None):
    if _is_macos():
        return capture_screen_macos(region=region)

    try:
        import cv2
        import numpy as np
        from PIL import ImageGrab
    except ImportError as exc:
        raise RuntimeError("Screen capture requires pillow, numpy, and opencv-python.") from exc

    if region:
        left = region["left"]
        top = region["top"]
        width = region["width"]
        height = region["height"]
        bbox = (left, top, left + width, top + height)
    else:
        bbox = None

    try:
        img = np.array(ImageGrab.grab(bbox=bbox))
    except OSError as exc:
        try:
            return capture_screen_gdi(region=region)
        except Exception as gdi_exc:
            raise RuntimeError(
                "Screen grab failed. Run this from an interactive Windows desktop "
                "session with the game visible, or use --auto-play-image with a screenshot."
            ) from gdi_exc
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def capture_screen_macos(region=None):
    import cv2
    import numpy as np
    from PIL import Image

    with NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    command = ["screencapture", "-x"]
    if region:
        left = int(region["left"])
        top = int(region["top"])
        width = int(region["width"])
        height = int(region["height"])
        command.extend(["-R", f"{left},{top},{width},{height}"])
    command.append(path)
    try:
        completed = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        if completed.returncode != 0 or not os.path.exists(path):
            message = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(
                "macOS screen capture failed. Grant Screen Recording permission "
                "to Terminal, Python, or your IDE in System Settings > Privacy & Security. "
                f"Details: {message or 'no image was created'}"
            )
        image = np.array(Image.open(path).convert("RGB"))
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def capture_screen_gdi(region=None):
    import ctypes

    import cv2
    import numpy as np

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    if region:
        left = int(region["left"])
        top = int(region["top"])
        width = int(region["width"])
        height = int(region["height"])
    else:
        left = user32.GetSystemMetrics(76)
        top = user32.GetSystemMetrics(77)
        width = user32.GetSystemMetrics(78)
        height = user32.GetSystemMetrics(79)
        if width <= 0 or height <= 0:
            left = 0
            top = 0
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)

    hdesktop = user32.GetDesktopWindow()
    hdc = user32.GetWindowDC(hdesktop)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bitmap = gdi32.CreateCompatibleBitmap(hdc, width, height)
    old_obj = gdi32.SelectObject(memdc, bitmap)

    try:
        if not gdi32.BitBlt(memdc, 0, 0, width, height, hdc, left, top, 0x00CC0020):
            raise RuntimeError("Windows BitBlt screen capture failed.")

        buffer = ctypes.create_string_buffer(width * height * 4)

        class BitmapInfoHeader(ctypes.Structure):
            _fields_ = [
                ("biSize", ctypes.c_uint32),
                ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32),
            ]

        class BitmapInfo(ctypes.Structure):
            _fields_ = [("bmiHeader", BitmapInfoHeader), ("bmiColors", ctypes.c_uint32 * 3)]

        bmi = BitmapInfo()
        bmi.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        lines = gdi32.GetDIBits(memdc, bitmap, 0, height, buffer, ctypes.byref(bmi), 0)
        if lines != height:
            raise RuntimeError("Windows GetDIBits screen capture failed.")

        image = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    finally:
        gdi32.SelectObject(memdc, old_obj)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(hdesktop, hdc)


def capture_window(hwnd):
    """Capture a specific Windows HWND even when another window overlaps it."""
    if _is_macos():
        raise RuntimeError("macOS window capture needs a window region, not an HWND.")

    import ctypes
    from ctypes import wintypes

    import cv2
    import numpy as np

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    handle = wintypes.HWND(int(hwnd))
    if not user32.IsWindow(handle):
        raise RuntimeError(f"Invalid window handle: {hwnd}")

    rect = wintypes.RECT()
    if not user32.GetWindowRect(handle, ctypes.byref(rect)):
        raise ctypes.WinError()
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Window has invalid dimensions: {width}x{height}")

    window_dc = user32.GetWindowDC(handle)
    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    old_object = gdi32.SelectObject(memory_dc, bitmap)

    try:
        printed = user32.PrintWindow(handle, memory_dc, 0x00000002)
        if not printed:
            printed = gdi32.BitBlt(
                memory_dc,
                0,
                0,
                width,
                height,
                window_dc,
                0,
                0,
                0x00CC0020,
            )
        if not printed:
            raise RuntimeError("Windows PrintWindow/BitBlt capture failed.")

        class BitmapInfoHeader(ctypes.Structure):
            _fields_ = [
                ("biSize", ctypes.c_uint32),
                ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32),
            ]

        class BitmapInfo(ctypes.Structure):
            _fields_ = [
                ("bmiHeader", BitmapInfoHeader),
                ("bmiColors", ctypes.c_uint32 * 3),
            ]

        bitmap_info = BitmapInfo()
        bitmap_info.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
        bitmap_info.bmiHeader.biWidth = width
        bitmap_info.bmiHeader.biHeight = -height
        bitmap_info.bmiHeader.biPlanes = 1
        bitmap_info.bmiHeader.biBitCount = 32
        buffer = ctypes.create_string_buffer(width * height * 4)
        lines = gdi32.GetDIBits(
            memory_dc,
            bitmap,
            0,
            height,
            buffer,
            ctypes.byref(bitmap_info),
            0,
        )
        if lines != height:
            raise RuntimeError("Windows GetDIBits window capture failed.")
        image = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    finally:
        gdi32.SelectObject(memory_dc, old_object)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(handle, window_dc)


def save_screenshot(path, region=None):
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("Saving screenshots requires opencv-python.") from exc

    frame = capture_screen(region=region)
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    if not cv2.imwrite(path, frame):
        raise RuntimeError(f"Could not save screenshot: {path}")
    return path


def save_window_screenshot(path, hwnd):
    import cv2

    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    frame = capture_window(hwnd)
    if not cv2.imwrite(path, frame):
        raise RuntimeError(f"Could not save window screenshot: {path}")
    return path


class ScreenCapture:
    """Capture frames in memory and optionally retain a bounded debug history."""

    def __init__(self, debug=False, debug_dir="debug/screenshots", max_debug_files=50):
        self.debug = bool(debug)
        self.debug_dir = Path(debug_dir)
        self.max_debug_files = max(1, int(max_debug_files))

    def set_debug(self, enabled):
        self.debug = bool(enabled)

    def grab(self, region=None, label="frame"):
        frame = capture_screen(region=region)
        if self.debug:
            self.save_debug(frame, label=label)
        return frame

    def save_debug(self, frame, label="frame"):
        import cv2

        self.debug_dir.mkdir(parents=True, exist_ok=True)
        safe_label = "".join(
            char if char.isalnum() or char in "-_" else "_"
            for char in str(label)
        )
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        millis = int((time.time() % 1) * 1000)
        path = self.debug_dir / f"{timestamp}-{millis:03d}-{safe_label}.png"
        if not cv2.imwrite(str(path), frame):
            raise RuntimeError(f"Could not save debug screenshot: {path}")
        self.cleanup()
        return str(path)

    def cleanup(self):
        if not self.debug_dir.exists():
            return
        files = sorted(
            (
                path for path in self.debug_dir.iterdir()
                if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for old_path in files[self.max_debug_files:]:
            try:
                old_path.unlink()
            except OSError:
                pass

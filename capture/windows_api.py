import ctypes
from ctypes import wintypes


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
SW_RESTORE = 9
HWND_TOP = 0
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040


def _get_window_text(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def list_windows():
    windows = []

    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def enum_proc(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _get_window_text(hwnd)
        if title:
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            windows.append({
                "hwnd": int(hwnd),
                "title": title,
                "left": rect.left,
                "top": rect.top,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top,
            })
        return True

    user32.EnumWindows(enum_proc_type(enum_proc), 0)
    return windows


def find_window(title, exact=False):
    needle = title.lower()
    for window in list_windows():
        candidate = window["title"].lower()
        if (exact and needle == candidate) or (not exact and needle in candidate):
            return window
    return None


def focus_window(title, exact=False):
    window = find_window(title, exact=exact)
    if window is None:
        return None

    hwnd = wintypes.HWND(window["hwnd"])
    foreground = user32.GetForegroundWindow()
    current_thread = kernel32.GetCurrentThreadId()
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)
    foreground_thread = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0

    user32.ShowWindow(hwnd, SW_RESTORE)
    if foreground_thread:
        user32.AttachThreadInput(current_thread, foreground_thread, True)
    user32.AttachThreadInput(current_thread, target_thread, True)
    user32.BringWindowToTop(hwnd)
    user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.SetForegroundWindow(hwnd)
    user32.SetActiveWindow(hwnd)
    user32.SetFocus(hwnd)
    user32.AttachThreadInput(current_thread, target_thread, False)
    if foreground_thread:
        user32.AttachThreadInput(current_thread, foreground_thread, False)
    return window


def foreground_window():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return {
        "hwnd": int(hwnd),
        "title": _get_window_text(hwnd),
        "left": rect.left,
        "top": rect.top,
        "width": rect.right - rect.left,
        "height": rect.bottom - rect.top,
    }

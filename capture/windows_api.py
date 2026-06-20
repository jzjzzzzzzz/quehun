import ctypes
import sys
import subprocess
from ctypes import wintypes


SW_RESTORE = 9
HWND_TOP = 0
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040


def _is_windows():
    return sys.platform.startswith("win")


def _is_macos():
    return sys.platform == "darwin"


def _require_windows():
    if not _is_windows() or not hasattr(ctypes, "windll"):
        raise RuntimeError("Window management requires Windows.")
    return ctypes.windll.user32, ctypes.windll.kernel32


def _run_osascript(script):
    completed = subprocess.run(
        ["osascript", "-e", script],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(message or "AppleScript command failed.")
    return completed.stdout.strip()


def _list_macos_windows():
    script = r'''
set AppleScript's text item delimiters to linefeed
set output to {}
tell application "System Events"
    repeat with proc in (application processes whose visible is true)
        set processName to name of proc
        set processId to unix id of proc
        set windowIndex to 0
        repeat with win in windows of proc
            set windowIndex to windowIndex + 1
            try
                set windowName to name of win
                if windowName is "" then set windowName to processName
                set windowPosition to position of win
                set windowSize to size of win
                set end of output to processName & tab & processId & tab & windowIndex & tab & windowName & tab & (item 1 of windowPosition) & tab & (item 2 of windowPosition) & tab & (item 1 of windowSize) & tab & (item 2 of windowSize)
            end try
        end repeat
    end repeat
end tell
return output as text
'''
    rows = _run_osascript(script)
    windows = []
    for row in rows.splitlines():
        parts = row.split("\t")
        if len(parts) != 8:
            continue
        process_name, process_id, index, title, left, top, width, height = parts
        try:
            window = {
                "hwnd": f"mac:{process_id}:{index}",
                "process": process_name,
                "title": title,
                "left": int(float(left)),
                "top": int(float(top)),
                "width": int(float(width)),
                "height": int(float(height)),
            }
        except ValueError:
            continue
        if window["width"] > 0 and window["height"] > 0:
            windows.append(window)
    return windows


def _get_window_text(hwnd):
    user32, _ = _require_windows()
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def list_windows():
    if _is_macos():
        try:
            return _list_macos_windows()
        except RuntimeError:
            return []

    if not _is_windows():
        return []

    user32, _ = _require_windows()
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
    if _is_macos():
        window = find_window(title, exact=exact)
        if window is None:
            return None
        process_name = window.get("process") or window["title"]
        script = f'''
tell application "System Events"
    set targetName to "{process_name.replace('"', '\\"')}"
    if exists process targetName then
        set frontmost of process targetName to true
    end if
end tell
tell application "{process_name.replace('"', '\\"')}" to activate
'''
        _run_osascript(script)
        return window

    user32, kernel32 = _require_windows()
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
    if _is_macos():
        script = r'''
tell application "System Events"
    set proc to first application process whose frontmost is true
    set processName to name of proc
    set processId to unix id of proc
    if (count of windows of proc) is 0 then
        return processName & tab & processId & tab & "0" & tab & processName & tab & "0" & tab & "0" & tab & "0" & tab & "0"
    end if
    set win to first window of proc
    set windowName to name of win
    if windowName is "" then set windowName to processName
    set windowPosition to position of win
    set windowSize to size of win
    return processName & tab & processId & tab & "1" & tab & windowName & tab & (item 1 of windowPosition) & tab & (item 2 of windowPosition) & tab & (item 1 of windowSize) & tab & (item 2 of windowSize)
end tell
'''
        try:
            parts = _run_osascript(script).split("\t")
        except RuntimeError:
            return None
        if len(parts) != 8:
            return None
        process_name, process_id, index, title, left, top, width, height = parts
        try:
            return {
                "hwnd": f"mac:{process_id}:{index}",
                "process": process_name,
                "title": title,
                "left": int(float(left)),
                "top": int(float(top)),
                "width": int(float(width)),
                "height": int(float(height)),
            }
        except ValueError:
            return None

    if not _is_windows():
        return None

    user32, _ = _require_windows()
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

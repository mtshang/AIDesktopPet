"""Windows taskbar visibility for a window that must not take focus."""
import ctypes
from ctypes import wintypes
import sys

from PySide6.QtWidgets import QApplication


def sync_taskbar_visibility(window, hidden):
    # Offscreen Qt windows do not have usable Windows HWNDs (e.g. in tests).
    if sys.platform != "win32" or QApplication.platformName() != "windows":
        return

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    get_style = user32.GetWindowLongW
    get_style.argtypes = [wintypes.HWND, ctypes.c_int]
    get_style.restype = wintypes.LONG
    set_style = user32.SetWindowLongW
    set_style.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    set_style.restype = wintypes.LONG

    hwnd = int(window.winId())
    ctypes.set_last_error(0)
    style = get_style(hwnd, -20)  # GWL_EXSTYLE
    error = ctypes.get_last_error()
    if not style and error:
        raise ctypes.WinError(error)

    # WS_EX_NOACTIVATE suppresses the taskbar entry unless APPWINDOW is set.
    # Preserve it, the topmost style, and all other unrelated window styles.
    appwindow, toolwindow = 0x00040000, 0x00000080
    desired = ((style | toolwindow) & ~appwindow) if hidden else ((style | appwindow) & ~toolwindow)
    if desired != style:
        ctypes.set_last_error(0)
        previous = set_style(hwnd, -20, desired)
        error = ctypes.get_last_error()
        if not previous and error:
            raise ctypes.WinError(error)

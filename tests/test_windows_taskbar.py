"""Native Windows regression: run in a subprocess, separate from offscreen tests."""
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest


@unittest.skipUnless(sys.platform == "win32", "Windows taskbar styles")
class WindowsTaskbarTests(unittest.TestCase):
    def test_taskbar_survives_tutorial_and_visibility_changes(self):
        script = textwrap.dedent(r'''
            import ctypes
            from ctypes import wintypes
            from pathlib import Path
            import sys
            import tempfile
            from unittest.mock import patch
            from PySide6.QtCore import Qt, QTimer
            from PySide6.QtGui import QAction
            from PySide6.QtWidgets import QApplication, QWidget

            # Import application code without reading any real user settings.
            with tempfile.TemporaryDirectory() as root:
                with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(Path(root) / "app.exe")):
                    import pet
            app = QApplication([])
            app.setQuitOnLastWindowClosed(False)

            class Probe(pet.PetWindow):
                initUI = pet.PetWindow.initUI
                showEvent = pet.PetWindow.showEvent
                toggle_taskbar = pet.PetWindow.toggle_taskbar

                def __init__(self, hidden=False):
                    QWidget.__init__(self)
                    self.hide_taskbar = hidden
                    self.current_image_path = ""
                    self.initUI()
                    self.move(-10000, -10000)

                def show_static_image(self, path):
                    pass

                def init_tray(self):
                    self.tray_hide_action = QAction(self)

                def closeEvent(self, event):
                    QWidget.closeEvent(self, event)

                def update_bubble_position(self):
                    pass

            get_style = ctypes.windll.user32.GetWindowLongW
            get_style.argtypes = [wintypes.HWND, ctypes.c_int]
            get_style.restype = wintypes.LONG

            def check(window, hidden):
                app.processEvents()
                style = get_style(int(window.winId()), -20)
                assert bool(style & 0x00040000) == (not hidden), hex(style)
                assert bool(style & 0x00000080) == hidden, hex(style)
                assert style & 0x08000000, "must retain NOACTIVATE"
                assert style & 0x00000008, "must remain topmost"
                assert window.windowFlags() & Qt.WindowDoesNotAcceptFocus
                assert window.testAttribute(Qt.WA_ShowWithoutActivating)
                return style

            with patch.object(pet, "start_worker"), patch.object(pet, "ConfigSaveWorker"):
                window = Probe()
                window.show()
                original = check(window, False)
                dialog = pet.TutorialDialog(False, False)
                dialog.setAttribute(Qt.WA_ShowWithoutActivating)
                dialog.move(-10000, -10000)
                QTimer.singleShot(0, dialog.ok_btn.click)
                dialog.exec()
                assert not dialog.hide_cb.isChecked()
                check(window, False)
                for hidden in (True, False, True, False):
                    window.toggle_taskbar()
                    assert window.hide_taskbar == hidden
                    check(window, hidden)
                window.hide()
                window.show()
                assert check(window, False) == original
                window.close()
                window.destroy()
                # Startup with an already saved hidden preference.
                window = Probe(True)
                window.show()
                check(window, True)
                window.toggle_taskbar()
                check(window, False)
                window.close()
                window.destroy()
            print("Native taskbar regression passed")
        ''')
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "windows"
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1], env=env,
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

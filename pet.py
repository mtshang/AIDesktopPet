# 文件名：pet.py
import os
import json
import sys
import shutil
import keyboard
import random
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMenu
from PySide6.QtGui import QPixmap, QAction
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QMutex, QMutexLocker 

import bottom
from set import SettingsWindow

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

current_dir = get_base_path()
config_path = os.path.join(current_dir, "config.json")
modpath_path = os.path.join(current_dir, "modpath.json")

default_config_path = os.path.join(current_dir, "asset", "config_default.json")
default_modpath_path = os.path.join(current_dir, "asset", "modpath_default.json")

# 🌟 冗余自检，保证在单独测试 pet.py 时也能部署
if not os.path.exists(config_path) and os.path.exists(default_config_path):
    try: shutil.copy(default_config_path, config_path)
    except: pass
if not os.path.exists(modpath_path) and os.path.exists(default_modpath_path):
    try: shutil.copy(default_modpath_path, modpath_path)
    except: pass

class AIWorker(QThread):
    update_signal = Signal(str)

    def run(self):
        try:
            data = bottom.get_ai_reply()
            if data["status"] == "success":
                self.update_signal.emit(data["reply"])
            else:
                self.update_signal.emit(f"呜呜，引擎报错了喵：{data.get('message', '未知错误')}")
        except Exception as e:
            self.update_signal.emit("⚠️ 大脑短路了喵，请看终端报错。")
            print(f"\n[多线程 Debug 拦截] {e}")


class BubbleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel("", self)
        self.label.setStyleSheet("""
            background-color: rgba(255, 255, 255, 230);
            border: 2px solid #ffb6c1; border-radius: 12px;
            font-family: 'Microsoft YaHei';
            font-size: 14px; font-weight: bold; color: #333333;
        """)
        self.label.setMargin(10)
        self.label.setWordWrap(True)
        self.label.setFixedWidth(250)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)

    def set_text(self, text):
        self.label.setText(text)
        self.label.adjustSize()
        self.adjustSize()


class PetWindow(QWidget):
    trigger_f9_signal = Signal()
    
    def __init__(self):
        super().__init__()
        self.current_hotkey = 'f9'
        self.hotkey_enabled = True
        self.ignore_hotkey = False
        self.peek_mode = 'close'
        self.peek_params = {}
        
        self.bubble_win = BubbleWindow() 
        self.bubble_timer = QTimer(self)
        self.bubble_timer.timeout.connect(self.bubble_tick)
        self.bubble_time_left = 0
        
        self.was_bubble_visible_before_drag = False
        self.was_timer_running_before_drag = False
        
        self.last_pos_x = ""
        self.last_pos_y = ""
        self.pet_last = "default_pet" 
        
        self.load_initial_config()
        self.initUI()

        if self.last_pos_x != "" and self.last_pos_y != "":
            self.move(int(self.last_pos_x), int(self.last_pos_y))
        else:
            screen_geo = QApplication.primaryScreen().availableGeometry()
            default_x = int(screen_geo.width() * 0.85 - self.width() / 2)
            default_y = int(screen_geo.height() * 0.85 - self.height() / 2)
            self.move(default_x, default_y)

        self.settings_window = None
        self.ai_thread = AIWorker()
        self.ai_thread.update_signal.connect(self.update_bubble)
        self.trigger_f9_signal.connect(self.on_f9_pressed_safe)
        
        if self.hotkey_enabled:
            keyboard.add_hotkey(self.current_hotkey, self.trigger_f9_signal.emit)
        
        self.dot_count = 1
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.animate_loading_text)

        self.peek_timer = QTimer(self)
        self.peek_timer.timeout.connect(self.trigger_f9_signal.emit)
        
        self.setup_next_peek()
        
        hk_str = self.current_hotkey.title() if self.hotkey_enabled else ""
        initial_text = f"主人好喵！按 {hk_str} 我就会吐槽你哦~" if hk_str else "主人好喵！"
        self.show_bubble(initial_text, duration=15)
        

    def load_initial_config(self):
        if not os.path.exists(config_path): return
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.peek_mode = config.get("PEEK_MODE", "close")
                self.peek_params = config.get("PEEK_PARAMS", {})
                self.hotkey_enabled = config.get("HOTKEY_ENABLED", True)
                self.current_hotkey = config.get("HOTKEY", "f9").lower()
                
                self.last_pos_x = config.get("LAST_POS_X", "")
                self.last_pos_y = config.get("LAST_POS_Y", "")
                self.pet_last = config.get("PET_LAST", "default_pet") 
        except Exception as e:
            print(f"⚠️ 猫娘开机读取存档失败: {e}")

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        pet_image_path = os.path.join(current_dir, "asset", self.pet_last, "character.png")
        
        self.pet_img = QLabel(self)
        pixmap = QPixmap(pet_image_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaledToHeight(250, Qt.SmoothTransformation)
            self.pet_img.setPixmap(pixmap)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pet_img)
        self.setLayout(layout)
        
        self.drag_pos = None 

    def update_bubble_position(self):
        bx = self.geometry().x() + (self.width() - self.bubble_win.width()) // 2
        by = self.geometry().y() - self.bubble_win.height()
        self.bubble_win.move(bx, by)

    def show_bubble(self, text, duration=None):
        self.bubble_win.set_text(text)
        self.update_bubble_position()
        self.bubble_win.show()
        
        if duration is None:
            duration = max(1, int(len(text.encode('gbk')) / 2))
            
        self.bubble_time_left = duration
        self.bubble_timer.start(1000)

    def bubble_tick(self):
        self.bubble_time_left -= 1
        if self.bubble_time_left <= 0:
            self.bubble_timer.stop()
            self.bubble_win.hide()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_bubble_position()
    
    def moveEvent(self, event):
        super().moveEvent(event)
        self.update_bubble_position()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.was_bubble_visible_before_drag = self.bubble_win.isVisible()
            self.was_timer_running_before_drag = self.bubble_timer.isActive()
            self.bubble_win.hide()
            self.bubble_timer.stop()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        if self.was_bubble_visible_before_drag:
            self.update_bubble_position()
            self.bubble_win.show()
        if self.was_timer_running_before_drag:
            self.bubble_timer.start(1000)

    def closeEvent(self, event):
        self.save_current_position() 
        self.bubble_win.close()
        super().closeEvent(event)

    def save_current_position(self):
        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config["LAST_POS_X"] = self.x()
            config["LAST_POS_Y"] = self.y()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 保存位置存档失败: {e}")

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: white; border: 2px solid #ffb6c1; border-radius: 5px; } QMenu::item { padding: 5px 20px; font-family: 'Microsoft YaHei'; font-size: 13px; } QMenu::item:selected { background-color: #ffb6c1; color: white; }")
        
        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        quit_action = QAction("❌ 退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def open_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow()
            self.settings_window.recording_state_signal.connect(self.set_ignore_hotkey)
            self.settings_window.settings_saved_signal.connect(self.apply_settings)
            
        self.settings_window.show()
        self.settings_window.activateWindow()

    def set_ignore_hotkey(self, is_ignoring):
        self.ignore_hotkey = is_ignoring

    def apply_settings(self, settings):
        keyboard.unhook_all_hotkeys()
        self.current_hotkey = settings['hotkey']
        self.hotkey_enabled = settings['hotkey_enabled'] 
        
        if self.hotkey_enabled:
            keyboard.add_hotkey(self.current_hotkey, self.trigger_f9_signal.emit)

        hk_str = self.current_hotkey.title() if self.hotkey_enabled else ""
        if "主人好喵" in self.bubble_win.label.text():
            new_text = f"主人好喵！按 {hk_str} 我就会吐槽你哦~" if hk_str else "主人好喵！"
            self.show_bubble(new_text, duration=self.bubble_time_left)

        self.peek_mode = settings['peek_mode']
        self.peek_params = settings['peek_params']
        self.setup_next_peek()

    def setup_next_peek(self):
        self.peek_timer.stop() 
        if self.peek_mode == 'fixed':
            self.peek_timer.start(self.peek_params['interval'] * 1000)
        elif self.peek_mode == 'random':
            interval = random.randint(self.peek_params['min'], self.peek_params['max'])
            self.peek_timer.start(interval * 1000)

    def animate_loading_text(self):
        dots = "." * self.dot_count
        text = f"让我来看看{dots}"
        
        self.bubble_win.set_text(text)
        self.update_bubble_position()
        
        if not self.bubble_win.isVisible() and self.drag_pos is None:
            self.bubble_win.show()
            
        self.bubble_timer.stop()
        
        self.dot_count += 1
        if self.dot_count > 6: self.dot_count = 1

    def on_f9_pressed_safe(self):
        if self.ignore_hotkey: return
        
        if not self.ai_thread.isRunning():
            self.peek_timer.stop() 
            self.dot_count = 1
            self.show_bubble("让我来看看.", duration=5)
            self.animate_loading_text() 
            self.loading_timer.start(300) 
            self.ai_thread.start()

    def update_bubble(self, text):
        self.loading_timer.stop() 
        self.show_bubble(text)
        self.setup_next_peek()
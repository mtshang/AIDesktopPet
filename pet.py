# 文件名：pet.py
import os
import json
import sys
import shutil
import keyboard
import random
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QMenu, QMessageBox, 
                               QSystemTrayIcon)
from PySide6.QtGui import QPixmap, QAction, QIcon
from PySide6.QtCore import Qt, QThread, Signal, QTimer

import bottom
from set import SettingsWindow
from pet_bubble import BubbleWindow
from pet_tutorial import TutorialDialog
from json_write import save_config_atomic

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
        self.hide_taskbar = False 
        
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
        QTimer.singleShot(500, self.check_first_run)
        
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
                self.hide_taskbar = config.get("HIDE_TASKBAR", False)
        except Exception as e:
            print(f"⚠️ 猫娘开机读取存档失败: {e}")

    def initUI(self):
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        if self.hide_taskbar:
            flags |= Qt.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self.setWindowTitle("AIDesktopPet")

        icon_path = os.path.join(current_dir, "asset", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

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
        
        self.init_tray()

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        icon_path = os.path.join(current_dir, "asset", "icon.ico")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            fallback_img = os.path.join(current_dir, "asset", self.pet_last, "character.png")
            if os.path.exists(fallback_img): self.tray_icon.setIcon(QIcon(fallback_img))
        
        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet("QMenu { background-color: white; border: 1px solid #ffb6c1; } QMenu::item { padding: 5px 20px; font-family: 'Microsoft YaHei'; font-size: 13px; } QMenu::item:selected { background-color: #ffb6c1; color: white; }")

        center_action = QAction("🎯 桌宠居中", self)
        center_action.triggered.connect(self.center_pet)
        self.tray_menu.addAction(center_action)

        self.tray_hide_action = QAction(f"隐藏桌面任务栏 {'✓' if self.hide_taskbar else '×'}", self)
        self.tray_hide_action.triggered.connect(self.toggle_taskbar)
        self.tray_menu.addAction(self.tray_hide_action)

        self.tray_menu.addSeparator()

        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(self.open_settings)
        self.tray_menu.addAction(settings_action)

        quit_action = QAction("❌ 退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        self.tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

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
        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config["LAST_POS_X"] = self.x()
            config["LAST_POS_Y"] = self.y()
            save_config_atomic(config, config_path)
        except Exception as e:
            print(f"⚠️ 保存位置存档失败: {e}")
            
        self.bubble_win.close()
        QApplication.instance().quit()
        super().closeEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: white; border: 2px solid #ffb6c1; border-radius: 5px; } QMenu::item { padding: 5px 20px; font-family: 'Microsoft YaHei'; font-size: 13px; } QMenu::item:selected { background-color: #ffb6c1; color: white; }")
        
        tutorial_action = QAction("📖 查看教程", self)
        tutorial_action.triggered.connect(self.show_tutorial)
        menu.addAction(tutorial_action)
        
        menu.addSeparator()

        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        hide_action = QAction(f"隐藏桌面任务栏 {'✓' if self.hide_taskbar else '×'}", self)
        hide_action.triggered.connect(self.toggle_taskbar)
        menu.addAction(hide_action)

        quit_action = QAction("❌ 退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def toggle_taskbar(self):
        self.hide_taskbar = not self.hide_taskbar
        
        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config["HIDE_TASKBAR"] = self.hide_taskbar
            save_config_atomic(config, config_path)
        except Exception as e:
            print(f"保存任务栏状态失败: {e}")
        
        self.tray_hide_action.setText(f"隐藏桌面任务栏 {'✓' if self.hide_taskbar else '×'}")
        
        self.hide()
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        if self.hide_taskbar:
            flags |= Qt.Tool
        self.setWindowFlags(flags)
        self.show()

    def center_pet(self):
        screen_geo = QApplication.primaryScreen().availableGeometry()
        center_x = int(screen_geo.width() / 2 - self.width() / 2)
        center_y = int(screen_geo.height() / 2 - self.height() / 2)
        self.move(center_x, center_y)
        self.show()

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
        # 配合气泡的状态机进行校验，如果不在请求中，直接跳出
        if not self.bubble_win.is_waiting_for_ai:
            return

        # 🌟【核心修复】：如果 2 秒的防抖警告气泡正在显示，立刻跳出，别让“点点点”动画去抢戏！
        if self.bubble_win.busy_timer.isActive():
            return

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
        
        # 🌟 核心拦截机制：如果子线程（AI 请求）仍在运行，说明桌宠还在忙
        if self.ai_thread.isRunning():
            # 【唤起 2 秒防抖气泡拦截】
            self.bubble_win.show_busy_message()
            self.update_bubble_position()
            if not self.bubble_win.isVisible() and self.drag_pos is None:
                self.bubble_win.show()
            return
            
        # 如果空闲，开启新一轮的大脑请求
        self.bubble_win.is_waiting_for_ai = True
        self.peek_timer.stop() 
        self.dot_count = 1
        
        self.show_bubble("让我来看看.", duration=5)
        self.animate_loading_text() 
        self.loading_timer.start(300) 
        self.ai_thread.start()

    def update_bubble(self, text):
        # 大模型返回成功，重置等待状态，停止点点点动画
        self.bubble_win.is_waiting_for_ai = False
        self.loading_timer.stop() 
        
        self.show_bubble(text)
        self.setup_next_peek()

    def check_first_run(self):
        is_first = True
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    is_first = config.get("IS_FIRST_RUN", True)
            except: pass

        if is_first:
            self.show_tutorial()
            
    def show_tutorial(self):
        current_admin = False
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    current_admin = json.load(f).get("RUN_AS_ADMIN", False)
        except: pass

        dialog = TutorialDialog(self.hide_taskbar, current_admin)
        dialog.exec() 
        
        if dialog.hide_cb.isChecked() != self.hide_taskbar:
            self.toggle_taskbar()
            
        new_admin_state = dialog.admin_cb.isChecked()
        needs_restart = (new_admin_state != current_admin)
        
        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
            config["IS_FIRST_RUN"] = False
            config["RUN_AS_ADMIN"] = new_admin_state 
            
            save_config_atomic(config, config_path)
        except Exception as e:
            print(f"保存新手教程状态失败: {e}")

        if needs_restart:
            QMessageBox.information(self, "权限变更", "👑 您勾选了以管理员身份运行！\n\n为了让防快捷键失效的最高权限生效，请手动【退出并重新启动】桌宠喵！")
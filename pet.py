from worker_lifecycle import start_worker, is_shutting_down, worker_registry
# 文件名：pet.py
import os
import json
import sys
import shutil
import keyboard
import random
import time
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QMenu, QMessageBox, 
                               QSystemTrayIcon)
from PySide6.QtGui import QPixmap, QAction, QIcon, QFontDatabase
from PySide6.QtCore import Qt, QThread, Signal, QTimer

import bottom
from set import SettingsWindow
from pet_bubble import BubbleWindow
from pet_tutorial import TutorialDialog
from json_write import update_config_atomic

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

class ScreenshotWorker(QThread):
    finished_signal = Signal(str)

    def run(self):
        try:
            img_b64 = bottom.get_screen_b64()
            self.finished_signal.emit(img_b64 if img_b64 else "")
        except Exception as e:
            print(f"[截图线程报错] {e}")
            self.finished_signal.emit("")

class AIWorker(QThread):
    update_signal = Signal(str)
    img_b64 = None

    def run(self):
        try:
            data = bottom.get_ai_reply(self.img_b64) 
            if data["status"] == "success":
                self.update_signal.emit(data["reply"])
            else:
                ui_msgs = bottom.global_config.get_ui_msgs()
                self.update_signal.emit(f"{ui_msgs['error_head_msg']}{data.get('message', '未知错误')}")
        except Exception as e:
            self.update_signal.emit("⚠️ 大脑短路了喵，请看终端报错。")
            print(f"\n[多线程 Debug 拦截] {e}")

class ConfigSaveWorker(QThread):
    def __init__(self, config_path, updates_dict):
        super().__init__()
        self.config_path = config_path
        self.updates_dict = updates_dict

    def run(self):
        try:
            update_config_atomic(self.config_path, self.updates_dict)
        except Exception as e:
            print(f"后台保存配置失败: {e}")

class PetWindow(QWidget):
    trigger_f9_signal = Signal()
    
    def __init__(self):
        super().__init__()
        
        self.load_custom_fonts()
        
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
        
        self.image_cache = {}
        
        self.nature_data = {} 
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.play_next_frame)
        self.current_anim_frames = []
        self.current_anim_times = []
        self.current_frame_index = 0
        self.current_state = "standing" 
        self.current_css_frames = [] 
        
        self.load_initial_config()
        self.resolve_pet_path_and_image()
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
        
        self.screenshot_thread = ScreenshotWorker()
        self.screenshot_thread.finished_signal.connect(self.on_screenshot_ready)
        
        self.trigger_f9_signal.connect(self.on_f9_pressed_safe)
        
        if self.hotkey_enabled:
            keyboard.add_hotkey(self.current_hotkey, self.trigger_f9_signal.emit)
        
        self.dot_count = 1
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.animate_loading_text)

        self.peek_timer = QTimer(self)
        self.peek_timer.timeout.connect(self.trigger_f9_signal.emit)
        
        self.setup_next_peek()
        
        ui_msgs = bottom.global_config.get_ui_msgs()
        hk_str = self.current_hotkey.title() if self.hotkey_enabled else ""
        initial_text = ui_msgs['hello_hk_msg'] if hk_str else ui_msgs['hello_msg']
        self.show_bubble(initial_text, duration=15)
        QTimer.singleShot(500, self.check_first_run)
        
        self.switch_animation_state("standing")

    def load_custom_fonts(self):
        font_dir = os.path.join(current_dir, "asset", "font")
        regular_path = os.path.join(font_dir, "HarmonyOS_Sans_SC_Regular.ttf")
        bold_path = os.path.join(font_dir, "HarmonyOS_Sans_SC_Bold.ttf")

        if os.path.exists(regular_path):
            QFontDatabase.addApplicationFont(regular_path)
        if os.path.exists(bold_path):
            QFontDatabase.addApplicationFont(bold_path)

    def wake_up_from_other_instance(self):
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.show()
        self.activateWindow()
        self.raise_()
        self.show_bubble("别点啦，本猫一直都在喵！", duration=4)

    def resolve_pet_path_and_image(self):
        self.image_cache.clear()
        
        path_petmod = os.path.join(current_dir, "petmod", self.pet_last)
        path_asset = os.path.join(current_dir, "asset", "pet", self.pet_last)
        
        if os.path.exists(path_petmod) and os.path.isdir(path_petmod):
            self.pet_folder_path = path_petmod
        elif os.path.exists(path_asset) and os.path.isdir(path_asset):
            self.pet_folder_path = path_asset
        else:
            print(f"⚠️ 找不到桌宠配置 [{self.pet_last}]，强制回退到 default_pet！")
            self.pet_last = "default_pet"
            self.pet_folder_path = os.path.join(current_dir, "asset", "pet", "default_pet")
            
            self.fallback_worker = ConfigSaveWorker(config_path, {"PET_LAST": "default_pet"})
            self.fallback_worker.finished.connect(self.fallback_worker.deleteLater)
            start_worker(self.fallback_worker)

        self.current_image_path = os.path.join(self.pet_folder_path, "character.png")
        self.current_scale = 1.0 
        self.nature_data = {}
        
        nature_file = os.path.join(self.pet_folder_path, "nature.json")
        if os.path.exists(nature_file):
            try:
                with open(nature_file, 'r', encoding='utf-8') as f:
                    self.nature_data = json.load(f)
                    img_name = self.nature_data.get("default_image", "")
                    if img_name:
                        self.current_image_path = os.path.join(self.pet_folder_path, img_name)
                    self.current_scale = self.nature_data.get("scale", 1.0)
            except Exception as e:
                print(f"读取 nature.json 失败: {e}")

    def switch_animation_state(self, state_name):
        if state_name == "error":
            if not self.nature_data.get("have_error", False):
                state_name = "standing"
        
        self.current_state = state_name
        self.anim_timer.stop() 
        
        if not self.nature_data.get(f"have_{state_name}", False):
            self.show_static_image(self.current_image_path)
            return
            
        mode = self.nature_data.get(f"{state_name}_mode", "static")
        file_node = self.nature_data.get("file", {}).get(state_name, {})
        
        if mode == "static":
            img_name = file_node.get("image", "")
            img_path = os.path.join(self.pet_folder_path, state_name, img_name) if img_name else self.current_image_path
            self.show_static_image(img_path)
            
        elif mode == "sequence":
            self.current_anim_frames = file_node.get("frame", [])
            self.current_anim_times = file_node.get("frame_time", [])
            if not self.current_anim_frames:
                self.show_static_image(self.current_image_path)
                return
                
            self.current_frame_index = 0
            self.play_next_frame() 
            
        elif mode == "css":
            sprite_filename = file_node.get("css_sprites", "")
            if not sprite_filename:
                self.show_static_image(self.current_image_path)
                return
                
            sprite_path = os.path.join(self.pet_folder_path, state_name, sprite_filename)
            if not os.path.exists(sprite_path):
                self.show_static_image(self.current_image_path)
                return
                
            list_cache_key = f"css_list_{state_name}_{sprite_filename}_{self.current_scale}"
            
            # 🌟 终极防御 1：动态读取列数和行数，并防止 0 或空字符串导致闪退
            try: cols = max(1, int(file_node.get("css_col", 1)))
            except: cols = 1
            
            try: rows = max(1, int(file_node.get("css_row", 1)))
            except: rows = 1
            
            self.sprite_total_frames = cols * rows
            self.sprite_current_frame = 0
            
            if list_cache_key not in self.image_cache:
                full_sprite = QPixmap(sprite_path)
                if full_sprite.isNull():
                    self.show_static_image(self.current_image_path)
                    return
                    
                # 🌟 终极防御 2：使用刚拿到的局部变量 cols 和 rows 进行切割计算，彻底抛弃未定义的 self 变量
                frame_w = full_sprite.width() // cols
                frame_h = full_sprite.height() // rows
                target_height = int(250 * self.current_scale)
                
                frames_list = []
                for i in range(self.sprite_total_frames):
                    row = i // cols
                    col = i % cols
                    x = col * frame_w
                    y = row * frame_h
                    frame_pix = full_sprite.copy(x, y, frame_w, frame_h)
                    frames_list.append(frame_pix.scaledToHeight(target_height, Qt.SmoothTransformation))
                    
                self.image_cache[list_cache_key] = frames_list
                
            self.current_css_frames = self.image_cache[list_cache_key]
            
            # 🌟 终极防御 3：防止 json 里时间填了空字符串 "" 导致强转 int 报错
            try: wait_time = int(file_node.get("css_sprite_time", 100))
            except: wait_time = 100
                
            self.play_next_frame() 
            self.anim_timer.start(max(1, wait_time))

    def show_static_image(self, img_path):
        if not os.path.exists(img_path): return
        
        if img_path not in self.image_cache:
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                target_height = int(250 * self.current_scale)
                self.image_cache[img_path] = pixmap.scaledToHeight(target_height, Qt.SmoothTransformation)
            else:
                return
                
        self.pet_img.setPixmap(self.image_cache[img_path])

    def play_next_frame(self):
        mode = self.nature_data.get(f"{self.current_state}_mode", "static")
        
        if mode == "sequence":
            if not self.current_anim_frames: return
            
            img_name = self.current_anim_frames[self.current_frame_index]
            img_path = os.path.join(self.pet_folder_path, self.current_state, img_name)
            
            self.show_static_image(img_path)
            
            wait_time = 100 
            if self.current_frame_index < len(self.current_anim_times):
                try: wait_time = int(self.current_anim_times[self.current_frame_index])
                except: wait_time = 100
                
            self.anim_timer.start(max(1, wait_time))
            
            self.current_frame_index += 1
            if self.current_frame_index >= len(self.current_anim_frames):
                self.current_frame_index = 0
                
        elif mode == "css":
            if not hasattr(self, 'current_css_frames') or not self.current_css_frames: 
                return
            
            self.pet_img.setPixmap(self.current_css_frames[self.sprite_current_frame])
            
            self.sprite_current_frame += 1
            if self.sprite_current_frame >= self.sprite_total_frames:
                self.sprite_current_frame = 0

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

        self.pet_img = QLabel(self)
        self.show_static_image(self.current_image_path)

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
            if os.path.exists(self.current_image_path): 
                self.tray_icon.setIcon(QIcon(self.current_image_path))
        
        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet("QMenu { background-color: white; border: 1px solid #ffb6c1; } QMenu::item { padding: 5px 20px; font-family: 'HarmonyOS Sans SC'; font-size: 13px; } QMenu::item:selected { background-color: #ffb6c1; color: white; }")

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
        quit_action.triggered.connect(self.request_shutdown)
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
            duration = max(1, int(len(text.encode('gbk', errors='replace')) / 2))
            
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
            self.switch_animation_state("draging")
            
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
        
        if self.bubble_win.is_waiting_for_ai:
            self.switch_animation_state("thinking")
        else:
            self.switch_animation_state("standing")
            
        if self.was_bubble_visible_before_drag:
            self.update_bubble_position()
            self.bubble_win.show()
        if self.was_timer_running_before_drag:
            self.bubble_timer.start(1000)

    def closeEvent(self, event):
        event.ignore()
        self.request_shutdown()

    def request_shutdown(self):
        if is_shutting_down():
            return
        for timer in (self.peek_timer, self.loading_timer, self.anim_timer, self.bubble_timer,
                      self.bubble_win.busy_timer):
            timer.stop()
        keyboard.unhook_all_hotkeys()
        self.hide()
        self.bubble_win.hide()
        self.tray_icon.hide()
        if self.settings_window is not None:
            self.settings_window.hide()
        registry = worker_registry()
        registry.drained.connect(self.finish_shutdown)
        registry.begin_shutdown()

    def finish_shutdown(self):
        try:
            update_config_atomic(config_path, {"LAST_POS_X": self.x(), "LAST_POS_Y": self.y()})
        except Exception as exc:
            print(f"保存位置失败: {exc}")
        QApplication.instance().quit()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: white; border: 2px solid #ffb6c1; border-radius: 5px; } QMenu::item { padding: 5px 20px; font-family: 'HarmonyOS Sans SC'; font-size: 13px; } QMenu::item:selected { background-color: #ffb6c1; color: white; }")
        
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
        quit_action.triggered.connect(self.request_shutdown)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def toggle_taskbar(self):
        self.hide_taskbar = not self.hide_taskbar
        
        self.taskbar_worker = ConfigSaveWorker(config_path, {"HIDE_TASKBAR": self.hide_taskbar})
        self.taskbar_worker.finished.connect(self.taskbar_worker.deleteLater)
        start_worker(self.taskbar_worker)
        
        self.tray_hide_action.setText(f"隐藏桌面任务栏 {'✓' if self.hide_taskbar else '×'}")
        
        self.hide()
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
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
            self.settings_window.mod_applied_signal.connect(self.reload_mod_hotly)
            
        self.settings_window.show()
        self.settings_window.activateWindow()
        
    def reload_mod_hotly(self, new_pet_folder):
        self.pet_last = new_pet_folder
        self.resolve_pet_path_and_image()
        bottom.global_config.reload_nature_config() 
        self.switch_animation_state("standing")

    def set_ignore_hotkey(self, is_ignoring):
        self.ignore_hotkey = is_ignoring

    def apply_settings(self, settings):
        keyboard.unhook_all_hotkeys()
        self.current_hotkey = settings['hotkey']
        self.hotkey_enabled = settings['hotkey_enabled'] 
        
        if self.hotkey_enabled:
            keyboard.add_hotkey(self.current_hotkey, self.trigger_f9_signal.emit)

        hk_str = self.current_hotkey.title() if self.hotkey_enabled else ""
        
        ui_msgs = bottom.global_config.get_ui_msgs()
        current_text = self.bubble_win.label.text()
        if current_text in [ui_msgs['hello_msg'], ui_msgs['hello_hk_msg']] or "主人好喵" in current_text:
            new_text = ui_msgs['hello_hk_msg'] if hk_str else ui_msgs['hello_msg']
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
        if not self.bubble_win.is_waiting_for_ai:
            return

        if self.bubble_win.busy_timer.isActive():
            return

        dots = "." * self.dot_count
        ui_msgs = bottom.global_config.get_ui_msgs()
        text = f"{ui_msgs['peek_msg']}{dots}"
        
        self.bubble_win.set_text(text)
        self.update_bubble_position()
        
        if not self.bubble_win.isVisible() and self.drag_pos is None:
            self.bubble_win.show()
            
        self.bubble_timer.stop()
        
        self.dot_count += 1
        if self.dot_count > 6: self.dot_count = 1

    def on_f9_pressed_safe(self):
        if is_shutting_down():
            return
        if self.ignore_hotkey: return
        
        ui_msgs = bottom.global_config.get_ui_msgs()
        
        if self.bubble_win.is_waiting_for_ai and not (self.screenshot_thread.isRunning() or self.ai_thread.isRunning()):
            return  # The screenshot is queued but its thread has not started yet.
        if self.screenshot_thread.isRunning() or self.ai_thread.isRunning():
            self.bubble_win.show_busy_message(ui_msgs['peekagain_msg'], ui_msgs['peek_msg'])
            self.update_bubble_position()
            if not self.bubble_win.isVisible() and self.drag_pos is None:
                self.bubble_win.show()
            return
            
        self.bubble_win.is_waiting_for_ai = True
        self.peek_timer.stop() 
        self.dot_count = 1
        
        self.hide()
        self.bubble_win.hide()
        
        QApplication.processEvents()
        QTimer.singleShot(50, lambda: start_worker(self.screenshot_thread))

    def on_screenshot_ready(self, img_b64):
        if is_shutting_down():
            return
        self.show()
        self.switch_animation_state("thinking")
        
        ui_msgs = bottom.global_config.get_ui_msgs()
        self.show_bubble(f"{ui_msgs['peek_msg']}.", duration=5)
        self.animate_loading_text() 
        self.loading_timer.start(300) 
        
        self.ai_thread.img_b64 = img_b64
        start_worker(self.ai_thread)

    def update_bubble(self, text):
        if is_shutting_down():
            return
        self.bubble_win.is_waiting_for_ai = False
        self.loading_timer.stop() 
        
        ui_msgs = bottom.global_config.get_ui_msgs()
        if (ui_msgs['error_head_msg'] and text.startswith(ui_msgs['error_head_msg'])) or "大脑短路" in text:
            self.switch_animation_state("error")
        else:
            self.switch_animation_state("standing")
            
        self.show_bubble(text)
        self.setup_next_peek()

    def check_first_run(self):
        if is_shutting_down():
            return
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
        
        new_hide_state = dialog.hide_cb.isChecked()
        new_admin_state = dialog.admin_cb.isChecked()
        
        needs_restart = (new_admin_state != current_admin)
        needs_toggle_taskbar = (new_hide_state != self.hide_taskbar)
        
        self.tutorial_worker = ConfigSaveWorker(config_path, {
            "IS_FIRST_RUN": False,
            "RUN_AS_ADMIN": new_admin_state
        })
        self.tutorial_worker.finished.connect(self.tutorial_worker.deleteLater)
        start_worker(self.tutorial_worker)

        if needs_restart:
            QMessageBox.information(self, "权限变更", "👑 您勾选了以管理员身份运行！\n\n为了让防快捷键失效的最高权限生效，请手动【退出并重新启动】桌宠喵！")
            
        if needs_toggle_taskbar:
            self.toggle_taskbar()
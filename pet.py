# 文件名：pet.py
import os
import json
import sys
import shutil
import keyboard
import random
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QMenu, QMessageBox, 
                               QSystemTrayIcon, QDialog, QHBoxLayout, QPushButton, QCheckBox)
from PySide6.QtGui import QPixmap, QAction, QIcon
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

# 🌟 新增：高级教程弹窗（带底部功能区）
class TutorialDialog(QDialog):
    def __init__(self, current_hide_state, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ 新手教程")
        self.setWindowIcon(QIcon(os.path.join(current_dir, "asset", "icon.ico")))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(480)
        self.setStyleSheet("background-color: #ffffff;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        text = (
            "这里是新手教程！使用前必读！！！（可以在右键桌宠的菜单中再次查看教程）\n\n"
            "    1. 鼠标左键按住桌宠移动鼠标可以改变桌宠位置，鼠标右键可以调出菜单（包括“设置”、“退出”等）。\n\n"
            "    2. 一定要先在“设置”→“api设置”中新建配置，配置api并保存后才能正常使用！（暂时需要你上网自学如何获取相关大模型api，这里推荐搜索【火山引擎api申请】，后续会更新相关教程）\n\n"
            "    3. 完成第2步后，按下键盘上的 F9（或你自定义的快捷键），宠物就会观察你的屏幕并吐槽。当然，你也可以在“设置”→“窥屏设置”详细设置（包括“定时窥屏”，修改“窥屏快捷键”等）。"
        )
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; line-height: 1.6; color: #333;")
        layout.addWidget(label)
        
        layout.addSpacing(15)
        
        # 底部控制区
        bottom_layout = QHBoxLayout()
        self.hide_cb = QCheckBox("隐藏桌面任务栏图标")
        self.hide_cb.setStyleSheet("font-size: 13px; color: #555;")
        self.hide_cb.setChecked(current_hide_state) # 同步当前状态
        bottom_layout.addWidget(self.hide_cb)
        
        bottom_layout.addStretch()
        
        self.ok_btn = QPushButton("开始体验！")
        self.ok_btn.setStyleSheet("""
            QPushButton { 
                padding: 8px 20px; 
                font-weight: bold; 
                background-color: #FF69B4; 
                color: white; 
                border-radius: 5px; 
                font-size: 14px; 
            }
            QPushButton:hover { 
                background-color: #FF1493; 
            }
        """)
        self.ok_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.ok_btn)
        
        layout.addLayout(bottom_layout)
        self.setLayout(layout)


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
        self.hide_taskbar = False # 默认不隐藏任务栏
        
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
                self.hide_taskbar = config.get("HIDE_TASKBAR", False) # 🌟 读取任务栏设置
        except Exception as e:
            print(f"⚠️ 猫娘开机读取存档失败: {e}")

    def initUI(self):
        # 🌟 动态决定是否隐藏任务栏
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        if self.hide_taskbar:
            flags |= Qt.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setWindowTitle("AIDesktopPet")

        # 加载自定义软件图标（如果有）
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
        
        # 🌟 启动右下角系统托盘
        self.init_tray()

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # 托盘图标优先用根目录的 icon.ico，没有就用当前的桌宠图片
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
        # 退出时保存坐标位置
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
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存任务栏状态失败: {e}")
        
        # 刷新托盘文本
        self.tray_hide_action.setText(f"隐藏桌面任务栏 {'✓' if self.hide_taskbar else '×'}")
        
        # 刷新窗口属性
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
        dialog = TutorialDialog(self.hide_taskbar)
        dialog.exec() 
        
        # 弹窗关闭后，检查复选框状态是否被用户修改了
        if dialog.hide_cb.isChecked() != self.hide_taskbar:
            self.toggle_taskbar()
            
        # 存档：保证开机新手教程只弹一次
        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config["IS_FIRST_RUN"] = False
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存新手教程状态失败: {e}")
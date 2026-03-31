# 文件名：set.py
import os, sys, shutil
from PySide6.QtWidgets import QWidget, QHBoxLayout, QListWidget, QStackedWidget
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

# 🌟 导入我们拆分出去的四个武将
from set_general import GeneralPage
from set_api import ApiPage
from set_peek import PeekPage
from set_mod import ModPage

def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

current_dir = get_base_path()
config_path = os.path.join(current_dir, "config.json")
modpath_path = os.path.join(current_dir, "modpath.json")

default_config_path = os.path.join(current_dir, "asset", "config_default.json")
default_modpath_path = os.path.join(current_dir, "asset", "modpath_default.json")

# 冗余自检
if not os.path.exists(config_path) and os.path.exists(default_config_path):
    try: shutil.copy(default_config_path, config_path)
    except: pass
if not os.path.exists(modpath_path) and os.path.exists(default_modpath_path):
    try: shutil.copy(default_modpath_path, modpath_path)
    except: pass

class SettingsWindow(QWidget):
    # 这两个核心 Signal 不能丢，它是和 pet.py 沟通的桥梁
    settings_saved_signal = Signal(dict)
    recording_state_signal = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("桌宠设置中心")
        self.setWindowIcon(QIcon(os.path.join(current_dir, "asset", "icon.ico")))
        self.resize(1024, 576)
        
        main_layout = QHBoxLayout()
        
        self.sidebar = QListWidget()
        self.sidebar.setMaximumWidth(120)
        self.sidebar.addItem("🧰 综合设置")
        self.sidebar.addItem("⚙️ api设置")
        self.sidebar.addItem("👁️ 窥屏设置")
        self.sidebar.addItem("🎨 桌宠设置") # 🌟 我们给 MOD 预留的位子
        self.sidebar.currentRowChanged.connect(self.switch_page)
        
        self.content_area = QStackedWidget()
        
        # 实例化四个子页面
        self.general_page = GeneralPage()
        self.api_page = ApiPage()
        self.peek_page = PeekPage()
        self.mod_page = ModPage()
        
        # ⚡️【核心解耦魔法】：把窥屏子页面里触发的信号，直接转发给主窗体的信号！
        self.peek_page.settings_saved_signal.connect(self.settings_saved_signal.emit)
        self.peek_page.recording_state_signal.connect(self.recording_state_signal.emit)
        
        # 将子页面装入右侧的栈容器中
        self.content_area.addWidget(self.general_page)
        self.content_area.addWidget(self.api_page)
        self.content_area.addWidget(self.peek_page)
        self.content_area.addWidget(self.mod_page)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)
        self.setLayout(main_layout)
        
        self.setStyleSheet("""
            QListWidget { font-family: 'Microsoft YaHei'; font-size: 14px; border: 1px solid #ffb6c1; border-radius: 5px; background-color: #fffaf0; outline: none; }
            QListWidget::item { padding: 10px; }
            QListWidget::item:selected { background-color: #ffb6c1; color: white; border-radius: 3px; }
        """)

    def switch_page(self, index):
        self.content_area.setCurrentIndex(index)
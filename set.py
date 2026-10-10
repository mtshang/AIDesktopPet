# 文件名：set.py
import os, sys, shutil
from PySide6.QtWidgets import QWidget, QHBoxLayout, QListWidget, QStackedWidget
from PySide6.QtGui import QIcon, QFontDatabase  # 🌟 引入字体数据库
from PySide6.QtCore import Signal

# 🌟 导入拆分后的功能页面
from set_general import GeneralPage
from set_api import ApiPage
from set_peek import PeekPage
from set_mod import ModPage

def get_base_path():
    """获取程序执行的根目录，适配打包环境"""
    if getattr(sys, 'frozen', False): 
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

current_dir = get_base_path()
config_path = os.path.join(current_dir, "config.json")
modpath_path = os.path.join(current_dir, "modpath.json")

# 默认资源路径
default_config_path = os.path.join(current_dir, "asset", "config_default.json")
default_modpath_path = os.path.join(current_dir, "asset", "modpath_default.json")

# 冗余自检与配置文件修复
if not os.path.exists(config_path) and os.path.exists(default_config_path):
    try: shutil.copy(default_config_path, config_path)
    except: pass
if not os.path.exists(modpath_path) and os.path.exists(default_modpath_path):
    try: shutil.copy(default_modpath_path, modpath_path)
    except: pass

class SettingsWindow(QWidget):
    # 🌟 核心：跨页面通信信号
    settings_saved_signal = Signal(dict)
    recording_state_signal = Signal(bool)
    mod_applied_signal = Signal(str)

    def __init__(self):
        super().__init__()
        
        # 🛡️ 1. 字体排雷：动态加载鸿蒙商用字体
        self.load_custom_fonts()
        
        self.setWindowTitle("桌宠设置中心")
        self.setWindowIcon(QIcon(os.path.join(current_dir, "asset", "icon.ico")))
        self.resize(1024, 576)
        
        main_layout = QHBoxLayout()
        
        # 侧边栏列表
        self.sidebar = QListWidget()
        self.sidebar.setMaximumWidth(120)
        self.sidebar.addItem("🧰 综合设置")
        self.sidebar.addItem("⚙️ api配置")
        self.sidebar.addItem("👁️ 窥屏设置")
        self.sidebar.addItem("🎨 桌宠配置") 
        self.sidebar.currentRowChanged.connect(self.switch_page)
        
        # 右侧堆叠区域
        self.content_area = QStackedWidget()
        
        # 实例化四个子页面
        self.general_page = GeneralPage()
        self.api_page = ApiPage()
        self.peek_page = PeekPage()
        self.mod_page = ModPage()
        
        # ⚡️【信号接力】：将子页面的信号转发给外部监听者
        self.peek_page.settings_saved_signal.connect(self.settings_saved_signal.emit)
        self.peek_page.recording_state_signal.connect(self.recording_state_signal.emit)
        self.mod_page.mod_applied_signal.connect(self.mod_applied_signal.emit)
        
        # 装载页面
        self.content_area.addWidget(self.general_page)
        self.content_area.addWidget(self.api_page)
        self.content_area.addWidget(self.peek_page)
        self.content_area.addWidget(self.mod_page)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)
        self.setLayout(main_layout)
        
        # 🎨 2. 界面除颤：移除‘Microsoft YaHei’，替换为‘HarmonyOS Sans SC’
        self.apply_styles()

    def load_custom_fonts(self):
        """将 asset/font 目录下的字体加载进程序字体库"""
        font_dir = os.path.join(current_dir, "asset", "font")
        regular_path = os.path.join(font_dir, "HarmonyOS_Sans_SC_Regular.ttf")
        bold_path = os.path.join(font_dir, "HarmonyOS_Sans_SC_Bold.ttf")

        if os.path.exists(regular_path):
            QFontDatabase.addApplicationFont(regular_path)
        if os.path.exists(bold_path):
            QFontDatabase.addApplicationFont(bold_path)

    def apply_styles(self):
        """应用统一的样式表"""
        self.setStyleSheet("""
            QListWidget { 
                font-family: 'HarmonyOS Sans SC';  /* 🌟 已成功替换为鸿蒙字体 */
                font-size: 14px; 
                border: 1px solid #ffb6c1; 
                border-radius: 5px; 
                background-color: #fffaf0; 
                outline: none; 
            }
            QListWidget::item { 
                padding: 10px; 
            }
            QListWidget::item:selected { 
                background-color: #ffb6c1; 
                color: white; 
                border-radius: 3px; 
            }
        """)

    def switch_page(self, index):
        """页面切换逻辑"""
        self.content_area.setCurrentIndex(index)
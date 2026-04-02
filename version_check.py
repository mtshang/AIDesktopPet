# 文件名：version_check.py
import json
import os
import sys
import requests
import urllib3
import webbrowser

# 【新增】引入我们刚刚写好的原子化写入工具
from json_write import save_config_atomic

# ==========================================
# 🌟 核心变化 1：引入 PySide6 相关组件
# ==========================================
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton, QHBoxLayout, QApplication
from PySide6.QtGui import QIcon

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_base_path():
    """获取绝对路径，完美兼容开发环境与打包后的 .exe 环境"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# 动态拼接出绝对安全的路径
CONFIG_PATH = os.path.join(get_base_path(), 'asset', 'version.json')
ICON_PATH = os.path.join(get_base_path(), 'asset', 'icon.ico')

def load_config():
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        default_config = {
            "current_version": "v0.1.0",
            "ignored_versions": [],
            "latest_version": "v0.1.0"
        }
        save_config(default_config)
        return default_config
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    """
    【核心修改】放弃原有的危险写入方式，
    直接调用工业级原子化写入，彻底保护配置文件防损坏！
    """
    save_config_atomic(config, CONFIG_PATH)

# ==========================================
# 🌟 核心变化 2：用 PySide6 重写弹窗 UI
# ==========================================
class UpdateDialog(QDialog):
    def __init__(self, cloud_version, parent=None):
        super().__init__(parent)
        self.cloud_version = cloud_version
        self.config = load_config()
        
        self.setWindowTitle("桌宠更新通知")
        self.setFixedSize(400, 200)
        
        # 设置窗口左上角的图标！
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        
        # 让窗口保持在最前端
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        # 初始化布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # 提示文本
        self.label = QLabel(f"发现新版本啦喵：{self.cloud_version}！")
        self.label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 14pt; font-weight: bold; margin: 15px;")
        layout.addWidget(self.label, alignment=Qt.AlignCenter)
        
        # 忽略复选框
        self.ignore_checkbox = QCheckBox("忽略本次新版本通知")
        self.ignore_checkbox.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 11pt;")
        layout.addWidget(self.ignore_checkbox, alignment=Qt.AlignCenter)
        
        # 按钮布局 (水平)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        btn_layout.setContentsMargins(0, 10, 0, 0)
        
        # 前往下载按钮
        self.download_btn = QPushButton("去看看")
        self.download_btn.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 11pt; padding: 5px 15px;")
        self.download_btn.clicked.connect(self.on_download)
        
        # 确认按钮
        self.confirm_btn = QPushButton("我知道了")
        self.confirm_btn.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 11pt; padding: 5px 15px;")
        self.confirm_btn.clicked.connect(self.on_confirm)
        
        btn_layout.addWidget(self.download_btn)
        btn_layout.addWidget(self.confirm_btn)
        layout.addLayout(btn_layout)

    def on_download(self):
        """点击去看看，直接用浏览器打开项目 Release 页"""
        webbrowser.open("https://github.com/mtshang/AIDesktopPet/releases")
        self.on_confirm()

    def on_confirm(self):
        """处理确认逻辑并关闭窗口"""
        if self.ignore_checkbox.isChecked():
            if self.cloud_version not in self.config.get("ignored_versions", []):
                self.config["ignored_versions"].append(self.cloud_version)
                save_config(self.config)
        self.accept()

# ==========================================
# 🌟 核心变化 3：把网络请求塞进 QThread
# ==========================================
class VersionCheckThread(QThread):
    update_found_signal = Signal(str)

    def __init__(self):
        super().__init__()

    def fetch_latest_version(self):
        urls = [
            "https://fastly.jsdelivr.net/gh/mtshang/AIDesktopPet@main/asset/version.json",
            "https://raw.gitmirror.com/mtshang/AIDesktopPet/main/asset/version.json",
            "https://ghproxy.net/https://raw.githubusercontent.com/mtshang/AIDesktopPet/main/asset/version.json",
            "https://cdn.staticaly.com/gh/mtshang/AIDesktopPet/main/asset/version.json",
            "https://raw.kkgithub.com/mtshang/AIDesktopPet/main/asset/version.json"
        ]
        zh_nums = ["一", "二", "三", "四", "五"]
        
        for i, url in enumerate(urls):
            try:
                response = requests.get(
                    url, 
                    timeout=3, 
                    verify=False,
                    proxies={"http": None, "https": None}
                )
                response.raise_for_status() 
                data = response.json()
                return data.get("current_version")
            except Exception:
                num_str = zh_nums[i] if i < len(zh_nums) else str(i + 1)
                print(f"节点{num_str}失败，尝试切换线路喵...")
                continue
                
        print("五大节点全军覆没！猫娘决定继续潜水喵...")
        return None

    def run(self):
        cloud_version = self.fetch_latest_version()
        if not cloud_version:
            return
            
        config = load_config()
        
        if config.get("latest_version") != cloud_version:
            config["latest_version"] = cloud_version
            save_config(config)
            
        if cloud_version != config["current_version"]:
            if cloud_version not in config.get("ignored_versions", []):
                print(f"后台发现新版本：{cloud_version}，正在呼叫大堂经理...")
                self.update_found_signal.emit(cloud_version)
            else:
                print(f"版本 {cloud_version} 在忽略列表中，不弹窗。")
        else:
            print("当前已经是最新版本了，没有任何更新。")

# ==========================================
# 🌟 核心变化 4：对外提供启动接口
# ==========================================
_checker_thread = None 

def start_version_check_async():
    global _checker_thread
    _checker_thread = VersionCheckThread()
    _checker_thread.update_found_signal.connect(lambda v: UpdateDialog(v).exec())
    _checker_thread.start()

if __name__ == "__main__":
    print("开始测试版本检查 (PySide6 信号槽版)...")
    app = QApplication(sys.argv)
    start_version_check_async()
    sys.exit(app.exec())
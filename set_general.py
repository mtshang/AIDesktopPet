# 文件名：set_general.py
import os, sys, json
import winreg  # 【新增】用于操作 Windows 注册表
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QMessageBox

# 【新增】引入工业级防损坏写入工具
from json_write import save_config_atomic

def get_base_path():
    if getattr(sys, 'frozen', False): 
        return os.path.dirname(sys.executable)
    else: 
        return os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(get_base_path(), "config.json")
# 【新增】版本信息文件的路径
version_path = os.path.join(get_base_path(), "asset", "version.json")

class GeneralPage(QWidget):
    def __init__(self):
        super().__init__()
        self.original_admin_state = False
        self.original_autostart_state = False  # 【新增】记录原始自启状态
        self.current_ver = "未知"
        self.latest_ver = "未知"
        
        self.load_version_info()  # 在初始化 UI 前先读取版本号
        self.init_ui()
        self.load_config()

    def load_version_info(self):
        """读取本地的 version.json 获取版本号信息"""
        if os.path.exists(version_path):
            try:
                with open(version_path, 'r', encoding='utf-8') as f:
                    v_data = json.load(f)
                    self.current_ver = v_data.get("current_version", "未知")
                    self.latest_ver = v_data.get("latest_version", "未知")
            except Exception as e:
                print(f"⚠️ 读取 version.json 失败: {e}")

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # ==========================================
        # 🌟 软件信息板块
        # ==========================================
        info_title = QLabel("<b>ℹ️ 软件信息 (Software Info)</b>")
        info_title.setStyleSheet("font-size: 16px; color: #333;")
        layout.addWidget(info_title)

        ver_layout = QHBoxLayout()
        
        # 当前版本显示
        cur_ver_label = QLabel(f"<b>当前版本号：</b><span style='color: #666;'>{self.current_ver}</span>")
        cur_ver_label.setStyleSheet("font-size: 14px;")
        
        # 最新版本显示
        if self.current_ver != self.latest_ver and self.latest_ver != "未知":
            latest_color = "#ff4500" 
            latest_text = "&nbsp;&nbsp;<i>(发现新版本喵！)</i>"
        else:
            latest_color = "#3cb371" 
            latest_text = "&nbsp;&nbsp;<i>(已是最新)</i>"

        latest_ver_label = QLabel(f"<b>最新版本号：</b><span style='color: {latest_color};'>{self.latest_ver}</span><span style='color: #888;'>{latest_text}</span>")
        latest_ver_label.setStyleSheet("font-size: 14px;")

        ver_layout.addWidget(cur_ver_label)
        ver_layout.addWidget(latest_ver_label)
        ver_layout.addStretch() 
        layout.addLayout(ver_layout)

        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #e0e0e0; margin-top: 5px; margin-bottom: 5px;")
        layout.addWidget(line)

        # ==========================================
        # 综合与高级设置板块
        # ==========================================
        title = QLabel("<b>🧰 综合与高级设置 (General Settings)</b>")
        title.setStyleSheet("font-size: 16px; color: #333;")
        layout.addWidget(title)
        
        # 管理员权限勾选
        self.admin_cb = QCheckBox("👑 以管理员身份运行 (解决全屏游戏快捷键失效)")
        self.admin_cb.setStyleSheet("font-size: 14px; color: #ff4500; font-weight: bold; padding-top: 10px;")
        layout.addWidget(self.admin_cb)

        # 【新增】开机启动勾选
        self.autostart_cb = QCheckBox(" 开机自动启动 ")
        self.autostart_cb.setStyleSheet("font-size: 14px; color: #333; padding-bottom: 10px;")
        layout.addWidget(self.autostart_cb)

        layout.addStretch()

        self.save_general_btn = QPushButton("💾 保存综合设置")
        self.save_general_btn.setMinimumHeight(40)
        self.save_general_btn.setStyleSheet("QPushButton { background-color: #ffb6c1; color: white; font-weight: bold; border-radius: 5px; font-size: 14px; } QPushButton:hover { background-color: #ff91a4; }")
        self.save_general_btn.clicked.connect(self.save_general_settings)
        layout.addWidget(self.save_general_btn)

        self.setLayout(layout)

    def load_config(self):
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.original_admin_state = config.get("RUN_AS_ADMIN", False)
                    self.original_autostart_state = config.get("AUTO_START", False) # 【新增】加载自启状态
            except: pass
        self.admin_cb.setChecked(self.original_admin_state)
        self.autostart_cb.setChecked(self.original_autostart_state) # 【新增】更新 UI

    def set_windows_autostart(self, enabled):
        """修改注册表实现或取消开机自启"""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "AIDesktopPet" # 注册表中的键名
        
        # 获取当前运行的程序路径 (适配打包后的 exe 或源码运行)
        if getattr(sys, 'frozen', False):
            app_path = sys.executable
        else:
            app_path = os.path.abspath(sys.argv[0])

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass # 如果本来就没有，就不管它
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"写入注册表失败: {e}")
            return False

    def save_general_settings(self):
        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            new_admin_state = self.admin_cb.isChecked()
            new_autostart_state = self.autostart_cb.isChecked()

            # 1. 处理注册表
            reg_success = self.set_windows_autostart(new_autostart_state)
            
            # 2. 更新 config 数据
            config["RUN_AS_ADMIN"] = new_admin_state
            config["AUTO_START"] = new_autostart_state # 【新增】

            # 3. 原子化写入
            save_config_atomic(config, config_path)
                
            # 提示逻辑
            msg = "综合设置已保存喵！"
            if new_admin_state != self.original_admin_state:
                msg += "\n\n👑 管理员权限设置已更改，请重启桌宠生效！"
                self.original_admin_state = new_admin_state
            
            if not reg_success:
                msg += "\n\n⚠️ 开机自启写入注册表失败，请检查杀毒软件是否拦截。"
            
            QMessageBox.information(self, "成功", msg)
            self.original_autostart_state = new_autostart_state
                
        except Exception as e:
            QMessageBox.warning(self, "存档失败", f"写入配置失败：{e}")
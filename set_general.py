# 文件名：set_general.py
import os, sys, json
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QPushButton, QMessageBox

def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(get_base_path(), "config.json")

class GeneralPage(QWidget):
    def __init__(self):
        super().__init__()
        self.original_admin_state = False
        self.init_ui()
        self.load_config()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        title = QLabel("<b>🧰 综合与高级设置 (General Settings)</b>")
        title.setStyleSheet("font-size: 16px; color: #333;")
        layout.addWidget(title)
        
        self.admin_cb = QCheckBox("👑 以管理员身份运行 (强烈建议全屏游戏玩家勾选，解决快捷键失效问题)")
        self.admin_cb.setStyleSheet("font-size: 14px; color: #ff4500; font-weight: bold; padding: 10px 0;")
        layout.addWidget(self.admin_cb)

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
            except: pass
        self.admin_cb.setChecked(self.original_admin_state)

    def save_general_settings(self):
        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            new_admin_state = self.admin_cb.isChecked()
            config["RUN_AS_ADMIN"] = new_admin_state
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                
            if new_admin_state != self.original_admin_state:
                QMessageBox.information(self, "设置已保存", "👑 管理员权限设置已更改！\n\n为了让权限生效，请手动【退出并重新启动】桌宠喵！")
                self.original_admin_state = new_admin_state
            else:
                QMessageBox.information(self, "成功", "综合设置已保存喵！")
                
        except Exception as e:
            QMessageBox.warning(self, "存档失败", f"写入 config.json 失败：{e}")
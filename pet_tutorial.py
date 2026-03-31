# 文件名：pet_tutorial.py
import os
import sys
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QPushButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

current_dir = get_base_path()

class TutorialDialog(QDialog):
    def __init__(self, current_hide_state, current_admin_state, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ 新手教程")
        self.setWindowIcon(QIcon(os.path.join(current_dir, "asset", "icon.ico")))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(500)
        self.setStyleSheet("background-color: #ffffff;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        text = (
            "这里是新手教程！使用前必读！！！（可以在右键桌宠的菜单中再次查看教程）\n\n"
            "    1. 鼠标左键按住桌宠移动鼠标可以改变桌宠位置，鼠标右键可以调出菜单（包括“设置”、“退出”等）。\n\n"
            "    2. 一定要先在“设置”→“api设置”中新建配置，配置api并保存后才能正常使用！（暂时需要你上网自学如何获取相关大模型api，这里推荐搜索【火山引擎api申请】，后续会更新相关教程）\n\n"
            "    3. 完成第2步后，按下键盘上的 F9（或你自定义的快捷键），桌宠就会观察你的屏幕并吐槽。当然，你也可以在“设置”→“窥屏设置”详细设置。\n\n"
            "    4. 如果您会在运行全屏程序时使用该桌宠快捷键，请务必勾选【以管理员身份运行】！后续可以在“设置”→“综合设置”中更改是/否选择。"
        )
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; line-height: 1.6; color: #333;")
        layout.addWidget(label)
        
        layout.addSpacing(15)
        
        # 底部控制区
        bottom_layout = QHBoxLayout()
        checkbox_layout = QVBoxLayout()
        
        self.hide_cb = QCheckBox("隐藏桌面任务栏图标")
        self.hide_cb.setStyleSheet("font-size: 13px; color: #555;")
        self.hide_cb.setChecked(current_hide_state) 
        
        self.admin_cb = QCheckBox("👑 以管理员身份运行 (防快捷键失效)")
        self.admin_cb.setStyleSheet("font-size: 13px; color: #ff4500; font-weight: bold;")
        self.admin_cb.setChecked(current_admin_state)
        
        checkbox_layout.addWidget(self.hide_cb)
        checkbox_layout.addWidget(self.admin_cb)
        
        bottom_layout.addLayout(checkbox_layout)
        bottom_layout.addStretch()
        
        self.ok_btn = QPushButton("开始体验！")
        self.ok_btn.setStyleSheet("""
            QPushButton { padding: 8px 20px; font-weight: bold; background-color: #FF69B4; color: white; border-radius: 5px; font-size: 14px; }
            QPushButton:hover { background-color: #FF1493; }
        """)
        self.ok_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.ok_btn)
        
        layout.addLayout(bottom_layout)
        self.setLayout(layout)
# 文件名：set_mod.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class ModPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        label = QLabel("🛠️ \n\n(功能开发中...)")
        label.setStyleSheet("font-size: 20px; color: #ff69b4; font-weight: bold;")
        label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(label)
        self.setLayout(layout)
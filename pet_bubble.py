# 文件名：pet_bubble.py
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

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
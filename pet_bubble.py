# 文件名：pet_bubble.py
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer

class BubbleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel("", self)
        self.label.setTextFormat(Qt.PlainText)
        # 🌟 字体替换 1：气泡主文本
        self.label.setStyleSheet("""
            background-color: rgba(255, 255, 255, 230);
            border: 2px solid #ffb6c1; border-radius: 12px;
            font-family: 'HarmonyOS Sans SC';
            font-size: 14px; font-weight: bold; color: #333333;
            padding-right: 25px; 
        """)
        self.label.setMargin(10)
        self.label.setWordWrap(True)
        self.label.setFixedWidth(250)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.close_btn = QPushButton("×", self)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        # 🌟 字体替换 2：关闭按钮的悬浮样式
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #ffb6c1;
                border: 2px solid #ffb6c1;
                border-radius: 10px; 
                font-family: 'HarmonyOS Sans SC';
                font-size: 14px;
                font-weight: bold;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background-color: #ffb6c1;
                color: white;
            }
        """)
        self.close_btn.clicked.connect(self.hide_bubble)

        self.is_waiting_for_ai = False 
        
        self.busy_timer = QTimer(self)
        self.busy_timer.setSingleShot(True)
        self.busy_timer.timeout.connect(self.revert_to_looking)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.close_btn.move(self.width() - 26, 6)

    def hide_bubble(self):
        self.hide()
        if self.busy_timer.isActive():
            self.busy_timer.stop()

    def set_text(self, text):
        if self.busy_timer.isActive():
            self.busy_timer.stop()
            
        self.label.setText(text)
        self.label.adjustSize()
        self.adjustSize()
        
        if self.is_waiting_for_ai:
            self.close_btn.hide()  
        else:
            self.close_btn.show()  

    # 🌟 核心修改：接收外部传进来的文本，不再写死
    def show_busy_message(self, busy_text, peek_text):
        """当 F9 触发防抖拦截时，调用此函数"""
        self.label.setText(busy_text)
        self.base_peek_msg = peek_text # 存下 peek_msg，等会恢复用
        self.label.adjustSize()
        self.adjustSize()
        
        self.close_btn.hide()
        self.busy_timer.start(2000)

    def revert_to_looking(self):
        """2 秒倒计时结束触发"""
        if self.is_waiting_for_ai:
            # 🌟 核心修改：恢复时使用存下来的 peek_msg，并加上一个点
            self.set_text(f"{getattr(self, 'base_peek_msg', '让我来看看')}.")
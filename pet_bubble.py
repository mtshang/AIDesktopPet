# 文件名：pet_bubble.py
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer

class BubbleWindow(QWidget):
    def __init__(self):
        super().__init__()
        # 🌟 移除了 Qt.WindowTransparentForInput，否则鼠标点不到关闭按钮
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel("", self)
        # 为右侧预留出 padding，防止长文字被关闭按钮挡住
        self.label.setStyleSheet("""
            background-color: rgba(255, 255, 255, 230);
            border: 2px solid #ffb6c1; border-radius: 12px;
            font-family: 'Microsoft YaHei';
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

        # ==========================================
        # 🌟 气泡专属控件：圆形粉色关闭按钮
        # ==========================================
        self.close_btn = QPushButton("×", self)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #ffb6c1;
                border: 2px solid #ffb6c1;
                border-radius: 10px; /* 圆角是宽高的一半，即为圆形 */
                font-family: 'Microsoft YaHei';
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

        # ==========================================
        # 🌟 防抖与气泡状态机核心控制区
        # ==========================================
        self.is_waiting_for_ai = False 
        
        self.busy_timer = QTimer(self)
        self.busy_timer.setSingleShot(True)
        self.busy_timer.timeout.connect(self.revert_to_looking)

    def resizeEvent(self, event):
        """当气泡尺寸因为文字变化而改变时，永远把按钮钉在右上角"""
        super().resizeEvent(event)
        self.close_btn.move(self.width() - 26, 6)

    def hide_bubble(self):
        """点击按键时隐藏气泡"""
        self.hide()
        if self.busy_timer.isActive():
            self.busy_timer.stop()

    def set_text(self, text):
        """核心重写：任何正规的文本更新，都会立刻打断 2 秒防抖气泡"""
        if self.busy_timer.isActive():
            self.busy_timer.stop()
            
        self.label.setText(text)
        self.label.adjustSize()
        self.adjustSize()
        
        # 🌟【核心显示逻辑】：根据当前是否处于大模型任务中，决定按键的去留
        if self.is_waiting_for_ai:
            self.close_btn.hide()  # 正在加载中，隐藏关闭按钮防误触
        else:
            self.close_btn.show()  # 空闲状态（欢迎、成功回复、报错），显示关闭按钮

    def show_busy_message(self):
        """当 F9 触发防抖拦截时，调用此函数"""
        self.label.setText("本猫还在思考啦喵！")
        self.label.adjustSize()
        self.adjustSize()
        
        # 🌟 拦截气泡也是不允许关闭的
        self.close_btn.hide()
        
        self.busy_timer.start(2000)

    def revert_to_looking(self):
        """2 秒倒计时结束触发"""
        if self.is_waiting_for_ai:
            self.set_text("让我来看看.")
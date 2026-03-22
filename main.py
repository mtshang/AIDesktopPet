# 文件名：main.py
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # Windows 8.1及以上
except:
    pass
import sys
from PySide6.QtWidgets import QApplication

# 引入我们刚才独立出去的猫娘主窗口
from pet import PetWindow

if __name__ == '__main__':
    print("🚀 正在启动全息桌宠系统...")
    
    app = QApplication(sys.argv)
    
    # 🌟 绝杀连坐 Bug：告诉系统，只有右键点击“退出”才能杀进程
    # 无论怎么关闭设置窗口，猫娘都不会死！
    app.setQuitOnLastWindowClosed(False)
    
    pet = PetWindow()
    pet.show()
    
    exit_code = app.exec()
    print("👋 系统已安全退出，无任何僵尸进程残留。")
    sys.exit(exit_code)
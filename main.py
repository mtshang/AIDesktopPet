# 文件名：main.py
import sys
import os
import json
import ctypes

# 1. 🌟 极致高清：High DPI 适配 (保持你原来的优秀设计)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # Windows 8.1及以上
except:
    pass

# 2. 🌟 提权魔法核心函数
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def check_and_elevate():
    """极其优雅的自举提权函数"""
    current_dir = get_base_path()
    config_path = os.path.join(current_dir, "config.json")
    
    run_as_admin = False
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                run_as_admin = json.load(f).get("RUN_AS_ADMIN", False)
        except: pass

    # 如果 JSON 里要求管理员权限
    if run_as_admin:
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False

        if not is_admin:
            print("🔄 检测到最高权限需求，正在呼叫 UAC 盾牌重启...")
            # 调用 Windows 底层 API 申请以 admin 身份重新运行自己
            if getattr(sys, 'frozen', False):
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
            else:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1)
            
            # 杀掉当前的“平民权限”进程，留下新弹出的“贵族进程”
            sys.exit()

# ⚡️ 必须在实例化 QApplication 之前执行提权拦截！
check_and_elevate()


# ==========================================
# 下面是你原本干净利落的 UI 启动逻辑
# ==========================================
from PySide6.QtWidgets import QApplication

# 引入我们刚才独立出去的桌宠主窗口
from pet import PetWindow

if __name__ == '__main__':
    print("🚀 正在启动全息桌宠系统...")
    
    app = QApplication(sys.argv)
    
    # 🌟 绝杀连坐 Bug：告诉系统，只有右键点击“退出”才能杀进程
    # 无论怎么关闭设置窗口，桌宠都不会死！
    app.setQuitOnLastWindowClosed(False)
    
    pet = PetWindow()
    pet.show()
    
    exit_code = app.exec()
    print("👋 系统已安全退出，无任何僵尸进程残留。")
    sys.exit(exit_code)
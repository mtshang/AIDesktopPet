# 文件名：main.py
import sys
import os
import json
import ctypes

# 将 Qt 相关的引入放到最前面
from PySide6.QtWidgets import QApplication, QMessageBox
from pet import PetWindow
from version_check import start_version_check_async

# 1. 🌟 极致高清：High DPI 适配
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # Windows 8.1及以上
except:
    pass

# 2. 🌟 提权魔法与防崩溃降级核心函数
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def check_and_elevate():
    """极其优雅的自举提权与降级函数"""
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
            if getattr(sys, 'frozen', False):
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
            else:
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1)
            
            # 【核心修复】：捕获并判断 UAC 盾牌的返回值
            if ret > 32:
                # 返回值大于 32 代表提权成功，新进程已经弹出来了，旧进程安心离场
                sys.exit()
            else:
                # 返回值 <= 32 代表提权失败（比如用户点了“否”）
                print("⚠️ UAC 提权被取消，降级为普通权限运行。")
                QMessageBox.warning(
                    None, 
                    "权限请求被取消", 
                    "您取消了管理员提权！\n桌宠将以普通权限继续运行，但在全屏游戏内使用快捷键可能会没有反应。"
                )

# ==========================================
# 程序的真正入口
# ==========================================
if __name__ == '__main__':
    print("🚀 正在启动全息桌宠系统...")
    
    # 🌟 第一步：必须先把 app 实例化！
    # 这样如果后面提权被拒，我们才能用 QMessageBox 弹出警告框，不然程序会直接崩溃
    app = QApplication(sys.argv)
    
    # ⚡️ 第二步：执行提权拦截与降级检测
    check_and_elevate()
    
    # 🌟 绝杀连坐 Bug：告诉系统，只有右键点击“退出”才能杀进程
    app.setQuitOnLastWindowClosed(False)
    
    # 第三步：常规加载桌宠
    pet = PetWindow()
    pet.show()
    
    print("🔍 正在后台呼叫云端检查新版本...")
    start_version_check_async()
    
    exit_code = app.exec()
    print("👋 系统已安全退出，无任何僵尸进程残留。")
    sys.exit(exit_code)
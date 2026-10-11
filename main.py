# 文件名：main.py
import sys
import os
import json
import ctypes

# 将 Qt 相关的引入放到最前面
from PySide6.QtWidgets import QApplication, QMessageBox
# 🌟 新增：引入本地套接字通信模块，用于单例检测
from PySide6.QtNetwork import QLocalServer, QLocalSocket

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
# 🌟 3. 单例运行核心逻辑
# ==========================================
APP_UNIQUE_ID = "AIDesktopPet_Unique_Instance_Socket_2024"

def check_single_instance(app):
    """检查单例，如果已存在则唤醒旧实例并退出当前实例"""
    socket = QLocalSocket()
    socket.connectToServer(APP_UNIQUE_ID)
    
    if socket.waitForConnected(500):
        # 连接成功，说明已经有一个实例在运行了
        print("🔄 检测到已有实例运行，正在发送唤醒信号...")
        socket.write(b"WAKE_UP")
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        sys.exit(0) # 核心：第二个实例立刻自杀
        
    # 如果连接失败，说明是第一个实例，建立服务器监听
    server = QLocalServer(app)
    # 清理可能因为上次异常崩溃残留的死套接字
    QLocalServer.removeServer(APP_UNIQUE_ID) 
    if not server.listen(APP_UNIQUE_ID):
        # Another process may have won the race between connecting and listening.
        socket.abort()
        socket.connectToServer(APP_UNIQUE_ID)
        if socket.waitForConnected(500):
            socket.write(b"WAKE_UP")
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            sys.exit(0)
        QMessageBox.warning(None, "启动失败", "无法创建桌宠单例服务：" + server.errorString())
        sys.exit(1)
    return server

# ==========================================
# 程序的真正入口
# ==========================================
if __name__ == '__main__':
    print("🚀 正在启动全息桌宠系统...")
    
    # 🌟 第一步：必须先把 app 实例化！
    app = QApplication(sys.argv)
    
    # ⚡️ 第二步：执行提权拦截与降级检测
    check_and_elevate()
    
    # 🌟 绝杀连坐 Bug：告诉系统，只有右键点击“退出”才能杀进程
    app.setQuitOnLastWindowClosed(False)
    
    # ⚡️ 第三步：检查单例并建立监听 (必须在提权之后执行)
    server = check_single_instance(app)
    
    # 第四步：常规加载桌宠
    pet = PetWindow()
    pet.show()
    
    # ⚡️ 第五步：绑定服务器收到消息时的回调函数
    def on_new_connection():
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            received = bytearray()

            def read_message(socket=socket, received=received):
                received.extend(bytes(socket.readAll()))
                if b"WAKE_UP" in received:
                    pet.wake_up_from_other_instance()
                    socket.disconnectFromServer()

            socket.readyRead.connect(read_message)
            socket.disconnected.connect(socket.deleteLater)
            read_message()

    server.newConnection.connect(on_new_connection)
    
    print("🔍 正在后台呼叫云端检查新版本...")
    start_version_check_async()
    
    exit_code = app.exec()
    print("👋 系统已安全退出，无任何僵尸进程残留。")
    sys.exit(exit_code)
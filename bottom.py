# 文件名：bottom.py
import base64
import io
import os
import json
import shutil
import sys
import gc  # 引入 Python 垃圾回收模块
import time  # 【新增】引入时间模块，用于计算 API 耗时
from PIL import Image, ImageGrab
from openai import OpenAI

# 引入工业级防损坏写入工具
from json_write import save_config_atomic

# ==========================================
# 1. 动态配置加载区 (带记忆功能的雷达扫描版)
# ==========================================
VISION_API_KEY = ""
VISION_BASE_URL = ""
VISION_MODEL = ""
CHAT_API_KEY = ""
CHAT_BASE_URL = ""
CHAT_MODEL = ""
VISION_PROMPT = ""
CHAT_PROMPT = ""
VISION_MAX_TOKENS = 300 
CHAT_MAX_TOKENS = 150

API_LAST = ""
PET_LAST = "default_pet" 

def get_base_path():
    """获取程序运行的真实目录，兼容源码模式和打包模式"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

current_dir = get_base_path()
config_path = os.path.join(current_dir, "config.json")
modpath_path = os.path.join(current_dir, "modpath.json")

default_config_path = os.path.join(current_dir, "asset", "config_default.json")
default_modpath_path = os.path.join(current_dir, "asset", "modpath_default.json")

# 🌟 开机自检与自动部署出厂设置
if not os.path.exists(config_path) and os.path.exists(default_config_path):
    try:
        shutil.copy(default_config_path, config_path)
        print("📦 [初始化] 已自动从 asset 部署 config.json")
    except Exception as e:
        print(f"⚠️ [初始化] 部署 config.json 失败: {e}")

if not os.path.exists(modpath_path) and os.path.exists(default_modpath_path):
    try:
        shutil.copy(default_modpath_path, modpath_path)
        print("📦 [初始化] 已自动从 asset 部署 modpath.json")
    except Exception as e:
        print(f"⚠️ [初始化] 部署 modpath.json 失败: {e}")

config_data = {}
if os.path.exists(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config_data = json.load(file)
            API_LAST = config_data.get("API_LAST", "")
            PET_LAST = config_data.get("PET_LAST", "default_pet")
            print(f"📖 成功读取历史存档 -> API: {API_LAST}, 桌宠: {PET_LAST}")
    except Exception as e:
        print(f"⚠️ 读取 config.json 失败，存档可能损坏: {e}")

need_update_config = False 

api_folder = os.path.join(current_dir, "api")
all_apis = {}

if os.path.exists(api_folder):
    for filename in os.listdir(api_folder):
        if filename.endswith(".json"):
            file_path = os.path.join(api_folder, filename)
            config_name = os.path.splitext(filename)[0]
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    all_apis[config_name] = json.load(file)
            except Exception as e:
                print(f"⚠️ 解析 {filename} 失败: {e}")

if all_apis:
    if API_LAST and API_LAST in all_apis:
        active_api_key = API_LAST
        print(f"🔄 恢复历史 API 引擎：【{active_api_key}】")
    else:
        active_api_key = list(all_apis.keys())[0]
        API_LAST = active_api_key
        need_update_config = True
        print(f"🚀 挂载默认 API 引擎：【{active_api_key}】 (历史记录已失效或为空)")

    active_config = all_apis[active_api_key]
    VISION_API_KEY = active_config.get("VISION_API_KEY", "")
    VISION_BASE_URL = active_config.get("VISION_BASE_URL", "")
    VISION_MODEL = active_config.get("VISION_MODEL", "")
    CHAT_API_KEY = active_config.get("CHAT_API_KEY", "")
    CHAT_BASE_URL = active_config.get("CHAT_BASE_URL", "")
    CHAT_MODEL = active_config.get("CHAT_MODEL", "")

nature_path = os.path.join(current_dir, "asset", PET_LAST, "nature.json")
if os.path.exists(nature_path):
    try:
        with open(nature_path, 'r', encoding='utf-8') as file:
            active_nature = json.load(file)
            VISION_PROMPT = active_nature.get("vision_prompt", "")
            CHAT_PROMPT = active_nature.get("chat_prompt", "")
            VISION_MAX_TOKENS = active_nature.get("vision_max_tokens", 300)
            CHAT_MAX_TOKENS = active_nature.get("chat_max_tokens", 150)
        print(f"🎭 成功挂载桌宠灵魂与外观：【{PET_LAST}】")
    except Exception as e:
        print(f"⚠️ 解析 {nature_path} 失败: {e}")
else:
    print(f"⚠️ 找不到桌宠配置文件：{nature_path}")

if need_update_config:
    try:
        config_data["API_LAST"] = API_LAST
        config_data["PET_LAST"] = PET_LAST
        save_config_atomic(config_data, config_path)
        print(f"📝 自动存档完毕！已安全更新 config.json")
    except Exception as e:
        print(f"⚠️ 自动存档失败: {e}")

# ==========================================
# 【核心模块】专用于被外部触发的全局变量热更新函数
# ==========================================
def update_api_globals():
    global VISION_API_KEY, VISION_BASE_URL, VISION_MODEL
    global CHAT_API_KEY, CHAT_BASE_URL, CHAT_MODEL
    global API_LAST
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                API_LAST = config.get("API_LAST", API_LAST)
                
        if API_LAST:
            api_file = os.path.join(current_dir, "api", f"{API_LAST}.json")
            if os.path.exists(api_file):
                with open(api_file, 'r', encoding='utf-8') as f:
                    api_config = json.load(f)
                    VISION_API_KEY = api_config.get("VISION_API_KEY", VISION_API_KEY)
                    VISION_BASE_URL = api_config.get("VISION_BASE_URL", VISION_BASE_URL)
                    VISION_MODEL = api_config.get("VISION_MODEL", VISION_MODEL)
                    CHAT_API_KEY = api_config.get("CHAT_API_KEY", CHAT_API_KEY)
                    CHAT_BASE_URL = api_config.get("CHAT_BASE_URL", CHAT_BASE_URL)
                    CHAT_MODEL = api_config.get("CHAT_MODEL", CHAT_MODEL)
        print(f"🔄 [底层引擎] 收到更新信号！全局 API 变量已成功覆写，当前引擎：【{API_LAST}】")
    except Exception as e:
        print(f"⚠️ [底层引擎] 热更新全局变量失败: {e}")

# ==========================================
# 2. 核心 AI 处理接口 (熔断超时 & 性能监控版)
# ==========================================
def get_ai_reply():
    print("\n[底层引擎] 正在执行截图与大模型分析...")
    
    # 提前声明变量，方便在 finally 中统一清理
    screenshot = None
    resized_screenshot = None
    buffered = None
    
    # 记录全局起始时间
    global_start_time = time.time()
    
    try:
        # 1. 抓取原生屏幕截图
        screenshot = ImageGrab.grab()
        
        # 2. 短边对齐 512 像素等比缩放
        orig_width, orig_height = screenshot.size
        target_min = 512
        
        if orig_width < orig_height:
            ratio = target_min / orig_width
            new_width = target_min
            new_height = int(orig_height * ratio)
        else:
            ratio = target_min / orig_height
            new_height = target_min
            new_width = int(orig_width * ratio)
            
        resized_screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        buffered = io.BytesIO()
        if resized_screenshot.mode == 'RGBA':
            old_resized = resized_screenshot
            resized_screenshot = resized_screenshot.convert('RGB')
            old_resized.close()
            
        # 3. 质量压缩
        resized_screenshot.save(buffered, format="JPEG", quality=60)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        buffered.close()
        resized_screenshot.close()
        screenshot.close()
        
        # --- 视觉模型请求 (Vision) ---
        print("⏳ 正在请求 Vision 模型解析画面...")
        # 【核心新增】：强制加入 20 秒超时熔断机制
        v_client = OpenAI(api_key=VISION_API_KEY, base_url=VISION_BASE_URL, timeout=25.0)
        
        v_start_time = time.time() # 记录 Vision 开始时间
        v_res = v_client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ],
            }],
            max_tokens=VISION_MAX_TOKENS
        )
        v_end_time = time.time() # 记录 Vision 结束时间
        v_cost = v_end_time - v_start_time
        
        description = v_res.choices[0].message.content
        img_b64 = None # 释放巨型字符串
        
        print(f"[视觉识别完毕] 耗时: {v_cost:.2f}s | 画面细节提取 ({len(description)}字)：\n{description}")
        if v_res.usage:
            print(f"📊 [Vision Token消耗] 输入: {v_res.usage.prompt_tokens} | 输出: {v_res.usage.completion_tokens} | 总计: {v_res.usage.total_tokens}")

        # --- 对话模型请求 (Chat) ---
        print("⏳ 正在请求 Chat 模型生成吐槽...")
        # 【核心新增】：强制加入 15 秒超时熔断机制
        c_client = OpenAI(api_key=CHAT_API_KEY, base_url=CHAT_BASE_URL, timeout=15.0)
        system_instruction = f"\n\n[系统强制指令] 用户当前的屏幕画面详细描述如下：\n【{description}】\n请基于上述画面细节，结合你的角色设定，进行回应！"
        final_prompt = CHAT_PROMPT + system_instruction

        c_start_time = time.time() # 记录 Chat 开始时间
        c_res = c_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": final_prompt}],
            max_tokens=CHAT_MAX_TOKENS
        )
        c_end_time = time.time() # 记录 Chat 结束时间
        c_cost = c_end_time - c_start_time
        
        reply = c_res.choices[0].message.content
        
        total_cost = time.time() - global_start_time
        
        print(f"[后端处理完毕] Chat耗时: {c_cost:.2f}s | 总流程耗时: {total_cost:.2f}s | 最终吐槽：{reply}")
        if c_res.usage:
            print(f"📊 [Chat Token消耗]   输入: {c_res.usage.prompt_tokens} | 输出: {c_res.usage.completion_tokens} | 总计: {c_res.usage.total_tokens}")
            
        return {"status": "success", "reply": reply}

    except Exception as e:
        error_str = str(e).lower()
        print(f"[底层报错] 详细捕获信息: {error_str}")
        
        if any(k in error_str for k in ["quota", "insufficient", "balance", "429", "rate limit", "余额", "欠费", "额度"]):
            msg = "API的Token余额不足了（或者被限制频率了）喵。"
        elif any(k in error_str for k in ["connection", "timeout", "network", "connect", "超时", "host", "proxy"]):
            msg = "网络似乎断开了或者请求超时，本喵连不上服务器了喵。或者是API的URL填错了喵？"
        elif any(k in error_str for k in ["unauthorized", "invalid", "api_key", "401", "认证失败", "incorrect"]):
            msg = "API密钥好像填错了，本喵没有权限喵。"
        elif "404" in error_str or "not found" in error_str:
            msg = "找不到指定的模型，URL或者Model名字是不是填错了喵？"
        else:
            msg = "API调用失败了，请检查设置面板喵。"

        return {"status": "error", "message": msg}
        
    finally:
        # 🌟 异常兜底，确保无论成功与否都要打扫战场
        try:
            if buffered and not buffered.closed: buffered.close()
            if resized_screenshot: resized_screenshot.close()
            if screenshot: screenshot.close()
        except:
            pass
            
        # 强制系统立刻执行垃圾回收
        gc.collect()
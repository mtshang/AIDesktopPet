# 文件名：bottom.py
import base64
import io
import os
import json
import shutil
import sys
from PIL import Image, ImageGrab
from openai import OpenAI

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
        print(f"🎭 成功挂载桌宠灵魂与外观：【{PET_LAST}】")
    except Exception as e:
        print(f"⚠️ 解析 {nature_path} 失败: {e}")
else:
    print(f"⚠️ 找不到桌宠配置文件：{nature_path}")

if need_update_config:
    try:
        config_data["API_LAST"] = API_LAST
        config_data["PET_LAST"] = PET_LAST
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4) 
        print(f"📝 自动存档完毕！已更新 config.json")
    except Exception as e:
        print(f"⚠️ 自动存档失败: {e}")

# ==========================================
# 2. 核心 AI 处理接口 (直接供子线程调用)
# ==========================================
# 将这段代码覆盖你 bottom.py 原有的 get_ai_reply 函数

# 将这段代码覆盖你 bottom.py 原有的 get_ai_reply 函数

# 将这段代码覆盖你 bottom.py 原有的 get_ai_reply 函数

def get_ai_reply():
    print("\n[底层引擎] 正在执行截图与大模型分析...")
    try:
        # 1. 抓取原生屏幕截图
        screenshot = ImageGrab.grab()
        
        # 2. 【终极修改：短边对齐 512 像素等比缩放】
        # 无论横屏还是竖屏，永远让最短的一边对齐 512，另一边等比例缩放。
        # 这是多模态大模型切片计费体系下的绝对最优解！
        
        orig_width, orig_height = screenshot.size
        target_min = 512
        
        # 判断哪一边更小
        if orig_width < orig_height:
            # 竖屏情况：宽度更小，把宽度固定为 512
            ratio = target_min / orig_width
            new_width = target_min
            new_height = int(orig_height * ratio)
        else:
            # 横屏情况（最常见）：高度更小，把高度固定为 512
            ratio = target_min / orig_height
            new_height = target_min
            new_width = int(orig_width * ratio)
            
        # 执行高质量等比例缩放
        screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        buffered = io.BytesIO()
        if screenshot.mode == 'RGBA':
            screenshot = screenshot.convert('RGB')
            
        # 3. 质量压缩
        screenshot.save(buffered, format="JPEG", quality=60)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # --- 视觉模型请求 (Vision) ---
        v_client = OpenAI(api_key=VISION_API_KEY, base_url=VISION_BASE_URL)
        v_res = v_client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ],
            }],
            max_tokens=300 
        )
        description = v_res.choices[0].message.content
        
        # 📊 【Vision Token 监控】
        if v_res.usage:
            print(f"📊 [Vision Token消耗] 输入: {v_res.usage.prompt_tokens} | 输出: {v_res.usage.completion_tokens} | 总计: {v_res.usage.total_tokens}")
            
        print(f"[视觉识别完毕] 画面细节提取 ({len(description)}字)：\n{description}")

        # --- 对话模型请求 (Chat) ---
        c_client = OpenAI(api_key=CHAT_API_KEY, base_url=CHAT_BASE_URL)
        c_res = c_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": CHAT_PROMPT + f"\n用户当前的屏幕画面详细描述如下：\n【{description}】\n请基于上述画面细节，进行针对性的吐槽！"}],
            max_tokens=150
        )
        reply = c_res.choices[0].message.content
        
        # 📊 【Chat Token 监控】
        if c_res.usage:
            print(f"📊 [Chat Token消耗]   输入: {c_res.usage.prompt_tokens} | 输出: {c_res.usage.completion_tokens} | 总计: {c_res.usage.total_tokens}")
            
        print(f"[后端处理完毕] 最终吐槽：{reply}")
        
        return {"status": "success", "reply": reply}

    except Exception as e:
        print(f"[底层报错] {e}")
        return {"status": "error", "message": str(e)}
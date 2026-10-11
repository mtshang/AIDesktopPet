# 文件名：bottom.py
import base64
import io
import os
import json
import shutil
import sys
import gc
import threading 
import copy # 🌟 修复隐患 3：引入深拷贝模块
from collections import deque
from PIL import Image, ImageGrab
from openai import OpenAI

from json_write import update_config_atomic

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

current_dir = get_base_path()
config_path = os.path.join(current_dir, "config.json")
modpath_path = os.path.join(current_dir, "modpath.json")
default_config_path = os.path.join(current_dir, "asset", "config_default.json")
default_modpath_path = os.path.join(current_dir, "asset", "modpath_default.json")

if not os.path.exists(config_path) and os.path.exists(default_config_path):
    try: shutil.copy(default_config_path, config_path)
    except: pass

if not os.path.exists(modpath_path) and os.path.exists(default_modpath_path):
    try: shutil.copy(default_modpath_path, modpath_path)
    except: pass

class AppConfig:
    _instance = None
    _singleton_lock = threading.Lock() 

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_vars()
        return cls._instance

    def _init_vars(self):
        self.data_lock = threading.Lock() 
        
        self.api_last = ""
        self.pet_last = "default_pet"
        self.recent_history = deque(maxlen=3) 
        
        self.vision_api_key = ""
        self.vision_base_url = ""
        self.vision_model = ""
        self.chat_api_key = ""
        self.chat_base_url = ""
        self.chat_model = ""
        
        self.vision_prompt = ""
        self.chat_prompt = ""
        self.chat_examples = [] 
        self.vision_max_tokens = 300 
        self.chat_max_tokens = 300 
        
        self.hello_hk_msg = "主人好喵！按下快捷键我就会吐槽你哦~"
        self.hello_msg = "主人好喵！"
        self.peek_msg = "让我来看看"
        self.peekagain_msg = "本猫还在思考啦喵！"
        self.error_head_msg = "呜呜，引擎报错了喵："
        self._nature_defaults = {
            "vision_prompt": copy.deepcopy(self.vision_prompt),
            "chat_prompt": copy.deepcopy(self.chat_prompt),
            "chat_example": copy.deepcopy(self.chat_examples),
            "vision_max_tokens": copy.deepcopy(self.vision_max_tokens),
            "chat_max_tokens": copy.deepcopy(self.chat_max_tokens),
            "hello_hk_msg": copy.deepcopy(self.hello_hk_msg),
            "hello_msg": copy.deepcopy(self.hello_msg),
            "peek_msg": copy.deepcopy(self.peek_msg),
            "peekagain_msg": copy.deepcopy(self.peekagain_msg),
            "error_head_msg": copy.deepcopy(self.error_head_msg),
        }

    def init_load(self):
        self.reload_api_config()
        self.reload_nature_config()

    def reload_api_config(self):
        api_last = ""
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    api_last = json.load(f).get("API_LAST", "")
            except: pass

        api_folder = os.path.join(current_dir, "api")
        all_apis = {}
        if os.path.exists(api_folder):
            for filename in os.listdir(api_folder):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(api_folder, filename), 'r', encoding='utf-8') as f:
                            record = json.load(f)
                            if isinstance(record, dict):
                                all_apis[os.path.splitext(filename)[0]] = record
                    except: pass

        need_update_config = False
        if all_apis:
            if api_last and api_last in all_apis:
                active_api_key = api_last
            else:
                active_api_key = list(all_apis.keys())[0]
                api_last = active_api_key
                need_update_config = True

            active_config = all_apis[active_api_key]

            with self.data_lock:
                self.api_last = api_last
                self.vision_api_key = active_config.get("VISION_API_KEY", "")
                self.vision_base_url = active_config.get("VISION_BASE_URL", "")
                self.vision_model = active_config.get("VISION_MODEL", "")
                self.chat_api_key = active_config.get("CHAT_API_KEY", "")
                self.chat_base_url = active_config.get("CHAT_BASE_URL", "")
                self.chat_model = active_config.get("CHAT_MODEL", "")

            if need_update_config:
                update_config_atomic(config_path, {"API_LAST": api_last})
        else:
            with self.data_lock:
                self.api_last = ""
                self.vision_api_key = self.vision_base_url = self.vision_model = ""
                self.chat_api_key = self.chat_base_url = self.chat_model = ""
            if api_last:
                update_config_atomic(config_path, {"API_LAST": ""})

    # 🌟 修复隐患 2：提供直接修改内存的接口，避免冗余磁盘读取
    def set_active_api(self, api_name):
        """直接在内存中切换 API 配置，无需重新读取 config.json"""
        api_file = os.path.join(current_dir, "api", f"{api_name}.json")
        if os.path.exists(api_file):
            try:
                with open(api_file, 'r', encoding='utf-8') as f:
                    api_config = json.load(f)
                with self.data_lock:
                    self.api_last = api_name
                    self.vision_api_key = api_config.get("VISION_API_KEY", "")
                    self.vision_base_url = api_config.get("VISION_BASE_URL", "")
                    self.vision_model = api_config.get("VISION_MODEL", "")
                    self.chat_api_key = api_config.get("CHAT_API_KEY", "")
                    self.chat_base_url = api_config.get("CHAT_BASE_URL", "")
                    self.chat_model = api_config.get("CHAT_MODEL", "")
            except Exception as e:
                print(f"切换 API 内存失败: {e}")

    def reload_nature_config(self):
        pet_last = "default_pet"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    pet_last = json.load(f).get("PET_LAST", "default_pet")
            except: pass

        path_petmod = os.path.join(current_dir, "petmod", pet_last)
        path_asset = os.path.join(current_dir, "asset", "pet", pet_last)
        nature_path = os.path.join(path_petmod if os.path.exists(path_petmod) else path_asset if os.path.exists(path_asset) else os.path.join(current_dir, "asset", "pet", "default_pet"), "nature.json")

        if os.path.exists(nature_path):
            try:
                with open(nature_path, 'r', encoding='utf-8') as f:
                    nature = json.load(f)
                
                with self.data_lock:
                    self.pet_last = pet_last
                    self.vision_prompt = copy.deepcopy(nature.get("vision_prompt", self._nature_defaults["vision_prompt"]))
                    self.chat_prompt = copy.deepcopy(nature.get("chat_prompt", self._nature_defaults["chat_prompt"]))
                    self.chat_examples = copy.deepcopy(nature.get("chat_example", self._nature_defaults["chat_example"]))
                    self.vision_max_tokens = copy.deepcopy(nature.get("vision_max_tokens", self._nature_defaults["vision_max_tokens"]))
                    self.chat_max_tokens = copy.deepcopy(nature.get("chat_max_tokens", self._nature_defaults["chat_max_tokens"]))
                    self.hello_hk_msg = copy.deepcopy(nature.get("hello_hk_msg", self._nature_defaults["hello_hk_msg"]))
                    self.hello_msg = copy.deepcopy(nature.get("hello_msg", self._nature_defaults["hello_msg"]))
                    self.peek_msg = copy.deepcopy(nature.get("peek_msg", self._nature_defaults["peek_msg"]))
                    self.peekagain_msg = copy.deepcopy(nature.get("peekagain_msg", self._nature_defaults["peekagain_msg"]))
                    self.error_head_msg = copy.deepcopy(nature.get("error_head_msg", self._nature_defaults["error_head_msg"]))
            except: pass

    def get_ai_payload(self):
        with self.data_lock:
            return {
                "v_key": self.vision_api_key,
                "v_url": self.vision_base_url,
                "v_model": self.vision_model,
                "c_key": self.chat_api_key,
                "c_url": self.chat_base_url,
                "c_model": self.chat_model,
                "v_prompt": self.vision_prompt,
                "c_prompt": self.chat_prompt,
                # 🌟 修复隐患 3：使用 deepcopy 彻底斩断内存引用，防止外部污染
                "c_examples": copy.deepcopy(self.chat_examples), 
                "v_tokens": self.vision_max_tokens,
                "c_tokens": self.chat_max_tokens
            }

    def get_ui_msgs(self):
        with self.data_lock:
            return {
                "hello_hk_msg": self.hello_hk_msg,
                "hello_msg": self.hello_msg,
                "peek_msg": self.peek_msg,
                "peekagain_msg": self.peekagain_msg,
                "error_head_msg": self.error_head_msg
            }
            
    def get_history(self):
        with self.data_lock:
            return list(self.recent_history)
            
    def add_history(self, text):
        with self.data_lock:
            self.recent_history.append(text)

global_config = AppConfig()
global_config.init_load()

def get_screen_b64():
    screenshot = resized_screenshot = buffered = None
    try:
        screenshot = ImageGrab.grab()
        orig_width, orig_height = screenshot.size
        target_min = 512
        ratio = target_min / orig_width if orig_width < orig_height else target_min / orig_height
        new_width, new_height = int(orig_width * ratio) if orig_width >= orig_height else target_min, int(orig_height * ratio) if orig_width < orig_height else target_min
            
        resized_screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        if resized_screenshot.mode == 'RGBA':
            old_resized = resized_screenshot
            resized_screenshot = resized_screenshot.convert('RGB')
            old_resized.close()
            
        resized_screenshot.save(buffered, format="JPEG", quality=60)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except: return None
    finally:
        try:
            if buffered and not buffered.closed: buffered.close()
            if resized_screenshot: resized_screenshot.close()
            if screenshot: screenshot.close()
        except: pass
        gc.collect()

def get_ai_reply(img_b64):
    if not img_b64:
        return {"status": "error", "message": "本猫刚才没看清屏幕（截图失败），请重试喵。"}
    payload = global_config.get_ai_payload()
    try:
        with OpenAI(api_key=payload['v_key'], base_url=payload['v_url'], timeout=25.0) as client:
            response = client.chat.completions.create(
                model=payload['v_model'],
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": payload['v_prompt']},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ]}],
                max_tokens=payload['v_tokens'],
            )
        description = response.choices[0].message.content if response.choices else None
        if not isinstance(description, str) or not description.strip():
            raise ValueError("视觉模型没有返回可用的屏幕描述")

        # The user's persona is the system instruction, with no hard-coded rewrite.
        messages = [{"role": "system", "content": payload['c_prompt']}]
        if payload['c_examples']:
            examples = "\n".join(str(item) for item in payload['c_examples'])
            messages.append({"role": "system", "content": "角色参考语录：\n" + examples})
        history = global_config.get_history()
        if history:
            messages.append({"role": "assistant", "content": "\n".join(history)})
        messages.append({"role": "user", "content": description})
        with OpenAI(api_key=payload['c_key'], base_url=payload['c_url'], timeout=20.0) as client:
            response = client.chat.completions.create(
                model=payload['c_model'], messages=messages, max_tokens=payload['c_tokens'],
            )
        reply = response.choices[0].message.content if response.choices else None
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("对话模型没有返回文本，请检查模型配置和 Token 上限")
        reply = reply.strip()
        global_config.add_history(reply)
        return {"status": "success", "reply": reply}

    except Exception as e:
        error_str = str(e).lower()
        if any(k in error_str for k in ["quota", "insufficient", "balance", "429", "rate limit", "余额", "欠费", "额度"]):
            msg = "API的Token余额不足了（或者被限制频率了）。"
        elif any(k in error_str for k in ["connection", "timeout", "network", "connect", "超时", "host", "proxy"]):
            msg = "网络似乎断开了或者请求超时，软件连不上服务器了。"
        elif any(k in error_str for k in ["unauthorized", "invalid", "api_key", "401", "认证失败"]):
            msg = "API密钥好像填错了，软件没有权限。"
        elif "404" in error_str or "not found" in error_str:
            msg = "找不到指定的模型，URL或者Model名字是不是填错了？"
        else:
            msg = f"API调用失败了: {e}"
        return {"status": "error", "message": msg}
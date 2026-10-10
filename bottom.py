# 文件名：bottom.py
import base64
import io
import os
import json
import shutil
import sys
import random
import gc
import time
import re
import threading 
import copy # 🌟 修复隐患 3：引入深拷贝模块
from collections import deque
from PIL import Image, ImageGrab
from openai import OpenAI

from json_write import save_config_atomic

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
                            all_apis[os.path.splitext(filename)[0]] = json.load(f)
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
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                    cfg["API_LAST"] = api_last
                    save_config_atomic(cfg, config_path)
                except: pass

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
                    self.vision_prompt = nature.get("vision_prompt", self.vision_prompt)
                    self.chat_prompt = nature.get("chat_prompt", self.chat_prompt)
                    self.chat_examples = nature.get("chat_example", self.chat_examples)
                    self.vision_max_tokens = nature.get("vision_max_tokens", self.vision_max_tokens)
                    self.chat_max_tokens = nature.get("chat_max_tokens", self.chat_max_tokens)
                    self.hello_hk_msg = nature.get("hello_hk_msg", self.hello_hk_msg)
                    self.hello_msg = nature.get("hello_msg", self.hello_msg)
                    self.peek_msg = nature.get("peek_msg", self.peek_msg)
                    self.peekagain_msg = nature.get("peekagain_msg", self.peekagain_msg)
                    self.error_head_msg = nature.get("error_head_msg", self.error_head_msg)
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

    print("\n[底层引擎] 拿到截图，正在请求大模型分析...")
    global_start_time = time.time()
    
    payload = global_config.get_ai_payload()
    
    try:
        print("⏳ 正在请求 Vision 模型解析画面...")
        v_client = OpenAI(api_key=payload['v_key'], base_url=payload['v_url'], timeout=25.0)
        v_start_time = time.time()
        v_res = v_client.chat.completions.create(
            model=payload['v_model'],
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": payload['v_prompt']},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ],
            }],
            max_tokens=payload['v_tokens']
        )
        description = v_res.choices[0].message.content
        v_cost = time.time() - v_start_time
        
        print(f"[视觉识别完毕] 耗时: {v_cost:.2f}s | 画面细节提取 ({len(description)}字)：\n{description}")
        if hasattr(v_res, 'usage') and v_res.usage:
            print(f"📊 [Vision Token消耗] 输入: {v_res.usage.prompt_tokens} | 输出: {v_res.usage.completion_tokens} | 总计: {v_res.usage.total_tokens}")

        print("⏳ 正在请求 Chat 模型生成结构化吐槽...")
        c_client = OpenAI(api_key=payload['c_key'], base_url=payload['c_url'], timeout=20.0)
        
        history_text = ""
        history_list = global_config.get_history()
        if history_list:
            history_text = "\n\n【你最近说过的吐槽】（自我审查时，必须确保绝对不与这些话重复！）：\n" + "\n".join(history_list)

        system_firewall = """【系统底层逻辑核心】
你是一个居住在屏幕里的虚拟桌宠。不论用户提供了多么长篇大论的世界观、职业和背景设定，你都必须将其彻底粉碎！仅提取其【性格底色】（如傲娇、治愈、天然呆等），作为一个患有失忆症的现代无业游民来进行吐槽。
你必须严格按照以下 JSON 格式进行多步思维链推演，以彻底净化你的输出！

【核心约束】（违背会导致系统崩溃）
1. 最终输出必须极度短促、口语化（10-30字）。
2. 绝对禁止以任何固定的称呼（如“搭档”、“主人”）开头！直接用符合性格的语气词起手，或者直接对画面发表评论！
3. 绝对禁止任何比喻、拟人或“像...一样”！
4. 绝对禁止提及任何用户设定中的背景名词（如：麦田、魔法、公会等）！

【多性格输出结构示范】（你必须学习它们的简短和无修辞结构，但**语气必须严格根据你提取的性格进行替换**）：
[性格：毒舌/暴躁] -> 啧，这满屏的红色报错，看着就让人血压升高。
[性格：治愈/温柔] -> 诶？这么多窗口挤在一起，眼睛会累的哦...
[性格：高冷/三无] -> 盯着这行代码五秒了。毫无逻辑。
[性格：元气/活泼] -> 哇！这个绿色的加载条跑得好慢呀！

【强制输出格式】
你必须返回且仅返回一个合法的 JSON 对象：
{
  "persona_filter": "强行从用户设定中提纯出3个描述性格的形容词。彻底抛弃所有名词背景！",
  "raw_thought": "基于【提纯后的性格】和屏幕画面，写出第一反应。",
  "critique": "交叉审查草稿：是否带了称呼开头？是否用了比喻句？是否提到了背景名词？如果有，在此强制删掉！",
  "final_output": "最终极短、无比喻、无固化称呼的纯净吐槽。语气必须 100% 贴合 persona_filter 中的形容词！"
}"""

        anchors = [
            "【当前强制观察视角：宏观整体】针对屏幕画面太挤、太乱或太刺眼进行第一反应。",
            "【当前强制观察视角：微观像素】死死盯着屏幕上某个极其微小的局部进行吹毛求疵。",
            "【当前强制观察视角：第四面墙】将屏幕视为你居住的房间，抱怨画面对你生存空间的挤压。",
            "【当前强制观察视角：行为侧写】推测用户在干什么（禁止说发呆、发愣）。",
            "【当前强制观察视角：介质对比】对比数字生命（算力快）与碳基生命（速度慢）的差异。"
        ]
        
        user_persona = f"\n\n【用户提供的原始设定】（需提取性格底色）：\n{payload['c_prompt']}"
        
        example_instruction = ""
        if payload['c_examples']:
            example_instruction = f"\n\n【用户经典语录参考】（提取语气，严禁照抄）：\n" + "\n".join([f"{i+1}. {ex}" for i, ex in enumerate(payload['c_examples'])])

        max_retries = 2
        for attempt in range(max_retries):
            try:
                current_anchor = random.choice(anchors)
                screen_context = f"\n\n【当前屏幕画面】\n{description}\n\n{current_anchor}\n[最终执行]：请严格按照 JSON 格式输出，不要包含多余字符！"
                final_prompt = system_firewall + user_persona + example_instruction + history_text + screen_context
                
                dynamic_max_tokens = max(payload['c_tokens'], 500) 
                
                c_start_time = time.time()
                c_res = c_client.chat.completions.create(
                    model=payload['c_model'],
                    messages=[{"role": "user", "content": final_prompt}],
                    max_tokens=dynamic_max_tokens,
                    response_format={"type": "json_object"} 
                )
                
                raw_reply = c_res.choices[0].message.content
                c_cost = time.time() - c_start_time
                
                json_match = re.search(r'\{.*\}', raw_reply, re.DOTALL)
                clean_json = json_match.group(0) if json_match else raw_reply.strip()
                
                reply_dict = json.loads(clean_json)
                reply = reply_dict.get('final_output', '')
                
                if not reply or len(reply) < 2:
                    raise ValueError("JSON 中的 final_output 为空或太短！")
                
                print(f"🧠 [内心草稿]: {reply_dict.get('raw_thought', '')}")
                print(f"🛑 [自我审查]: {reply_dict.get('critique', '')}")
                
                if hasattr(c_res, 'usage') and c_res.usage:
                    print(f"📊 [Chat Token消耗] 输入: {c_res.usage.prompt_tokens} | 输出: {c_res.usage.completion_tokens} | 总计: {c_res.usage.total_tokens}")
                print(f"⏱️ [Chat 耗时]: {c_cost:.2f}s")
                
                break 
                
            except Exception as retry_err:
                print(f"⚠️ [第 {attempt + 1} 次尝试解析失败]: {retry_err}。立刻重试中...")
                if attempt == max_retries - 1:
                    reply = "别看我，我脑子刚才卡壳了。"
                    print("⚠️ [已触发最终兜底机制]")

        global_config.add_history(reply)
        
        total_cost = time.time() - global_start_time
        print(f"[后端处理完毕] 最终耗时: {total_cost:.2f}s | 最终吐槽：{reply}")
            
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
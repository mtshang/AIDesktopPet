from worker_lifecycle import start_worker, is_shutting_down
# 文件名：set_mod.py
import os
import sys
import json
import shutil
import re
import uuid
import copy  # 🌟 引入 copy 模块用于深度拷贝
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QLineEdit, QComboBox, QTabWidget, 
                               QScrollArea, QFileDialog, QMessageBox, QFrame, 
                               QSpinBox, QDoubleSpinBox, QTextEdit, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, Signal, QSize, QThread
from json_write import save_config_atomic, update_config_atomic, validate_config_name
from mod_storage import checked_mod_path, image_relative_path, save_mod

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# ==========================================
# 🌟 全局默认配置模板 & 自动愈合机制
# ==========================================
DEFAULT_NATURE_TEMPLATE = {
    "name": "桌宠配置",
    "vision_prompt": "你是一个无情的屏幕观察助手。请仔细观察用户的屏幕截图，用极度客观的语言描述这张截图，绝对不要提及图片的画质、分辨率或模糊问题，只描述你能看清的内容！：1. 屏幕中央在运行什么软件/游戏/代码？2. 画面中有哪些具体的文字、弹窗或其他细节？3. 猜测用户当前正在做什么？（第3条30字以内）必须客观、详尽，字数控制在150字左右。",
    "vision_max_tokens": 150,
    "chat_prompt": "你现在是一只傲娇的二次元猫娘桌宠。用一句话吐槽用户当前的行为。态度可以适当可爱，句末必须带‘喵’。",
    "chat_example": [], 
    "chat_max_tokens": 150,
    "hello_hk_msg": "主人好喵！按下快捷键我就会吐槽你哦~", 
    "hello_msg": "主人好喵！", 
    "peek_msg": "让我来看看", 
    "peekagain_msg": "本猫还在思考啦喵！", 
    "error_head_msg": "呜呜，引擎报错了喵：", 
    "scale": 1.0,
    "default_image": "",
    "have_standing": False, "standing_mode": "static",
    "have_thinking": False, "thinking_mode": "static",
    "have_draging": False,  "draging_mode": "static",
    "have_error": False,    "error_mode": "static",
    "file": {
        "standing": { "image": "", "frame": [], "frame_time": [], "css_sprites": "", "css_sprite_time": 100, "css_row": 1, "css_col": 1 },
        "thinking": { "image": "", "frame": [], "frame_time": [], "css_sprites": "", "css_sprite_time": 100, "css_row": 1, "css_col": 1 },
        "draging":  { "image": "", "frame": [], "frame_time": [], "css_sprites": "", "css_sprite_time": 100, "css_row": 1, "css_col": 1 },
        "error":    { "image": "", "frame": [], "frame_time": [], "css_sprites": "", "css_sprite_time": 100, "css_row": 1, "css_col": 1 }
    },
    "can_write": True
}

def auto_heal_config(old_data, default_template):
    """
    🌟 核心黑科技：递归字典修补器
    对比老数据和标准模板，把老配置里没有的字段自动用默认值补全。
    """
    for key, default_value in default_template.items():
        if key not in old_data:
            old_data[key] = copy.deepcopy(default_value)
        elif isinstance(default_value, dict) and isinstance(old_data[key], dict):
            auto_heal_config(old_data[key], default_value)
    return old_data

# ==========================================
# 线程与后台处理
# ==========================================
class CopyWorker(QThread):
    finished_signal = Signal(bool, str, str, str, str)

    def __init__(self, src, dest, action_type, filename):
        super().__init__()
        self.src = src
        self.dest = dest
        self.action_type = action_type
        self.filename = filename

    def run(self):
        try:
            if os.path.exists(self.dest):
                if os.path.samefile(self.src, self.dest):
                    self.finished_signal.emit(True, "", self.dest, self.action_type, self.filename)
                    return
                stem, suffix = os.path.splitext(self.dest)
                # Never overwrite the image still referenced by the saved config.
                self.dest = f"{stem}_{uuid.uuid4().hex}{suffix}"
                self.filename = os.path.basename(self.dest)
            shutil.copy2(self.src, self.dest)
            self.finished_signal.emit(True, "", self.dest, self.action_type, self.filename)
        except Exception as exc:
            self.finished_signal.emit(False, str(exc), self.dest, self.action_type, self.filename)

class SaveWorker(QThread):
    finished_signal = Signal(bool, str, str)

    def __init__(self, old_path, new_path, nature_data, base_dir, new_folder_name,
                 config_path=None, pending_removals=()):
        super().__init__()
        self.old_path = old_path
        self.new_path = new_path
        self.nature_data = copy.deepcopy(nature_data)
        self.base_dir = base_dir
        self.new_folder_name = new_folder_name
        self.config_path = config_path
        self.pending_removals = set(pending_removals)

    def run(self):
        try:
            warning = save_mod(self.old_path, self.new_path, self.nature_data,
                               self.base_dir, self.config_path, self.pending_removals)
            self.finished_signal.emit(True, warning, self.new_folder_name)
        except Exception as exc:
            self.finished_signal.emit(False, str(exc), "")


class DeleteWorker(QThread):
    finished_signal = Signal(bool, str, str)

    def __init__(self, target_dir, base_dir, config_path):
        super().__init__()
        self.target_dir = target_dir
        self.base_dir = base_dir
        self.config_path = config_path

    def run(self):
        fallback = ""
        try:
            target = checked_mod_path(self.base_dir, self.target_dir)
            folder = os.path.basename(target)
            if folder == "default_pet":
                raise ValueError("不能删除默认角色。")
            def select_default(config):
                nonlocal fallback
                if config.get("PET_LAST") == folder:
                    config["PET_LAST"] = "default_pet"
                    fallback = "default_pet"
            # A failed config write must leave the character directory intact.
            try:
                update_config_atomic(self.config_path, select_default)
            except Exception:
                fallback = ""
                raise
            shutil.rmtree(target)
            self.finished_signal.emit(True, "", fallback)
        except Exception as exc:
            self.finished_signal.emit(False, str(exc), fallback)

class ApplyWorker(QThread):
    finished_signal = Signal(bool, str, str)

    def __init__(self, config_path, current_mod_folder):
        super().__init__()
        self.config_path = config_path
        self.current_mod_folder = current_mod_folder

    def run(self):
        try:
            update_config_atomic(self.config_path, {"PET_LAST": self.current_mod_folder})
            self.finished_signal.emit(True, "", self.current_mod_folder)
        except Exception as e:
            self.finished_signal.emit(False, str(e), "")

class CreateWorker(QThread):
    finished_signal = Signal(bool, str, str)

    def __init__(self, new_path, state_keys, default_nature, new_folder):
        super().__init__()
        self.new_path = new_path
        self.state_keys = state_keys
        self.default_nature = default_nature
        self.new_folder = new_folder

    def run(self):
        try:
            os.makedirs(self.new_path)
            for state_name in self.state_keys:
                os.makedirs(os.path.join(self.new_path, state_name), exist_ok=True)
            save_config_atomic(self.default_nature, os.path.join(self.new_path, "nature.json"))
            self.finished_signal.emit(True, "", self.new_folder)
        except Exception as e:
            self.finished_signal.emit(False, str(e), "")

class ModPage(QWidget):
    mod_applied_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.current_dir = get_base_path()
        self.asset_dir = os.path.join(self.current_dir, "asset", "pet")
        self.petmod_dir = os.path.join(self.current_dir, "petmod")
        if not os.path.exists(self.petmod_dir):
            try: os.makedirs(self.petmod_dir)
            except: pass
            
        self.config_path = os.path.join(self.current_dir, "config.json")
        
        self.current_mod_folder = ""
        self.current_base_dir = self.asset_dir
        self.current_nature = {}
        self.pending_image_removals = set()
        self.current_frame_index = 0
        
        self.state_keys = ["standing", "thinking", "draging", "error"]
        self.current_state_key = "standing"

        self.init_ui()
        self.refresh_mod_list()

    def init_ui(self):
        self.setStyleSheet("font-family: 'HarmonyOS Sans SC';")
        
        main_layout = QVBoxLayout()
        
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("当前桌宠配置："))
        
        self.mod_combo = QComboBox()
        self.mod_combo.currentIndexChanged.connect(self.on_mod_combo_changed)
        top_layout.addWidget(self.mod_combo)
        
        self.btn_apply = QPushButton("🌟 启用该配置")
        self.btn_apply.clicked.connect(self.apply_current_mod)
        self.btn_del = QPushButton("🗑️ 删除该配置")
        self.btn_del.clicked.connect(self.delete_current_mod)
        self.btn_new = QPushButton("➕ 新建配置")
        self.btn_new.clicked.connect(self.create_new_mod)
        
        top_layout.addWidget(self.btn_apply)
        top_layout.addWidget(self.btn_del)
        top_layout.addWidget(self.btn_new)
        main_layout.addLayout(top_layout)
        
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("配置文件夹名称："))
        self.mod_folder_input = QLineEdit()
        self.mod_folder_input.setPlaceholderText("请输入合法的文件夹名称")
        folder_layout.addWidget(self.mod_folder_input)
        main_layout.addLayout(folder_layout)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("桌宠名称："))
        self.mod_name_input = QLineEdit()
        self.mod_name_input.setPlaceholderText("请输入桌宠的显示名称")
        name_layout.addWidget(self.mod_name_input)
        main_layout.addLayout(name_layout)
        
        self.tabs = QTabWidget()
        
        self.tab_appearance = QWidget()
        self.setup_appearance_tab()
        self.tabs.addTab(self.tab_appearance, "🎨 形象设置")
        
        self.tab_persona = QWidget()
        self.setup_persona_tab()
        self.tabs.addTab(self.tab_persona, "🧠 人格设置")
        
        self.tab_phrases = QWidget()
        self.setup_phrases_tab()
        self.tabs.addTab(self.tab_phrases, "💬 固定语句替换")
        
        main_layout.addWidget(self.tabs)
        
        self.btn_save = QPushButton("💾 更改该桌宠配置")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setStyleSheet("font-family: 'HarmonyOS Sans SC'; background-color: #ffb6c1; color: white; font-weight: bold; font-size: 14px; border-radius: 5px;")
        self.btn_save.clicked.connect(self.save_current_mod)
        main_layout.addWidget(self.btn_save)
        
        self.setLayout(main_layout)

    def setup_appearance_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("形象缩放："))
        self.scale_input = QDoubleSpinBox()
        self.scale_input.setDecimals(1)
        self.scale_input.setSingleStep(0.1)
        self.scale_input.setRange(0.1, 5.0)
        scale_layout.addWidget(self.scale_input)
        
        lbl_scale_warn = QLabel(" 注意！此处无视禁止修改！可以结合自身情况修改！")
        lbl_scale_warn.setStyleSheet("font-family: 'HarmonyOS Sans SC'; color: red; font-size: 12px; font-style: italic;")
        scale_layout.addWidget(lbl_scale_warn)
        
        scale_layout.addStretch()
        
        self.btn_save_scale = QPushButton("💾 保存缩放")
        self.btn_save_scale.clicked.connect(self.save_current_mod)
        scale_layout.addWidget(self.btn_save_scale)
        
        layout.addLayout(scale_layout)

        layout.addWidget(QLabel("<b>静态立绘：</b>"))
        default_img_layout = QHBoxLayout()
        self.default_img_display = QLineEdit()
        self.default_img_display.setReadOnly(True)
        default_img_layout.addWidget(self.default_img_display)
        
        self.btn_add_default_img = QPushButton("添加/替换图片")
        self.btn_add_default_img.clicked.connect(lambda: self.add_or_replace_image("default"))
        default_img_layout.addWidget(self.btn_add_default_img)
        layout.addLayout(default_img_layout)
        
        hint_label = QLabel("<i>至少要添加一张静态立绘！</i>")
        hint_label.setStyleSheet("font-family: 'HarmonyOS Sans SC'; color: gray;")
        layout.addWidget(hint_label)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        state_layout = QHBoxLayout()
        state_layout.addWidget(QLabel("<b>编辑状态：</b>"))
        self.state_combo = QComboBox()
        self.state_combo.addItems(["站立状态", "窥屏状态", "拖拽状态", "报错状态"])
        self.state_combo.currentIndexChanged.connect(self.on_state_combo_changed)
        state_layout.addWidget(self.state_combo)
        state_layout.addStretch()
        layout.addLayout(state_layout)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("<b>动画模式：</b>"))
        self.anim_mode_combo = QComboBox()
        self.anim_mode_combo.addItems(["静态立绘", "图片序列帧动画", "CSS雪碧图动画"])
        self.anim_mode_combo.currentIndexChanged.connect(self.on_anim_mode_changed)
        mode_layout.addWidget(self.anim_mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        self.dynamic_widget = QWidget()
        self.dynamic_layout = QVBoxLayout()
        self.dynamic_layout.setContentsMargins(0, 0, 0, 0)
        self.dynamic_widget.setLayout(self.dynamic_layout)
        layout.addWidget(self.dynamic_widget)
        
        self.file_display_layout = QHBoxLayout()
        self.lbl_frame_index = QLabel("第 1 张")
        self.file_display_layout.addWidget(self.lbl_frame_index)
        self.file_display_layout.addWidget(QLabel("图片文件名："))
        
        self.standing_img_display = QComboBox() 
        self.file_display_layout.addWidget(self.standing_img_display)
        
        self.btn_layout = QHBoxLayout()
        self.btn_stand_add_replace = QPushButton("添加/替换图片")
        self.btn_stand_add = QPushButton("添加图片")
        self.btn_stand_replace = QPushButton("替换图片")
        self.btn_stand_del = QPushButton("删除图片")
        
        self.btn_stand_add_replace.clicked.connect(lambda: self.add_or_replace_image("static_css"))
        self.btn_stand_add.clicked.connect(lambda: self.add_or_replace_image("seq_add"))
        self.btn_stand_replace.clicked.connect(lambda: self.add_or_replace_image("seq_replace"))
        self.btn_stand_del.clicked.connect(self.delete_state_image)
        
        self.btn_layout.addWidget(self.btn_stand_add_replace)
        self.btn_layout.addWidget(self.btn_stand_add)
        self.btn_layout.addWidget(self.btn_stand_replace)
        self.btn_layout.addWidget(self.btn_stand_del)
        
        self.param_layout = QHBoxLayout()
        self.lbl_time = QLabel("图片持续时间：")
        self.time_input = QSpinBox()
        self.time_input.setRange(10, 10000)
        self.lbl_ms = QLabel("毫秒(ms)")
        
        self.lbl_css_row = QLabel("行数：")
        self.row_input = QSpinBox()
        self.row_input.setRange(1, 100)
        self.lbl_css_col = QLabel("列数：")
        self.col_input = QSpinBox()
        self.col_input.setRange(1, 100)
        
        self.param_layout.addWidget(self.lbl_time)
        self.param_layout.addWidget(self.time_input)
        self.param_layout.addWidget(self.lbl_ms)
        self.param_layout.addWidget(self.lbl_css_row)
        self.param_layout.addWidget(self.row_input)
        self.param_layout.addWidget(self.lbl_css_col)
        self.param_layout.addWidget(self.col_input)
        self.param_layout.addStretch()

        self.dynamic_layout.addLayout(self.file_display_layout)
        self.dynamic_layout.addLayout(self.btn_layout)
        self.dynamic_layout.addLayout(self.param_layout)

        layout.addStretch()
        container.setLayout(layout)
        scroll.setWidget(container)
        
        tab_layout = QVBoxLayout()
        tab_layout.addWidget(scroll)
        self.tab_appearance.setLayout(tab_layout)

    def setup_persona_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)

        lbl_chat_title = QLabel("<b>💬 吐槽模型 (Chat API)</b> - 用于生成对话")
        lbl_chat_title.setStyleSheet("font-family: 'HarmonyOS Sans SC'; font-size: 14px; color: #ff69b4;")
        layout.addWidget(lbl_chat_title)

        layout.addWidget(QLabel("模型提示词："))
        self.chat_prompt_input = QTextEdit()
        self.chat_prompt_input.setMinimumHeight(80)
        layout.addWidget(self.chat_prompt_input)

        lbl_chat_example = QLabel("示例：你现在是一只傲娇的二次元猫娘桌宠。用一句话吐槽用户当前的行为。态度可以适当可爱，句末必须带‘喵’。")
        lbl_chat_example.setStyleSheet("font-family: 'HarmonyOS Sans SC'; color: gray; font-size: 12px;")
        lbl_chat_example.setWordWrap(True)
        lbl_chat_example.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(lbl_chat_example)

        chat_token_layout = QHBoxLayout()
        chat_token_layout.addWidget(QLabel("最大Token："))
        self.chat_token_input = QSpinBox()
        self.chat_token_input.setRange(10, 4096)
        chat_token_layout.addWidget(self.chat_token_input)
        chat_token_layout.addStretch()
        layout.addLayout(chat_token_layout)

        lbl_chat_warn = QLabel("<i>注意！如果不认识请勿修改此内容！</i>")
        lbl_chat_warn.setStyleSheet("font-family: 'HarmonyOS Sans SC'; color: red; font-size: 12px;")
        layout.addWidget(lbl_chat_warn)

        line_ex = QFrame()
        line_ex.setFrameShape(QFrame.HLine)
        line_ex.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line_ex)

        lbl_ex_title = QLabel("<b>✨ 灵魂注入 (经典语录)</b>")
        lbl_ex_title.setStyleSheet("font-family: 'HarmonyOS Sans SC'; font-size: 14px; color: #9370db;")
        layout.addWidget(lbl_ex_title)
        
        lbl_ex_desc = QLabel("输入几句角色的经典台词，让 AI 完美模仿她的语气喵！(选填)")
        lbl_ex_desc.setStyleSheet("font-family: 'HarmonyOS Sans SC'; color: gray; font-size: 12px;")
        layout.addWidget(lbl_ex_desc)

        self.ex_list_widget = QListWidget()
        self.ex_list_widget.setMaximumHeight(150)
        self.ex_list_widget.setSelectionMode(QListWidget.NoSelection) 
        self.ex_list_widget.setStyleSheet("""
            QListWidget { font-family: 'HarmonyOS Sans SC'; border: 1px solid #d3d3d3; border-radius: 5px; background-color: #fafafa; padding: 5px; }
            QListWidget::item { margin-bottom: 5px; }
        """)
        layout.addWidget(self.ex_list_widget)

        ex_ctrl_layout = QHBoxLayout()
        self.ex_input = QLineEdit()
        self.ex_input.setPlaceholderText("输入一句台词，按回车或点添加...")
        self.ex_input.setMinimumHeight(30)
        self.btn_add_ex = QPushButton("➕ 添加语录")
        self.btn_add_ex.setMinimumHeight(30)
        self.btn_add_ex.setStyleSheet("font-family: 'HarmonyOS Sans SC'; background-color: #87cefa; color: white; border-radius: 4px; padding: 0 15px;")
        
        ex_ctrl_layout.addWidget(self.ex_input)
        ex_ctrl_layout.addWidget(self.btn_add_ex)
        layout.addLayout(ex_ctrl_layout)

        self.btn_add_ex.clicked.connect(self.add_example_item)
        self.ex_input.returnPressed.connect(self.add_example_item)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        lbl_vision_title = QLabel("<b>👁️ 视觉模型 (Vision API)</b> - 用于看屏幕")
        lbl_vision_title.setStyleSheet("font-family: 'HarmonyOS Sans SC'; font-size: 14px; color: #4682b4;")
        layout.addWidget(lbl_vision_title)

        layout.addWidget(QLabel("模型提示词："))
        self.vision_prompt_input = QTextEdit()
        self.vision_prompt_input.setMinimumHeight(80)
        layout.addWidget(self.vision_prompt_input)

        lbl_vision_warn1 = QLabel("<i>注意！如果不认识请勿修改此内容！</i>")
        lbl_vision_warn1.setStyleSheet("font-family: 'HarmonyOS Sans SC'; color: red; font-size: 12px;")
        layout.addWidget(lbl_vision_warn1)

        vision_token_layout = QHBoxLayout()
        vision_token_layout.addWidget(QLabel("最大Token："))
        self.vision_token_input = QSpinBox()
        self.vision_token_input.setRange(10, 4096)
        vision_token_layout.addWidget(self.vision_token_input)
        vision_token_layout.addStretch()
        layout.addLayout(vision_token_layout)

        lbl_vision_warn2 = QLabel("<i>注意！如果不认识请勿修改此内容！</i>")
        lbl_vision_warn2.setStyleSheet("font-family: 'HarmonyOS Sans SC'; color: red; font-size: 12px;")
        layout.addWidget(lbl_vision_warn2)

        layout.addStretch()
        container.setLayout(layout)
        scroll.setWidget(container)
        
        tab_layout = QVBoxLayout()
        tab_layout.addWidget(scroll)
        self.tab_persona.setLayout(tab_layout)

    def setup_phrases_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        lbl_title = QLabel("<b>💬 UI 提示语自定义</b>")
        lbl_title.setStyleSheet("font-family: 'HarmonyOS Sans SC'; font-size: 14px; color: #ff8c00;")
        layout.addWidget(lbl_title)
        
        lbl_desc = QLabel("在这里修改桌宠在各种状态下气泡里显示的固定文字喵~")
        lbl_desc.setStyleSheet("font-family: 'HarmonyOS Sans SC'; color: gray; font-size: 12px;")
        layout.addWidget(lbl_desc)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        layout.addWidget(QLabel("<b>打招呼（设置快捷键版）：</b>"))
        self.hello_hk_msg_input = QLineEdit()
        self.hello_hk_msg_input.setPlaceholderText("例如：主人好喵！按下快捷键我就会吐槽你哦~")
        layout.addWidget(self.hello_hk_msg_input)

        layout.addWidget(QLabel("<b>打招呼（无快捷键）：</b>"))
        self.hello_msg_input = QLineEdit()
        self.hello_msg_input.setPlaceholderText("例如：主人好喵！")
        layout.addWidget(self.hello_msg_input)

        layout.addWidget(QLabel("<b>正在窥屏中：</b>"))
        self.peek_msg_input = QLineEdit()
        self.peek_msg_input.setPlaceholderText("例如：让我来看看")
        layout.addWidget(self.peek_msg_input)

        layout.addWidget(QLabel("<b>重复窥屏（防抖提示）：</b>"))
        self.peekagain_msg_input = QLineEdit()
        self.peekagain_msg_input.setPlaceholderText("例如：本猫还在思考啦喵！")
        layout.addWidget(self.peekagain_msg_input)

        layout.addWidget(QLabel("<b>报错前缀：</b>"))
        self.error_head_msg_input = QLineEdit()
        self.error_head_msg_input.setPlaceholderText("例如：呜呜，引擎报错了喵：")
        layout.addWidget(self.error_head_msg_input)

        layout.addStretch()
        container.setLayout(layout)
        scroll.setWidget(container)
        
        tab_layout = QVBoxLayout()
        tab_layout.addWidget(scroll)
        self.tab_phrases.setLayout(tab_layout)

    def add_example_item(self):
        text = self.ex_input.text().strip()
        if text:
            self.create_custom_list_item(text)
            self.ex_input.clear()
        else:
            QMessageBox.warning(self, "提示", "语录内容不能为空喵！")

    def create_custom_list_item(self, text):
        item = QListWidgetItem(self.ex_list_widget)
        item.setText(text) 
        
        row_widget = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_widget.setStyleSheet("background-color: white; border: 1px solid #e0e0e0; border-radius: 8px;")
        
        lbl_text = QLabel(text)
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet("font-family: 'HarmonyOS Sans SC'; border: none; background: transparent; color: #333; font-size: 13px;")
        
        btn_del = QPushButton("❌")
        btn_del.setFixedSize(24, 24)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("QPushButton { font-family: 'HarmonyOS Sans SC'; border: none; background: transparent; color: #ff4d4d; } QPushButton:hover { background-color: #ffe6e6; border-radius: 12px; }")
        
        btn_del.clicked.connect(lambda checked, i=item: self.delete_specific_item(i))
        
        row_layout.addWidget(lbl_text)
        row_layout.addWidget(btn_del, 0, Qt.AlignTop) 
        row_widget.setLayout(row_layout)
        
        original_size = row_widget.sizeHint()
        adjusted_height = original_size.height() + 5 
        item.setSizeHint(QSize(original_size.width(), adjusted_height))
        
        self.ex_list_widget.setItemWidget(item, row_widget)

    def delete_specific_item(self, item):
        row = self.ex_list_widget.row(item)
        self.ex_list_widget.takeItem(row)

    def refresh_mod_list(self, target_folder=None):
        self.mod_combo.blockSignals(True)
        self.mod_combo.clear()
        
        pet_last_folder = "default_pet"
        if not target_folder:
            try:
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        pet_last_folder = json.load(f).get("PET_LAST", "default_pet")
            except: pass
        else:
            pet_last_folder = target_folder

        target_index = -1

        dirs_to_scan = [self.asset_dir, self.petmod_dir]
        for base_d in dirs_to_scan:
            if os.path.exists(base_d):
                for folder in os.listdir(base_d):
                    folder_path = os.path.join(base_d, folder)
                    nature_file = os.path.join(folder_path, "nature.json")
                    if os.path.isdir(folder_path) and os.path.exists(nature_file):
                        try:
                            with open(nature_file, 'r', encoding='utf-8') as f:
                                nature = json.load(f)
                                pet_name = nature.get("name", folder)
                                if not pet_name: pet_name = folder
                                
                                data_pkg = {"folder": folder, "base": base_d}
                                self.mod_combo.addItem(pet_name, userData=data_pkg)
                                
                                if folder == pet_last_folder:
                                    target_index = self.mod_combo.count() - 1
                        except: pass
                    
        self.mod_combo.blockSignals(False)
        
        if target_index >= 0:
            self.mod_combo.setCurrentIndex(target_index)
        elif self.mod_combo.count() > 0:
            self.mod_combo.setCurrentIndex(0)
            
        self.on_mod_combo_changed(self.mod_combo.currentIndex())

    def on_mod_combo_changed(self, index):
        if index < 0: return
        data = self.mod_combo.itemData(index)
        self.current_mod_folder = data["folder"]
        self.current_base_dir = data["base"] 
        self.load_mod_data()

    def load_mod_data(self):
        # Abandoning unsaved edits must never delete files used by the saved config.
        self.pending_image_removals.clear()
        self.mod_folder_input.setText(self.current_mod_folder)
        nature_file = os.path.join(self.current_base_dir, self.current_mod_folder, "nature.json")
        
        if os.path.exists(nature_file):
            try:
                with open(nature_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    
                    # 🌟 黑科技：自动愈合老旧存档的缺失变量！
                    self.current_nature = auto_heal_config(raw_data, DEFAULT_NATURE_TEMPLATE)
                    
            except Exception as e:
                QMessageBox.warning(self, "错误", f"读取 nature.json 失败: {e}")
                return
        else: return

        self.mod_name_input.setText(self.current_nature.get("name", self.current_mod_folder))
        self.scale_input.setValue(self.current_nature.get("scale", 1.0))
        self.default_img_display.setText(self.current_nature.get("default_image", ""))
        
        self.chat_prompt_input.setPlainText(self.current_nature.get("chat_prompt", ""))
        self.chat_token_input.setValue(self.current_nature.get("chat_max_tokens", 150))
        self.vision_prompt_input.setPlainText(self.current_nature.get("vision_prompt", ""))
        self.vision_token_input.setValue(self.current_nature.get("vision_max_tokens", 150))
        
        self.ex_list_widget.clear()
        examples = self.current_nature.get("chat_example", [])
        if isinstance(examples, list):
            for ex in examples:
                self.create_custom_list_item(ex)

        self.hello_hk_msg_input.setText(self.current_nature.get("hello_hk_msg", "主人好喵！按下快捷键我就会吐槽你哦~"))
        self.hello_msg_input.setText(self.current_nature.get("hello_msg", "主人好喵！"))
        self.peek_msg_input.setText(self.current_nature.get("peek_msg", "让我来看看"))
        self.peekagain_msg_input.setText(self.current_nature.get("peekagain_msg", "本猫还在思考啦喵！"))
        self.error_head_msg_input.setText(self.current_nature.get("error_head_msg", "呜呜，引擎报错了喵："))

        current_state_idx = self.state_combo.currentIndex()
        if current_state_idx < 0: current_state_idx = 0
        self.current_state_key = self.state_keys[current_state_idx]
        
        self.refresh_state_ui()
        self.apply_readonly_state()

    def on_state_combo_changed(self, index):
        self.sync_ui_to_memory()
        self.current_state_key = self.state_keys[index]
        self.refresh_state_ui()

    def refresh_state_ui(self):
        mode_str = self.current_nature.get(f"{self.current_state_key}_mode", "static")
        
        self.anim_mode_combo.blockSignals(True)
        if mode_str == "sequence": self.anim_mode_combo.setCurrentIndex(1)
        elif mode_str == "css": self.anim_mode_combo.setCurrentIndex(2)
        else: self.anim_mode_combo.setCurrentIndex(0)
        self.anim_mode_combo.blockSignals(False)
        
        self.on_anim_mode_changed()

    def on_anim_mode_changed(self):
        idx = self.anim_mode_combo.currentIndex()
        state_key = self.current_state_key
        
        if getattr(self, "_sequence_signal_connected", False):
            self.standing_img_display.currentIndexChanged.disconnect(self.on_sequence_frame_changed)
            self._sequence_signal_connected = False

        self.standing_img_display.clear()
        file_node = self.current_nature.setdefault("file", {}).setdefault(state_key, {})

        if idx == 0: 
            self.lbl_frame_index.hide()
            self.btn_stand_add_replace.show()
            self.btn_stand_add.hide()
            self.btn_stand_replace.hide()
            self.lbl_time.hide()
            self.time_input.hide()
            self.lbl_ms.hide()
            self.lbl_css_row.hide()
            self.row_input.hide()
            self.lbl_css_col.hide()
            self.col_input.hide()
            
            self.standing_img_display.addItem(file_node.get("image", ""))
            self.standing_img_display.setEnabled(False) 
            
        elif idx == 1: 
            self.lbl_frame_index.show()
            self.btn_stand_add_replace.hide()
            self.btn_stand_add.show()
            self.btn_stand_replace.show()
            self.lbl_time.show()
            self.time_input.show()
            self.lbl_ms.show()
            self.lbl_time.setText("该张图片持续时间：")
            self.lbl_css_row.hide()
            self.row_input.hide()
            self.lbl_css_col.hide()
            self.col_input.hide()
            
            frames = file_node.get("frame", [])
            times = file_node.get("frame_time", [])
            
            self.standing_img_display.setEnabled(True)
            if frames:
                self.standing_img_display.addItems(frames)
                self.current_frame_index = 0
                self.lbl_frame_index.setText(f"第 {self.current_frame_index + 1} 张")
                
                try: self.time_input.setValue(int(times[0]) if times else 100)
                except: self.time_input.setValue(100)
            else:
                self.lbl_frame_index.setText("第 0 张")
                self.standing_img_display.addItem("(空)")
                
            self.standing_img_display.currentIndexChanged.connect(self.on_sequence_frame_changed)
            self._sequence_signal_connected = True
            
        elif idx == 2: 
            self.lbl_frame_index.hide()
            self.btn_stand_add_replace.show()
            self.btn_stand_add.hide()
            self.btn_stand_replace.hide()
            self.lbl_time.show()
            self.time_input.show()
            self.lbl_ms.show()
            self.lbl_time.setText("每1格图片持续时间：")
            self.lbl_css_row.show()
            self.row_input.show()
            self.lbl_css_col.show()
            self.col_input.show()
            
            self.standing_img_display.setEnabled(False)
            self.standing_img_display.addItem(file_node.get("css_sprites", ""))
            
            try: self.time_input.setValue(int(file_node.get("css_sprite_time", 100) or 100))
            except: self.time_input.setValue(100)
            try: self.row_input.setValue(int(file_node.get("css_row", 1) or 1))
            except: self.row_input.setValue(1)
            try: self.col_input.setValue(int(file_node.get("css_col", 1) or 1))
            except: self.col_input.setValue(1)

    def on_sequence_frame_changed(self, index):
        if index < 0: return
        times = self.current_nature.get("file", {}).get(self.current_state_key, {}).get("frame_time", [])
        if self.current_frame_index < len(times):
            times[self.current_frame_index] = self.time_input.value()
            
        self.current_frame_index = index
        self.lbl_frame_index.setText(f"第 {index + 1} 张")
        if index < len(times):
            try: self.time_input.setValue(int(times[index]))
            except: self.time_input.setValue(100)

    def sync_ui_to_memory(self):
        state_key = self.current_state_key
        idx = self.anim_mode_combo.currentIndex()
        file_node = self.current_nature.setdefault("file", {}).setdefault(state_key, {})
        
        if idx == 0: 
            self.current_nature[f"{state_key}_mode"] = "static"
            self.current_nature[f"have_{state_key}"] = True if file_node.get("image") else False
        elif idx == 1: 
            self.current_nature[f"{state_key}_mode"] = "sequence"
            self.current_nature[f"have_{state_key}"] = True if file_node.get("frame") else False
            times = file_node.get("frame_time", [])
            if 0 <= self.current_frame_index < len(times):
                times[self.current_frame_index] = self.time_input.value()
        elif idx == 2: 
            self.current_nature[f"{state_key}_mode"] = "css"
            self.current_nature[f"have_{state_key}"] = True if file_node.get("css_sprites") else False
            file_node["css_sprite_time"] = self.time_input.value()
            file_node["css_row"] = self.row_input.value()
            file_node["css_col"] = self.col_input.value()

    def add_or_replace_image(self, action_type):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.gif)")
        if not file_path: return
        
        filename = os.path.basename(file_path)
        dest_folder = os.path.join(self.current_base_dir, self.current_mod_folder)
        state_key = self.current_state_key
        
        if action_type == "default":
            dest_path = os.path.join(dest_folder, filename)
        else:
            os.makedirs(os.path.join(dest_folder, state_key), exist_ok=True)
            dest_path = os.path.join(dest_folder, state_key, filename)
        
        self.setEnabled(False)
        
        self.copy_worker = CopyWorker(file_path, dest_path, action_type, filename)
        self.copy_worker.finished_signal.connect(self.on_image_copied)
        self.copy_worker.finished.connect(self.copy_worker.deleteLater) 
        start_worker(self.copy_worker)

    def on_image_copied(self, success, error_msg, dest_path, action_type, filename):
        if is_shutting_down():
            return
        self.setEnabled(True) 
        
        if not success:
            QMessageBox.warning(self, "拷贝失败", error_msg)
            return
            
        dest_folder = os.path.join(self.current_base_dir, self.current_mod_folder)
        state_key = self.current_state_key
        file_node = self.current_nature.setdefault("file", {}).setdefault(state_key, {})
        
        if action_type == "default":
            old_file = self.current_nature.get("default_image", "")
            if old_file and old_file != filename: self._safe_remove(os.path.join(dest_folder, old_file))
            self.current_nature["default_image"] = filename
            self.default_img_display.setText(filename)
            
        elif action_type == "static_css":
            idx = self.anim_mode_combo.currentIndex()
            if idx == 0:
                old_file = file_node.get("image", "")
                if old_file and old_file != filename: self._safe_remove(os.path.join(dest_folder, state_key, old_file))
                file_node["image"] = filename
            else:
                old_file = file_node.get("css_sprites", "")
                if old_file and old_file != filename: self._safe_remove(os.path.join(dest_folder, state_key, old_file))
                file_node["css_sprites"] = filename
            self.on_anim_mode_changed()
            
        elif action_type == "seq_add":
            file_node.setdefault("frame", []).append(filename)
            file_node.setdefault("frame_time", []).append(100) 
            self.on_anim_mode_changed()
            self.standing_img_display.setCurrentIndex(len(file_node["frame"]) - 1)
            
        elif action_type == "seq_replace":
            frames = file_node.get("frame", [])
            if not frames: return
            idx = self.standing_img_display.currentIndex()
            old_file = frames[idx]
            if old_file != filename: self._safe_remove(os.path.join(dest_folder, state_key, old_file))
            frames[idx] = filename
            self.on_anim_mode_changed()
            self.standing_img_display.setCurrentIndex(idx)

    def save_current_mod(self):
        if not self.current_mod_folder: return
        
        new_folder_name = self.mod_folder_input.text().strip()
        if not new_folder_name:
            QMessageBox.warning(self, "警告", "文件夹名称不能为空！")
            return
            
        if re.search(r'[\\/:*?"<>|]', new_folder_name):
            QMessageBox.warning(self, "警告", "文件夹名称包含非法字符！\n不能包含 \\ / : * ? \" < > |")
            return
            
        try:
            validate_config_name(new_folder_name)
        except ValueError as exc:
            QMessageBox.warning(self, "警告", str(exc))
            return
        old_path = os.path.join(self.current_base_dir, self.current_mod_folder)
        new_path = old_path
        
        if new_folder_name != self.current_mod_folder:
            if self.current_mod_folder == "default_pet":
                QMessageBox.warning(self, "警告", "不能重命名底层的 default_pet 文件夹！")
                self.mod_folder_input.setText("default_pet")
                return
                
            new_path = os.path.join(self.current_base_dir, new_folder_name)
            
            if os.path.exists(os.path.join(self.asset_dir, new_folder_name)) or \
               os.path.exists(os.path.join(self.petmod_dir, new_folder_name)):
                QMessageBox.warning(self, "警告", f"已存在名为 {new_folder_name} 的文件夹，请换一个名称！")
                return
        
        self.current_nature["name"] = self.mod_name_input.text().strip()
        self.current_nature["scale"] = self.scale_input.value()
        self.current_nature["chat_prompt"] = self.chat_prompt_input.toPlainText()
        self.current_nature["chat_max_tokens"] = self.chat_token_input.value()
        self.current_nature["vision_prompt"] = self.vision_prompt_input.toPlainText()
        self.current_nature["vision_max_tokens"] = self.vision_token_input.value()
        
        example_data = []
        for i in range(self.ex_list_widget.count()):
            example_data.append(self.ex_list_widget.item(i).text())
        self.current_nature["chat_example"] = example_data
        
        self.current_nature["hello_hk_msg"] = self.hello_hk_msg_input.text().strip()
        self.current_nature["hello_msg"] = self.hello_msg_input.text().strip()
        self.current_nature["peek_msg"] = self.peek_msg_input.text().strip()
        self.current_nature["peekagain_msg"] = self.peekagain_msg_input.text().strip()
        self.current_nature["error_head_msg"] = self.error_head_msg_input.text().strip()
        
        self.sync_ui_to_memory()

        self.setEnabled(False)
        self.btn_save.setText("💾 正在保存中...")
        
        self.save_worker = SaveWorker(old_path, new_path, self.current_nature,
                                      self.current_base_dir, new_folder_name,
                                      self.config_path, self.pending_image_removals)
        self.save_worker.finished_signal.connect(self.on_mod_saved)
        self.save_worker.finished.connect(self.save_worker.deleteLater)
        start_worker(self.save_worker)

    def on_mod_saved(self, success, error_msg, new_folder_name):
        if is_shutting_down():
            return
        self.setEnabled(True)
        self.btn_save.setText("💾 更改该桌宠配置")
        
        if not success:
            QMessageBox.warning(self, "错误", f"保存失败: {error_msg}")
            return
            
        self.current_mod_folder = new_folder_name
        self.pending_image_removals.clear()
        # A saved active character must reload before discarded images are needed again.
        try:
            with open(self.config_path, encoding="utf-8") as stream:
                active = json.load(stream).get("PET_LAST")
            if active == new_folder_name:
                self.mod_applied_signal.emit(new_folder_name)
        except (OSError, ValueError) as exc:
            error_msg = (error_msg + "\n" if error_msg else "") + f"读取启用状态失败：{exc}"
        self.refresh_mod_list(target_folder=self.current_mod_folder)
        message = "Mod 配置已保存！"
        if error_msg:
            message += "\n" + error_msg
        QMessageBox.information(self, "成功", message)

    def delete_current_mod(self):
        if self.current_mod_folder == "default_pet":
            QMessageBox.warning(self, "拒绝", "不能删除底层的 default_pet！")
            return
            
        pet_name = self.current_nature.get("name", self.current_mod_folder)
        res = QMessageBox.question(self, "警告", f"确定要永久删除【{pet_name}】及其所有图片吗？", QMessageBox.Yes | QMessageBox.No)
        
        if res == QMessageBox.Yes:
            self.setEnabled(False)
            self.btn_del.setText("🗑️ 正在删除...")
            
            target_dir = os.path.join(self.current_base_dir, self.current_mod_folder)
            self.delete_worker = DeleteWorker(target_dir, self.current_base_dir, self.config_path)
            self.delete_worker.finished_signal.connect(self.on_mod_deleted)
            self.delete_worker.finished.connect(self.delete_worker.deleteLater)
            start_worker(self.delete_worker)

    def on_mod_deleted(self, success, error_msg, fallback):
        if is_shutting_down():
            return
        self.setEnabled(True)
        self.btn_del.setText("🗑️ 删除该配置")
        if fallback:
            self.mod_applied_signal.emit(fallback)

        if not success:
            QMessageBox.warning(self, "错误", f"删除失败: {error_msg}")
            return
            
        self.refresh_mod_list()
        QMessageBox.information(self, "成功", "已删除")

    def delete_state_image(self):
        dest_folder = os.path.join(self.current_base_dir, self.current_mod_folder)
        state_key = self.current_state_key
        
        state_folder = os.path.join(dest_folder, state_key)
        
        file_node = self.current_nature.setdefault("file", {}).setdefault(state_key, {})
        idx = self.anim_mode_combo.currentIndex()
        
        if idx == 0:
            self._safe_remove(os.path.join(state_folder, file_node.get("image", "")))
            file_node["image"] = ""
        elif idx == 2:
            self._safe_remove(os.path.join(state_folder, file_node.get("css_sprites", "")))
            file_node["css_sprites"] = ""
        elif idx == 1:
            frames = file_node.get("frame", [])
            times = file_node.get("frame_time", [])
            c_idx = self.standing_img_display.currentIndex()
            if 0 <= c_idx < len(frames):
                self._safe_remove(os.path.join(state_folder, frames[c_idx]))
                frames.pop(c_idx)
                if c_idx < len(times): times.pop(c_idx)
        self.on_anim_mode_changed()

    def _safe_remove(self, path):
        root = os.path.join(self.current_base_dir, self.current_mod_folder)
        if os.path.isfile(path):
            try:
                self.pending_image_removals.add(image_relative_path(root, path))
            except ValueError:
                pass  # Never queue a path outside this character's images.

    def apply_current_mod(self):
        if not self.current_mod_folder: return
        
        default_img = self.current_nature.get("default_image", "")
        if not default_img:
            QMessageBox.warning(self, "拒绝", "该配置缺少基础静态立绘，不准启用喵！\n请先在形象设置中添加一张静态立绘！")
            return
            
        self.setEnabled(False)
        self.btn_apply.setText("🌟 正在启用...")
        
        self.apply_worker = ApplyWorker(self.config_path, self.current_mod_folder)
        self.apply_worker.finished_signal.connect(self.on_mod_applied)
        self.apply_worker.finished.connect(self.apply_worker.deleteLater)
        start_worker(self.apply_worker)

    def on_mod_applied(self, success, error_msg, current_mod_folder):
        if is_shutting_down():
            return
        self.setEnabled(True)
        self.btn_apply.setText("🌟 启用该配置")
        
        if not success:
            QMessageBox.warning(self, "错误", f"应用配置失败: {error_msg}")
            return
            
        pet_name = self.current_nature.get("name", current_mod_folder)
        QMessageBox.information(self, "成功", f"已启用桌宠：{pet_name}")
        self.mod_applied_signal.emit(current_mod_folder)

    def create_new_mod(self):
        base_name = "桌宠配置"
        counter = 1
        while True:
            new_folder = f"{base_name}{counter}"
            new_path = os.path.join(self.petmod_dir, new_folder)
            if not os.path.exists(new_path):
                break
            counter += 1
            
        # 🌟 直接从全局模板深度拷贝一份作为新桌宠的默认值
        default_nature = copy.deepcopy(DEFAULT_NATURE_TEMPLATE)
        default_nature["name"] = new_folder
        
        self.setEnabled(False)
        self.btn_new.setText("➕ 正在创建...")
        
        self.create_worker = CreateWorker(new_path, self.state_keys, default_nature, new_folder)
        self.create_worker.finished_signal.connect(self.on_mod_created)
        self.create_worker.finished.connect(self.create_worker.deleteLater)
        start_worker(self.create_worker)

    def on_mod_created(self, success, error_msg, new_folder):
        if is_shutting_down():
            return
        self.setEnabled(True)
        self.btn_new.setText("➕ 新建配置")
        
        if not success:
            QMessageBox.warning(self, "错误", f"创建配置失败: {error_msg}")
            return
            
        self.refresh_mod_list(target_folder=new_folder)
        QMessageBox.information(self, "成功", f"已在 petmod 下成功创建新配置：{new_folder}")

    def apply_readonly_state(self):
        can_write = self.current_nature.get("can_write", True)
        
        self.mod_folder_input.setReadOnly(not can_write)
        self.mod_name_input.setReadOnly(not can_write)
        self.btn_add_default_img.setEnabled(can_write)
        self.state_combo.setEnabled(can_write)
        self.anim_mode_combo.setEnabled(can_write)
        self.btn_stand_add_replace.setEnabled(can_write)
        self.btn_stand_add.setEnabled(can_write)
        self.btn_stand_replace.setEnabled(can_write)
        self.btn_stand_del.setEnabled(can_write)
        self.time_input.setEnabled(can_write)
        self.row_input.setEnabled(can_write)
        self.col_input.setEnabled(can_write)
        
        self.chat_prompt_input.setReadOnly(not can_write)
        self.chat_token_input.setEnabled(can_write)
        self.vision_prompt_input.setReadOnly(not can_write)
        self.vision_token_input.setEnabled(can_write)
        
        self.ex_input.setReadOnly(not can_write)
        self.btn_add_ex.setEnabled(can_write)
        
        for i in range(self.ex_list_widget.count()):
            item = self.ex_list_widget.item(i)
            widget = self.ex_list_widget.itemWidget(item)
            if widget:
                del_btn = widget.layout().itemAt(1).widget()
                if del_btn:
                    del_btn.setVisible(can_write)
                    
        self.hello_hk_msg_input.setReadOnly(not can_write)
        self.hello_msg_input.setReadOnly(not can_write)
        self.peek_msg_input.setReadOnly(not can_write)
        self.peekagain_msg_input.setReadOnly(not can_write)
        self.error_head_msg_input.setReadOnly(not can_write)
        
        self.btn_save.setEnabled(can_write)
        
        if not can_write:
            self.mod_folder_input.setStyleSheet("background-color: #f0f0f0; color: #666;")
            self.btn_save.setText("🔒 作者设定此 Mod 不可被修改")
            self.btn_save.setStyleSheet("font-family: 'HarmonyOS Sans SC'; background-color: #cccccc; color: #666666; border-radius: 5px;")
        else:
            self.mod_folder_input.setStyleSheet("")
            self.btn_save.setText("💾 更改该桌宠配置")
            self.btn_save.setStyleSheet("font-family: 'HarmonyOS Sans SC'; background-color: #ffb6c1; color: white; font-weight: bold; font-size: 14px; border-radius: 5px;")
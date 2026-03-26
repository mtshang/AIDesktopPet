# 文件名：set.py
import os
import shutil
import json
import sys
# [新增] 引入底层模块，为了触发热更新函数
import bottom 
from PySide6.QtWidgets import (QWidget, QListWidget, QStackedWidget, QHBoxLayout, 
                               QVBoxLayout, QRadioButton, QButtonGroup, QLabel, 
                               QSpinBox, QGridLayout, QLineEdit, QPushButton, 
                               QMessageBox, QComboBox)
from PySide6.QtGui import QKeySequence, QIcon
from PySide6.QtCore import Qt, Signal

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

# 🌟 冗余自检
if not os.path.exists(config_path) and os.path.exists(default_config_path):
    try: shutil.copy(default_config_path, config_path)
    except: pass
if not os.path.exists(modpath_path) and os.path.exists(default_modpath_path):
    try: shutil.copy(default_modpath_path, modpath_path)
    except: pass

class SettingsWindow(QWidget):
    settings_saved_signal = Signal(dict)
    recording_state_signal = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("桌宠设置中心")
        self.setWindowIcon(QIcon(os.path.join(current_dir, "asset", "icon.ico")))
        self.resize(1024, 576)
        
        main_layout = QHBoxLayout()
        
        self.sidebar = QListWidget()
        self.sidebar.setMaximumWidth(120)
        self.sidebar.addItem("⚙️ api设置")
        self.sidebar.addItem("👁️ 窥屏设置")
        self.sidebar.currentRowChanged.connect(self.switch_page)
        
        self.content_area = QStackedWidget()
        
        self.api_page = QWidget()
        self.init_api_page() 
        
        self.peek_page = QWidget()
        self.init_peek_page()
        
        self.content_area.addWidget(self.api_page)
        self.content_area.addWidget(self.peek_page)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)
        self.setLayout(main_layout)
        
        self.setStyleSheet("""
            QListWidget { font-family: 'Microsoft YaHei'; font-size: 14px; border: 1px solid #ffb6c1; border-radius: 5px; background-color: #fffaf0; outline: none; }
            QListWidget::item { padding: 10px; }
            QListWidget::item:selected { background-color: #ffb6c1; color: white; border-radius: 3px; }
        """)

        self.is_capturing_key = False
        self.load_config_to_ui()

    def switch_page(self, index):
        self.content_area.setCurrentIndex(index)

    def init_peek_page(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # 1. 窥屏间隔设置
        interval_layout = QVBoxLayout()
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(QLabel("<b>窥屏间隔：</b>"))
        self.radio_fixed = QRadioButton("定时")
        self.radio_random = QRadioButton("随机")
        self.radio_close = QRadioButton("关闭窥屏")
        self.radio_close.setChecked(True) 
        
        self.interval_group = QButtonGroup(self)
        self.interval_group.addButton(self.radio_fixed)
        self.interval_group.addButton(self.radio_random)
        self.interval_group.addButton(self.radio_close)
        
        radio_layout.addWidget(self.radio_fixed)
        radio_layout.addWidget(self.radio_random)
        radio_layout.addWidget(self.radio_close)
        radio_layout.addStretch()
        interval_layout.addLayout(radio_layout)

        self.interval_panels = QStackedWidget()
        
        # 定时面板
        self.fixed_panel = QWidget()
        fixed_layout = QHBoxLayout()
        fixed_layout.addWidget(QLabel("设置时间间隔："))
        self.fixed_min = QSpinBox(); self.fixed_min.setRange(0, 999)
        self.fixed_sec = QSpinBox(); self.fixed_sec.setRange(0, 59)
        fixed_layout.addWidget(self.fixed_min); fixed_layout.addWidget(QLabel("分"))
        fixed_layout.addWidget(self.fixed_sec); fixed_layout.addWidget(QLabel("秒 （时间不能小于5秒）"))
        fixed_layout.addStretch()
        self.fixed_panel.setLayout(fixed_layout)
        
        # 随机面板
        self.random_panel = QWidget()
        random_layout = QGridLayout()
        self.rand1_min = QSpinBox(); self.rand1_min.setRange(0, 999)
        self.rand1_sec = QSpinBox(); self.rand1_sec.setRange(0, 59)
        self.rand2_min = QSpinBox(); self.rand2_min.setRange(0, 999)
        self.rand2_sec = QSpinBox(); self.rand2_sec.setRange(0, 59)
        random_layout.addWidget(QLabel("设置随机间隔："), 0, 0)
        random_layout.addWidget(self.rand1_min, 0, 1); random_layout.addWidget(QLabel("分"), 0, 2)
        random_layout.addWidget(self.rand1_sec, 0, 3); random_layout.addWidget(QLabel("秒"), 0, 4)
        random_layout.addWidget(QLabel(" ~ "), 0, 5, Qt.AlignCenter)
        random_layout.addWidget(self.rand2_min, 1, 1); random_layout.addWidget(QLabel("分"), 1, 2)
        random_layout.addWidget(self.rand2_sec, 1, 3); random_layout.addWidget(QLabel("秒"), 1, 4)
        random_layout.addWidget(QLabel("（时间不能小于5秒）"), 1, 5)
        random_layout.setColumnStretch(6, 1)
        self.random_panel.setLayout(random_layout)
        
        self.empty_panel = QWidget()

        self.interval_panels.addWidget(self.fixed_panel)
        self.interval_panels.addWidget(self.random_panel)
        self.interval_panels.addWidget(self.empty_panel)
        self.interval_panels.setCurrentWidget(self.empty_panel)
        
        interval_layout.addWidget(self.interval_panels)
        layout.addLayout(interval_layout)

        self.radio_fixed.toggled.connect(lambda: self.interval_panels.setCurrentWidget(self.fixed_panel))
        self.radio_random.toggled.connect(lambda: self.interval_panels.setCurrentWidget(self.random_panel))
        self.radio_close.toggled.connect(lambda: self.interval_panels.setCurrentWidget(self.empty_panel))

        # 2. 快捷键设置
        hotkey_layout = QVBoxLayout()
        hk_radio_layout = QHBoxLayout()
        hk_radio_layout.addWidget(QLabel("<b>窥屏快捷键设置：</b>"))
        self.hk_enable = QRadioButton("启用快捷键窥屏")
        self.hk_disable = QRadioButton("关闭")
        self.hk_enable.setChecked(True)
        
        self.hk_group = QButtonGroup(self)
        self.hk_group.addButton(self.hk_enable)
        self.hk_group.addButton(self.hk_disable)
        
        hk_radio_layout.addWidget(self.hk_enable)
        hk_radio_layout.addWidget(self.hk_disable)
        hk_radio_layout.addStretch()
        hotkey_layout.addLayout(hk_radio_layout)

        self.hk_panel = QWidget()
        hk_inner_layout = QHBoxLayout()
        self.hk_display = QLineEdit("f9")
        self.hk_display.setReadOnly(True)
        self.hk_display.setMaximumWidth(150)
        self.hk_display.setStyleSheet("background-color: #f0f0f0; color: #333;")
        
        self.hk_btn = QPushButton("设置快捷键")
        self.hk_btn.clicked.connect(self.start_capturing_key)
        
        hk_inner_layout.addWidget(self.hk_display)
        hk_inner_layout.addWidget(self.hk_btn)
        hk_inner_layout.addStretch()
        self.hk_panel.setLayout(hk_inner_layout)
        
        hotkey_layout.addWidget(self.hk_panel)
        layout.addLayout(hotkey_layout)
        
        self.hk_enable.toggled.connect(self.hk_panel.show)
        self.hk_disable.toggled.connect(self.hk_panel.hide)

        # 3. 保存按钮
        layout.addStretch()
        self.save_btn = QPushButton("💾 保存窥屏设置")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("QPushButton { background-color: #ffb6c1; color: white; font-weight: bold; border-radius: 5px; font-size: 14px; } QPushButton:hover { background-color: #ff91a4; }")
        self.save_btn.clicked.connect(self.validate_and_save)
        layout.addWidget(self.save_btn)

        self.peek_page.setLayout(layout)

    def load_config_to_ui(self):
        if not os.path.exists(config_path): return
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            mode = config.get("PEEK_MODE", "close")
            params = config.get("PEEK_PARAMS", {})
            
            if mode == "fixed":
                self.radio_fixed.setChecked(True)
                total_sec = params.get("interval", 300)
                self.fixed_min.setValue(total_sec // 60)
                self.fixed_sec.setValue(total_sec % 60)
            elif mode == "random":
                self.radio_random.setChecked(True)
                min_sec = params.get("min", 60)
                max_sec = params.get("max", 120)
                self.rand1_min.setValue(min_sec // 60)
                self.rand1_sec.setValue(min_sec % 60)
                self.rand2_min.setValue(max_sec // 60)
                self.rand2_sec.setValue(max_sec % 60)
            else:
                self.radio_close.setChecked(True)

            hk_enabled = config.get("HOTKEY_ENABLED", True)
            if hk_enabled:
                self.hk_enable.setChecked(True)
                self.hk_panel.show()
            else:
                self.hk_disable.setChecked(True)
                self.hk_panel.hide()
                
            self.hk_display.setText(config.get("HOTKEY", "f9").lower())
        except Exception as e:
            print(f"⚠️ 设置界面读取存档失败: {e}")

    def start_capturing_key(self):
        self.hk_display.setText("按下要设置的按键...")
        self.hk_display.setStyleSheet("background-color: #ffb6c1; color: white; font-weight: bold;")
        self.is_capturing_key = True
        self.recording_state_signal.emit(True)
        self.grabKeyboard() 

    def keyPressEvent(self, event):
        if self.is_capturing_key:
            if event.key() not in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta):
                key_str = QKeySequence(event.keyCombination()).toString().lower()
                self.hk_display.setText(key_str)
                self.hk_display.setStyleSheet("background-color: #f0f0f0; color: #333;")
                
                self.is_capturing_key = False
                self.releaseKeyboard()
                self.recording_state_signal.emit(False)
        else:
            super().keyPressEvent(event)

    def validate_and_save(self):
        settings_payload = {
            'peek_mode': 'close',
            'peek_params': {},
            'hotkey_enabled': self.hk_enable.isChecked(),
            'hotkey': self.hk_display.text().lower()
        }

        if self.radio_fixed.isChecked():
            total_sec = self.fixed_min.value() * 60 + self.fixed_sec.value()
            if total_sec < 5:
                QMessageBox.warning(self, "设置失败", "定时时间总和不能小于 5 秒喵！")
                return
            settings_payload['peek_mode'] = 'fixed'
            settings_payload['peek_params'] = {'interval': total_sec}

        elif self.radio_random.isChecked():
            total_sec1 = self.rand1_min.value() * 60 + self.rand1_sec.value()
            total_sec2 = self.rand2_min.value() * 60 + self.rand2_sec.value()
            if total_sec1 < 5 or total_sec2 < 5:
                QMessageBox.warning(self, "设置失败", "随机时间的两个端点都不能小于 5 秒喵！")
                return
            min_sec = min(total_sec1, total_sec2)
            max_sec = max(total_sec1, total_sec2)
            settings_payload['peek_mode'] = 'random'
            settings_payload['peek_params'] = {'min': min_sec, 'max': max_sec}
            
        elif self.radio_close.isChecked():
            settings_payload['peek_mode'] = 'close'

        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config["PEEK_MODE"] = settings_payload["peek_mode"]
            config["PEEK_PARAMS"] = settings_payload["peek_params"]
            config["HOTKEY_ENABLED"] = settings_payload["hotkey_enabled"]
            config["HOTKEY"] = settings_payload["hotkey"]
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "存档失败", f"写入 config.json 失败：{e}")
            return

        self.settings_saved_signal.emit(settings_payload)
        QMessageBox.information(self, "成功", "窥屏设置已应用至桌宠大脑，并保存至硬盘喵！")

    def init_api_page(self):
        combo_style = """
            QComboBox { padding: 5px; border: 1px solid #ccc; border-radius: 3px; min-width: 150px; background-color: white; }
            QComboBox QAbstractItemView { background-color: white; selection-background-color: #ffb6c1; selection-color: white; outline: none; }
        """
        self.active_api_name = "" 
        
        layout = QVBoxLayout()
        layout.setSpacing(15)

        title = QLabel("<b>🔌 核心引擎端点配置 (API Settings)</b>")
        title.setStyleSheet("font-size: 16px; color: #333;")
        layout.addWidget(title)
        
        api_select_layout = QHBoxLayout()
        api_select_layout.addWidget(QLabel("<b>🔄 当前选择配置：</b>"))
        
        self.api_combo = QComboBox()
        self.api_combo.setStyleSheet(combo_style)
        self.api_combo.currentTextChanged.connect(self.on_api_combo_changed)
        api_select_layout.addWidget(self.api_combo)
        
        self.enable_api_btn = QPushButton("✅ 启用该配置")
        self.enable_api_btn.setStyleSheet("""
            QPushButton { background-color: #90ee90; color: #006400; border: 1px solid #3cb371; border-radius: 3px; padding: 5px 10px; font-weight: bold; } 
            QPushButton:hover { background-color: #98fb98; }
            QPushButton:disabled { background-color: #e0e0e0; color: #a0a0a0; border: 1px solid #ccc; }
        """)
        self.enable_api_btn.clicked.connect(self.enable_current_api)
        api_select_layout.addWidget(self.enable_api_btn)
        
        self.del_api_btn = QPushButton("🗑️ 删除该配置")
        self.del_api_btn.setStyleSheet("""
            QPushButton { background-color: #ffcccc; border: 1px solid #ff9999; border-radius: 3px; padding: 5px 10px; color: #c00; font-weight: bold; } 
            QPushButton:hover { background-color: #ff9999; color: white; }
            QPushButton:disabled { background-color: #f5f5f5; color: #ccc; border: 1px solid #ddd; }
        """)
        self.del_api_btn.clicked.connect(self.delete_current_api)
        api_select_layout.addWidget(self.del_api_btn)
        
        self.new_api_btn = QPushButton("➕ 新建配置")
        self.new_api_btn.setStyleSheet("QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 3px; padding: 5px 10px; font-weight: bold; color: #333;} QPushButton:hover { background-color: #e0e0e0; }")
        self.new_api_btn.clicked.connect(self.create_new_api)
        api_select_layout.addWidget(self.new_api_btn)
        
        api_select_layout.addStretch()
        layout.addLayout(api_select_layout)
        
        line = QWidget(); line.setFixedHeight(1); line.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(line)

        grid = QGridLayout()
        grid.setVerticalSpacing(12)

        grid.addWidget(QLabel("<b>📄 配置文件名:</b>"), 0, 0)
        self.api_filename = QLineEdit()
        self.api_filename.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 3px;")
        grid.addWidget(self.api_filename, 0, 1, 1, 3)

        grid.addWidget(QLabel("<b>👁️ 视觉模型 (Vision API)</b> - 用于看屏幕"), 1, 0, 1, 4)
        grid.addWidget(QLabel("Base URL:"), 2, 0)
        self.v_url = QLineEdit(); self.v_url.setStyleSheet("padding: 3px;")
        grid.addWidget(self.v_url, 2, 1, 1, 3)
        grid.addWidget(QLabel("API Key:"), 3, 0)
        self.v_key = QLineEdit(); self.v_key.setEchoMode(QLineEdit.PasswordEchoOnEdit); self.v_key.setStyleSheet("padding: 3px;")
        grid.addWidget(self.v_key, 3, 1, 1, 3)
        grid.addWidget(QLabel("Model:"), 4, 0)
        self.v_model = QLineEdit(); self.v_model.setStyleSheet("padding: 3px;")
        grid.addWidget(self.v_model, 4, 1, 1, 3)

        grid.addWidget(QLabel("<b>💬 吐槽模型 (Chat API)</b> - 用于生成对话"), 5, 0, 1, 4)
        grid.addWidget(QLabel("Base URL:"), 6, 0)
        self.c_url = QLineEdit(); self.c_url.setStyleSheet("padding: 3px;")
        grid.addWidget(self.c_url, 6, 1, 1, 3)
        grid.addWidget(QLabel("API Key:"), 7, 0)
        self.c_key = QLineEdit(); self.c_key.setEchoMode(QLineEdit.PasswordEchoOnEdit); self.c_key.setStyleSheet("padding: 3px;")
        grid.addWidget(self.c_key, 7, 1, 1, 3)
        grid.addWidget(QLabel("Model:"), 8, 0)
        self.c_model = QLineEdit(); self.c_model.setStyleSheet("padding: 3px;")
        grid.addWidget(self.c_model, 8, 1, 1, 3)

        layout.addLayout(grid)

        self.save_api_btn = QPushButton("📦 更改该 API 配置")
        self.save_api_btn.setMinimumHeight(45)
        self.save_api_btn.setStyleSheet("""
            QPushButton { background-color: #87CEFA; color: white; font-weight: bold; border-radius: 5px; font-size: 15px; } 
            QPushButton:hover { background-color: #00BFFF; }
            QPushButton:disabled { background-color: #d3d3d3; color: #a9a9a9; }
        """)
        self.save_api_btn.clicked.connect(self.save_api_to_file)
        
        layout.addWidget(self.save_api_btn)
        layout.addStretch()
        self.api_page.setLayout(layout)
        
        self.refresh_api_combo()

    def refresh_api_combo(self, select_name=None):
        self.api_combo.blockSignals(True)
        self.api_combo.clear()
        
        api_dir = os.path.join(current_dir, "api")
        if not os.path.exists(api_dir): os.makedirs(api_dir)
            
        configs = [f[:-5] for f in os.listdir(api_dir) if f.endswith(".json")]
        
        self.active_api_name = ""
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.active_api_name = json.load(f).get("API_LAST", "")
            except: pass

        if not configs:
            self.api_combo.addItem("(空)")
            self.api_combo.blockSignals(False)
            self.on_api_combo_changed("(空)")
            return
                
        self.api_combo.addItems(configs)
        
        if select_name and select_name in configs:
            self.api_combo.setCurrentText(select_name)
        elif self.active_api_name in configs:
            self.api_combo.setCurrentText(self.active_api_name)
        else:
            self.api_combo.setCurrentIndex(0) 
                
        self.api_combo.blockSignals(False)
        self.on_api_combo_changed(self.api_combo.currentText())

    def on_api_combo_changed(self, api_name):
        if not api_name: return
        
        if api_name == "(空)":
            self.api_filename.clear(); self.v_url.clear(); self.v_key.clear(); self.v_model.clear()
            self.c_url.clear(); self.c_key.clear(); self.c_model.clear()
            
            self.enable_api_btn.setEnabled(False)
            self.enable_api_btn.setText("🚫 无配置")
            self.del_api_btn.setEnabled(False)
            self.save_api_btn.setEnabled(False)
            return
            
        self.del_api_btn.setEnabled(True)
        self.save_api_btn.setEnabled(True)
        
        self.api_filename.setText(api_name)
        
        api_file = os.path.join(current_dir, "api", f"{api_name}.json")
        if os.path.exists(api_file):
            try:
                with open(api_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.v_url.setText(data.get("VISION_BASE_URL", ""))
                    self.v_key.setText(data.get("VISION_API_KEY", ""))
                    self.v_model.setText(data.get("VISION_MODEL", ""))
                    self.c_url.setText(data.get("CHAT_BASE_URL", ""))
                    self.c_key.setText(data.get("CHAT_API_KEY", ""))
                    self.c_model.setText(data.get("CHAT_MODEL", ""))
            except: pass

        if api_name == self.active_api_name:
            self.enable_api_btn.setEnabled(False)
            self.enable_api_btn.setText("🔄 当前正在使用")
        else:
            self.enable_api_btn.setEnabled(True)
            self.enable_api_btn.setText("✅ 启用该配置")
            
    def enable_current_api(self):
        target = self.api_combo.currentText()
        if not target: return
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                config["API_LAST"] = target
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                    
                self.active_api_name = target
                
                # ⚡️【核心触发】：写入文件后，强行让底层重新装载配置！
                bottom.update_api_globals()
                
                QMessageBox.information(self, "启用成功", f"桌宠大脑已成功切换至引擎：【{target}】喵！")
                self.on_api_combo_changed(target)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"启用失败：{e}")

    def create_new_api(self):
        api_dir = os.path.join(current_dir, "api")
        if not os.path.exists(api_dir): os.makedirs(api_dir)
        
        idx = 1
        while True:
            new_name = f"新建配置{idx}"
            if not os.path.exists(os.path.join(api_dir, f"{new_name}.json")):
                break
            idx += 1
            
        empty_payload = {
            "VISION_API_KEY": "", "VISION_BASE_URL": "", "VISION_MODEL": "",
            "CHAT_API_KEY": "", "CHAT_BASE_URL": "", "CHAT_MODEL": ""
        }
        
        try:
            with open(os.path.join(api_dir, f"{new_name}.json"), 'w', encoding='utf-8') as f:
                json.dump(empty_payload, f, ensure_ascii=False, indent=4)
            self.refresh_api_combo(select_name=new_name)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"新建失败：{e}")

    def delete_current_api(self):
        target = self.api_combo.currentText()
        if not target: return
        
        reply = QMessageBox.question(self, '确认删除', f'确定要彻底销毁配置文件 "{target}" 吗喵？\n(删除后不可恢复)',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                                     
        if reply == QMessageBox.Yes:
            file_path = os.path.join(current_dir, "api", f"{target}.json")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    QMessageBox.information(self, "成功", "配置文件已化为齑粉喵！")
                    self.refresh_api_combo()
                except Exception as e:
                    QMessageBox.warning(self, "失败", f"删除失败，可能被占用了喵：{e}")

    def save_api_to_file(self):
        old_name = self.api_combo.currentText()
        new_name = self.api_filename.text().strip()
        
        if not new_name:
            QMessageBox.warning(self, "错误", "配置文件名不能为空喵！")
            return
        if new_name.endswith(".json"): new_name = new_name[:-5]
            
        api_dir = os.path.join(current_dir, "api")
        
        if old_name and old_name != new_name and old_name != "(空)":
            old_path = os.path.join(api_dir, f"{old_name}.json")
            if os.path.exists(old_path):
                os.remove(old_path)
            if old_name == self.active_api_name:
                self.active_api_name = new_name
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    config["API_LAST"] = new_name
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=4)
                except: pass
        
        file_path = os.path.join(api_dir, f"{new_name}.json")
        payload = {
            "VISION_API_KEY": self.v_key.text().strip(),
            "VISION_BASE_URL": self.v_url.text().strip(),
            "VISION_MODEL": self.v_model.text().strip(),
            "CHAT_API_KEY": self.c_key.text().strip(),
            "CHAT_BASE_URL": self.c_url.text().strip(),
            "CHAT_MODEL": self.c_model.text().strip()
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)
                
            # ⚡️【核心触发】：如果你修改的刚好是当前正在使用的 API，强行热更新！
            if new_name == self.active_api_name:
                bottom.update_api_globals()
                
            QMessageBox.information(self, "保存成功", f"API 档案 [{new_name}] 已成功更改并入库喵！")
            self.refresh_api_combo(select_name=new_name)
        except Exception as e:
            QMessageBox.warning(self, "失败", f"文件写入失败：\n{e}")
# 文件名：set_api.py
import os, sys, json
import bottom 
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                               QPushButton, QGridLayout, QLineEdit, QMessageBox)

# 【新增】引入工业级防损坏写入工具
from json_write import save_config_atomic

def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

current_dir = get_base_path()
config_path = os.path.join(current_dir, "config.json")

class ApiPage(QWidget):
    def __init__(self):
        super().__init__()
        self.active_api_name = "" 
        self.init_ui()

    def init_ui(self):
        combo_style = """
            QComboBox { padding: 5px; border: 1px solid #ccc; border-radius: 3px; min-width: 150px; background-color: white; }
            QComboBox QAbstractItemView { background-color: white; selection-background-color: #ffb6c1; selection-color: white; outline: none; }
        """
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
        self.setLayout(layout)
        
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
                
                # 【核心优化】原子化写入
                save_config_atomic(config, config_path)
                    
                self.active_api_name = target
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
            # 【核心优化】原子化写入
            save_config_atomic(empty_payload, os.path.join(api_dir, f"{new_name}.json"))
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
                    with open(config_path, 'r', encoding='utf-8') as f: config = json.load(f)
                    config["API_LAST"] = new_name
                    # 【核心优化】原子化写入
                    save_config_atomic(config, config_path)
                except: pass
        
        file_path = os.path.join(api_dir, f"{new_name}.json")
        payload = {
            "VISION_API_KEY": self.v_key.text().strip(), "VISION_BASE_URL": self.v_url.text().strip(), "VISION_MODEL": self.v_model.text().strip(),
            "CHAT_API_KEY": self.c_key.text().strip(), "CHAT_BASE_URL": self.c_url.text().strip(), "CHAT_MODEL": self.c_model.text().strip()
        }
        
        try:
            # 【核心优化】原子化写入
            save_config_atomic(payload, file_path)
                
            if new_name == self.active_api_name:
                bottom.update_api_globals()
                
            QMessageBox.information(self, "保存成功", f"API 档案 [{new_name}] 已成功更改并入库喵！")
            self.refresh_api_combo(select_name=new_name)
        except Exception as e:
            QMessageBox.warning(self, "失败", f"文件写入失败：\n{e}")
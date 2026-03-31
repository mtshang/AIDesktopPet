# 文件名：set_peek.py
import os, sys, json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, 
                               QButtonGroup, QStackedWidget, QSpinBox, QGridLayout, 
                               QLineEdit, QPushButton, QMessageBox)
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt, Signal

def get_base_path():
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(get_base_path(), "config.json")

class PeekPage(QWidget):
    settings_saved_signal = Signal(dict)
    recording_state_signal = Signal(bool)

    def __init__(self):
        super().__init__()
        self.is_capturing_key = False
        self.init_ui()
        self.load_config()

    def init_ui(self):
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

        self.setLayout(layout)

    def load_config(self):
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
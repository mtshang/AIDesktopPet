# 🐾 AIDesktopPet (AI 桌面宠物)

![License](https://img.shields.io/github/license/mtshang/AIDesktopPet)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/PySide6-GUI-green)

一款结合**视觉感知（Vision）** 与**大语言模型（LLM）** 的跨平台桌面端 Agent 助手。采用无边框透明 UI 设计，结合系统级全局监听，实现基于当前屏幕画面的情境感知与智能交互，为你提供极致流畅的桌面 AI 陪伴体验。

## ✨ 核心特性

- 👁️ **多模态情境感知**：基于 `PIL.ImageGrab` 截取系统全局画面，利用 Base64 编码打通视觉模型（VLM）的数据链路，实现“屏幕内容识别 - 情境分析 - 智能回复”的交互闭环。
- ⚡ **异步无阻塞架构**：采用 `QThread` 将耗时的网络 I/O 与大模型推理剥离至子线程，配合 `Signal` 信号槽机制跨线程通信，彻底解决 GUI 程序“假死”问题，保障交互帧率。
- 🛡️ **优雅降级与自愈机制**：设计了轻量级动态资源路由，物理隔离默认资产与自定义 Mod 目录。在首次克隆无配置环境，或检测到用户自定义路径失效时，自动触发 Fallback 回退机制与兜底生成逻辑。
- ⌨️ **底层系统接管**：深度调用 PySide6 窗口属性（无边框、鼠标穿透、永远置顶），并集成全局键盘钩子（Hook）实现快捷键无缝唤醒。

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone [https://github.com/mtshang/AIDesktopPet.git](https://github.com/mtshang/AIDesktopPet.git)
cd AIDesktopPet
```
### 2. 安装依赖
请确保你的环境中已安装 Python 3.10+，然后执行：
```Bash
pip install PySide6 openai pillow keyboard
```
### 3. 配置与运行
项目采用模块化配置解耦，首次运行会自动生成 config.json 等配置文件。
```Bash
python main.py
```
注意：请在生成的配置或设置界面中填入你的可用大模型 API Key 及节点地址。

## 📂 项目结构说明
main.py：程序入口与生命周期管理

pet.py：桌面宠物 UI 核心组件与动画逻辑

bottom.py：大模型交互底层逻辑与 QThread 多线程引擎

set.py：系统设置与配置参数的动态加载 UI

asset/：默认美术资产与皮肤配置

## 🤝 许可证
本项目基于 MIT License 开源。欢迎任何人提交 Issue 或 Pull Request 来共同完善这个项目。

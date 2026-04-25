# 🐾 AIDesktopPet (AI 桌面宠物) v0.2.0

![License](https://img.shields.io/github/license/mtshang/AIDesktopPet)
![Version](https://img.shields.io/badge/Version-0.2.0-orange)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/PySide6-GUI-green)

一款结合 **视觉感知（Vision）** 与 **大语言模型（LLM）** 的轻量化桌面端交互助手。通过实时屏幕情境感知与多模态模型驱动，为你提供智能化、个性化的赛博陪伴体验。

## ✨ v0.2.0 核心特性更新

- 🧩 **全新模块化设置中心**：彻底重构单体架构，将设置面板解耦为 `API设置`、`通用设置`、`MOD管理`、`窥屏机制` 四大独立子模块，实现纯异步无阻塞的现代化 UI 交互。
- 🎨 **独立 MOD 引擎与动态路由**：引入全新的 `petmod/` 目录结构与 `modpath.json` 动态路径解析机制，支持用户零代码热插拔自定义角色皮肤与系统预设（Nature Prompt）。
- 🔤 **统一视觉排版体验**：全局注入 `HarmonyOS Sans SC` 定制字体，解决跨平台与不同分辨率下的 GUI 字体渲染发虚与排版错乱问题。
- 👁️ **多模态情境感知**：集成视觉模型（VLM）数据链路，实现对全局屏幕内容的实时识别与深度互动。
- ⚡ **异步高性能架构**：基于 `QThread` 与 `Signal-Slot` 实现网络 I/O、截图线程与 GUI 渲染的物理隔离，确保在复杂 API 请求期间主界面依然丝滑响应。
- 🛡️ **工业级稳定性设计**：
  - **原子化数据持久化**：采用 `json_write.py` 临时文件中转机制，彻底杜绝异常断电或强杀进程导致的配置文件（0KB）损坏。
  - **系统级事件拦截**：底层调用全局键盘钩子（Hook）捕捉快捷键，解决复杂应用环境下的焦点丢失问题。

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone -b main https://github.com/mtshang/AIDesktopPet.git
cd AIDesktopPet
```

### 2. 安装依赖 
```bash
# 安装核心依赖库
pip install PySide6 openai pillow keyboard
```

### 3. 配置与运行
项目采用模块化配置解耦，首次运行会自动生成核心运行所需的环境配置文件。
```bash
python main.py
```
> **Pro-Tip**：建议以管理员权限运行程序，以获得在全屏游戏环境下的最佳全局快捷键监听兼容性。

## 📂 核心项目结构说明

```text
📦 AIDesktopPet
 ┣ 📜 main.py               # 程序入口、High DPI 适配及 UAC 权限调度
 ┣ 📜 pet.py                # 主窗口控制器，负责状态机切换与屏幕停靠逻辑
 ┣ 📜 bottom.py             # 底层核心引擎，涵盖屏幕捕捉、图像压缩及大模型双路网络交互
 ┣ 📜 pet_bubble.py         # 交互气泡组件，内置防抖拦截逻辑与动态 UI 状态控制
 ┣ 📜 json_write.py         # 防御性编程：原子化文件写入模块，保障数据存储安全
 ┣ 📜 version_check.py      # 异步版本校验模块
 ┣ 📜 pet_tutorial.py       # 新手引导与教程渲染模块
 ┣ 📂 设置中心模块组 (Settings)
 ┃ ┣ 📜 set.py              # 设置面板主容器与导航路由
 ┃ ┣ 📜 set_api.py          # API 密钥与大模型参数调度
 ┃ ┣ 📜 set_general.py      # 常规运行属性配置
 ┃ ┣ 📜 set_mod.py          # UGC 角色模组管理器
 ┃ ┗ 📜 set_peek.py         # 屏幕感知(窥屏)时间间隔与快捷键设定
 ┣ 📂 asset/                # 系统级预设美术资源、默认配置与全局字体 (HarmonyOS Sans)
 ┗ 📂 petmod/               # 用户自定义扩展模组 (Mods) 目录
```

## 🤝 协议与声明 (License & Disclaimer)

**1. 代码授权 (Code License)**
* **v0.2.0 及后续版本 ([main 分支](https://github.com/mtshang/AIDesktopPet/tree/main))**：
  * 采用 [PolyForm Noncommercial 1.0.0](https://github.com/mtshang/AIDesktopPet/blob/main/LICENSE) 协议。
  * **非商业使用**：本项目核心代码仅供个人学习、研究与交流，严禁任何形式的商业化变现。
  * **商业授权**：如需将本软件用于商业用途，请联系创作者 [@mtshang](https://github.com/mtshang) 获取商业授权。
  * **UGC 与 Mod 免责声明**：用户通过修改配置文件（如 `.json`）或使用本软件扩展制作的自定义 Mod，其衍生内容的著作权归用户本人所有。若用户在制作 Mod 过程中使用了未经授权的侵权素材（含图像、音频、文本等），纯属用户个人行为，与本软件及核心开发者无关。

* **v0.1.2 历史版本 ([v0.1.2-opensource 分支](https://github.com/mtshang/AIDesktopPet/tree/v0.1.2-opensource))**：
  * 采用 [MIT License](https://github.com/mtshang/AIDesktopPet/blob/v0.1.2-opensource/LICENSE) 协议。您可以自由学习、修改和分发该分支下的早期源代码。

**2. 美术资产保留 (All Rights Reserved)**
* 本项目的专属 Logo 及相关核心美术资源（包括但不限于 `asset/icon.ico` 文件）**独立于上述开源协议**。
* 该资产的版权完全归属于创作者 [@mtshang](https://github.com/mtshang) 所有，保留所有权利。严禁未经明确授权，擅自使用、修改本软件 Logo 或将其用于任何形式的商业化宣传与变现。

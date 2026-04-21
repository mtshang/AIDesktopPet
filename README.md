# 🐾 AIDesktopPet (AI 桌面宠物)

![License](https://img.shields.io/github/license/mtshang/AIDesktopPet)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/PySide6-GUI-green)

一款结合 **视觉感知（Vision）** 与 **大语言模型（LLM）** 的轻量化桌面端交互助手。通过实时屏幕情境感知与多模态模型驱动，为你提供智能化、个性化的赛博陪伴体验。

## ✨ 核心特性

- 👁️ **多模态情境感知**：集成视觉模型（VLM）数据链路，实现对全局屏幕内容的实时识别与深度吐槽。
- ⚡ **异步高性能架构**：基于 `QThread` 实现网络 I/O 与 GUI 渲染的物理隔离，确保在 API 请求期间界面依然丝滑响应。
- 🛡️ **工业级稳定性设计**：
  - **原子化数据持久化**：采用临时文件中转机制，彻底杜绝异常断电导致的配置文件损坏。
  - **主动内存管理**：针对图像处理链路进行对象显式销毁，强制触发 GC 回收，保障长期挂机零负担。
  - **网络冗余防御**：内置 API 熔断机制与超时监控，优雅处理网络波动与服务端拥堵。
- 🎮 **深度环境适配**：支持 **UAC 提权自举** 与无焦点交互属性，确保程序在全屏游戏及高权限应用环境下依然能稳定监听与渲染。

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone -b main https://github.com/mtshang/AIDesktopPet.git
cd AIDesktopPet
```

### 2. 安装依赖
请确保你的环境中已安装 Python 3.10+，然后执行以下命令安装所需依赖库：
```bash
pip install PySide6 openai pillow keyboard
```

### 3. 配置与运行
项目采用模块化配置解耦，首次运行会自动生成环境配置文件。
```bash
python main.py
```
> **Pro-Tip**：建议以管理员权限运行程序，以获得在全屏游戏环境下的最佳兼容性。

## 📂 项目结构说明

- `main.py`：程序入口、High DPI 适配及 UAC 权限调度。
- `pet.py`：主窗口控制器，负责状态机切换与窗口绑定逻辑。
- `bottom.py`：底层引擎，涵盖屏幕捕捉、图像压缩及大模型双路交互。
- `pet_bubble.py`：交互气泡组件，内置防抖拦截逻辑与动态 UI 状态控制。
- `json_write.py`：原子化文件写入模块，保障数据存储安全性。
- `version_check.py`：异步版本校验模块，提供云端更新提醒。
- `asset/`：预设美术资源与角色皮肤 Mod 目录。

## 🤝 协议与声明 (License & Disclaimer)

* **代码授权**：本项目 `v0.1.2` 版本的源代码 [v0.1.2-opensource分支中](https://github.com/mtshang/AIDesktopPet/tree/v0.1.2-opensource) 基于 [MIT License](https://github.com/mtshang/AIDesktopPet/blob/v0.1.2-opensource/LICENSE) 彻底开源。您可以自由学习、修改和分发。
* **资产保留**：本项目的专属 Logo 美术资源（即 `asset/icon.ico` 文件）**不适用**于 MIT 协议。该资产的版权归创作者 [@mtshang](https://github.com/mtshang) 所有，保留所有权利 (All Rights Reserved)。
  * 严禁未经明确授权将本软件 Logo 用于任何形式的商业变现。

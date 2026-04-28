# SurgeryBox Project 文档入口

本项目是一个面向硬膜外镇痛护理训练的软硬件一体化系统。它包含 ESP8266 外设固件、PySide6 桌面模拟训练端、拔除硬膜外导管的教学材料、题库练习、训练记录和 AI Nursing Mentor。

当前仓库的正式文档已经整理到 `docs/` 目录。建议从本文开始阅读，再按需要进入专题文档。

## 快速导航

| 文档 | 内容 |
| --- | --- |
| [docs/README.md](docs/README.md) | 文档目录、维护规则、阅读路线 |
| [docs/project-overview.md](docs/project-overview.md) | 项目目标、模块划分、目录结构、当前状态 |
| [docs/setup-and-run.md](docs/setup-and-run.md) | Python 模拟器、PlatformIO 固件、UDP 测试脚本的运行方式 |
| [docs/hardware-and-protocol.md](docs/hardware-and-protocol.md) | ESP8266 固件、硬件引脚、WiFi/HTTP/UDP 协议、事件流程 |
| [docs/mobile-hardware-camera-architecture.md](docs/mobile-hardware-camera-architecture.md) | 最终手机端、人体模型硬件、外部摄像头、上位机低延迟融合架构 |
| [docs/simulator-training-flow.md](docs/simulator-training-flow.md) | 桌面端 UI、登录、训练流程、Quiz 与记录逻辑 |
| [docs/data-ai-and-maintenance.md](docs/data-ai-and-maintenance.md) | 数据目录、AI Mentor、配置、安全风险、维护建议 |

项目已有的教学资料仍保留在原位置：

| 资料 | 内容 |
| --- | --- |
| [simulator/assets/reading.md](simulator/assets/reading.md) | 硬膜外导管安全拔除学习材料 |
| [simulator/assets/epidural_quiz_questions.json](simulator/assets/epidural_quiz_questions.json) | Q1-Q5 题库 |

## 项目组成

```text
surgeryBoxProject/
├─ platformio.ini                  # ESP8266 / Wemos D1 PlatformIO 配置
├─ src/                            # MCU 固件实现
├─ include/                        # MCU 头文件
├─ simulator/                      # PySide6 桌面训练端
│  ├─ main.py                      # 桌面端入口
│  ├─ requirements.txt             # Python 依赖
│  ├─ app/                         # UI、训练、题库、AI、数据逻辑
│  ├─ assets/                      # 图片、音频、题库、阅读材料
│  └─ data/                        # 示例/本地训练记录
├─ models/                         # MediaPipe hand_landmarker.task
├─ udp_echo_tester.py              # UDP 基础连通测试
├─ udp_flow_tester.py              # UDP 全流程测试
├─ download_mediapipe_model.py     # MediaPipe 模型下载脚本
└─ docs/                           # 整理后的项目文档
```

## 一句话架构

ESP8266 固件创建 `surgeryBox` WiFi 热点，通过编码器检测导管拉出距离，控制舵机刹车和回卷电机，并通过 UDP 向桌面端发送 `Pain`、`HighDamp`、`LowDamp` 等事件；PySide6 桌面端负责训练 UI、Quiz、记录、学习材料和 AI 导师。

## 常用运行命令

### 启动桌面模拟器

```powershell
cd D:\surgeryBoxProject\simulator
python main.py
```

注意：桌面端大量资源路径使用相对路径 `assets/...`，建议从 `simulator/` 目录启动。

### 安装 Python 依赖

```powershell
cd D:\surgeryBoxProject\simulator
pip install -r requirements.txt
```

AI Nursing Mentor 还需要 `openai` SDK；当前 `requirements.txt` 尚未列出它。

```powershell
pip install openai
```

### 编译/上传 MCU 固件

```powershell
cd D:\surgeryBoxProject
pio run -e d1
pio run -e d1 -t upload
pio device monitor -b 115200
```

### 测试 UDP 通信

```powershell
python udp_echo_tester.py --mcu-ip 192.168.4.1 --mcu-port 4210 --local-port 4211
```

```powershell
python udp_flow_tester.py --mcu-ip 192.168.4.1 --mcu-port 4210 --local-port 4211 --start --auto
```

## 默认连接信息

| 项目 | 默认值 |
| --- | --- |
| MCU WiFi SSID | `surgeryBox` |
| MCU WiFi Password | `12345678` |
| MCU SoftAP IP | `192.168.4.1` |
| MCU UDP Port | `4210` |
| PC UDP Listen Port | `4211` |
| HTTP Echo | `http://192.168.4.1/echo` |

## 默认测试账号

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| Trainee | `training01` 至 `training20` | `train123` |
| Trainer | `trainer01` 至 `trainer10` | `teach123` |

## 当前重要注意事项

- 当前仓库没有统一交付版说明，`docs/` 是本次整理后的维护入口。
- `simulator/app/ai_config_local.py` 当前被 Git 跟踪，而且文件里存在 API Key 形态的密钥。建议立即轮换密钥，并改为只通过环境变量 `DASHSCOPE_API_KEY` 提供。
- `simulator/requirements.txt` 没有包含 `openai`，但 AI Mentor 代码会导入 `openai.OpenAI`。
- `include/wifi_server.txt` 和 `src/wifi_server.txt` 是旧 TCP 方案，当前主流程使用 UDP。
- `simulator/data/UDP_Test.py` 仍测试 `TestFlow`，但当前固件 `runTestFlow()` 已禁用，UDP handler 也没有处理 `TestFlow`。
- 当前工作区已有未提交/未跟踪文件，本次文档整理只新增文档，不处理代码和数据文件。

## 推荐阅读顺序

1. 先读 [docs/project-overview.md](docs/project-overview.md)，建立整体地图。
2. 如果要运行项目，读 [docs/setup-and-run.md](docs/setup-and-run.md)。
3. 如果要调硬件，读 [docs/hardware-and-protocol.md](docs/hardware-and-protocol.md)。
4. 如果要规划最终手机端、人体模型内硬件、外部摄像头和上位机，读 [docs/mobile-hardware-camera-architecture.md](docs/mobile-hardware-camera-architecture.md)。
5. 如果要改训练流程或 UI，读 [docs/simulator-training-flow.md](docs/simulator-training-flow.md)。
6. 如果要处理数据、AI、发布和维护，读 [docs/data-ai-and-maintenance.md](docs/data-ai-and-maintenance.md)。

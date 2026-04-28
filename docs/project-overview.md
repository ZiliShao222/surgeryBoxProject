# 项目概览

本文档说明 SurgeryBox Project 的目标、组成、目录结构和当前状态。它适合新成员接手项目时快速建立全局理解。

## 项目目标

本项目用于训练护理人员完成硬膜外镇痛相关操作，重点场景是硬膜外导管拔除。系统将临床决策点、视觉/手势交互、实体外设反馈和题库练习结合起来，让学习者在训练中遇到疼痛、高阻力、轻微阻力等关键情况，并根据安全原则作出处理。

学习内容主要覆盖：

- 确认麻醉师医嘱和停止硬膜外镇痛医嘱。
- 确认 INR、血小板等安全条件。
- 确认患者未使用抗凝/抗血小板药物。
- 使用合适体位：侧卧，双膝屈向胸部。
- 出现放射到腿部的疼痛时停止操作。
- 高阻力时停止操作。
- 轻微阻力时重新摆位，若仍有阻力则停止。

## 系统组成

项目分为两大运行端：

| 端 | 目录/入口 | 职责 |
| --- | --- | --- |
| MCU 固件 | `src/main.cpp` | ESP8266 WiFi 热点、UDP/HTTP 通信、编码器距离、舵机刹车、电机回卷、事件触发 |
| 桌面模拟器 | `simulator/main.py` | 登录、UI、训练流程、摄像头/手势识别、Quiz、训练记录、AI Mentor |

辅助内容包括：

| 内容 | 路径 |
| --- | --- |
| 阅读材料 | `simulator/assets/reading.md` |
| Quiz 题库 | `simulator/assets/epidural_quiz_questions.json` |
| UDP 基础测试 | `udp_echo_tester.py` |
| UDP 全流程测试 | `udp_flow_tester.py` |
| MediaPipe 模型下载 | `download_mediapipe_model.py` |

## 目录结构

```text
surgeryBoxProject/
├─ include/
│  ├─ config.h
│  ├─ encoder.h
│  ├─ events.h
│  ├─ motor.h
│  ├─ servo_brake.h
│  ├─ signal_tester.h
│  ├─ wifi_udp_server.h
│  └─ wifi_server.txt              # 旧 TCP 方案保留文件
├─ src/
│  ├─ main.cpp
│  ├─ encoder.cpp
│  ├─ events.cpp
│  ├─ motor.cpp
│  ├─ servo_brake.cpp
│  ├─ signal_tester.cpp
│  ├─ wifi_udp_server.cpp
│  └─ wifi_server.txt              # 旧 TCP 方案保留文件
├─ simulator/
│  ├─ main.py
│  ├─ requirements.txt
│  ├─ user_settings.json
│  ├─ app/
│  │  ├─ auth.py
│  │  ├─ camera_manager.py
│  │  ├─ config.py
│  │  ├─ hand_gesture_recognizer.py
│  │  ├─ hardware_connector.py
│  │  ├─ quiz_module.py
│  │  ├─ training_records.py
│  │  ├─ training_remove_needle.py
│  │  ├─ training_remove_needle_mcu.py
│  │  ├─ ai_mentor.py
│  │  └─ ui/
│  ├─ assets/
│  └─ data/
├─ models/
├─ docs/
├─ platformio.ini
├─ udp_echo_tester.py
├─ udp_flow_tester.py
├─ run_debug_test.py
└─ download_mediapipe_model.py
```

## 当前主流程

### 硬件端

固件启动后：

1. 创建 WiFi 热点 `surgeryBox`。
2. UDP 监听 `4210`。
3. HTTP `/echo` 服务监听 `80`，用于连接测试。
4. 初始化编码器、舵机、电机、事件序列和串口调试转发。
5. 收到 `Start` 后随机选择一组事件距离。
6. 拉动过程中根据编码器距离发送位置、速度和事件信号。
7. 在高阻力/低阻力事件处控制舵机刹车并等待上位机响应。

### 桌面端

应用启动后：

1. 进入登录页。
2. 根据用户角色进入主界面。
3. 训练入口在 `Simulation Training`。
4. `Removal of epidural catheter (Simulator)` 使用 MCU 驱动版训练。
5. `Removal of epidural catheter (No Simulator)` 使用摄像头/手势版训练。
6. 训练结果保存到 `data/<username>/training_logs/`。

## 当前实现状态

| 功能 | 状态 |
| --- | --- |
| ESP8266 UDP 热点通信 | 已实现 |
| HTTP Echo 连接测试 | 已实现 |
| 编码器距离与速度上报 | 已实现 |
| Pain/Pain2/HighDamp/LowDamp/Keep 事件 | 已实现 |
| 舵机刹车控制 | 已实现 |
| 电机回卷 | 已实现 |
| PySide6 主界面 | 已实现 |
| 登录和本地账号 | 已实现 |
| 题库练习 | 已实现 |
| 训练记录保存 | 已实现 |
| AI Nursing Mentor | 已实现，但依赖和密钥管理需要整理 |
| Change dressing / Comprehensive Training | 主界面入口存在，当前代码中标记为 TODO |
| 旧 TCP WiFi 方案 | 已保留为 `.txt`，非当前主流程 |

## 关键风险

- AI 配置文件中存在 API Key 形态的密钥，且本地配置文件被 Git 跟踪。
- `requirements.txt` 缺少 AI Mentor 需要的 `openai` SDK。
- 硬件端真实 `SEQ` 与 MCU 版上位机自己的随机 `pull_config` 同时存在，后续应统一事件来源，避免训练记录和硬件事件不一致。
- `TestFlow` 相关测试脚本已经与当前固件不一致。
- 仓库中存在大量本地运行数据、模型、缓存和 `__pycache__`，需要完善 `.gitignore` 和发布清单。


# 安装与运行

本文档说明如何运行桌面模拟器、编译上传 MCU 固件、下载 MediaPipe 模型，以及使用 UDP 测试脚本验证硬件通信。

## 环境概览

| 部分 | 技术栈 |
| --- | --- |
| MCU 固件 | PlatformIO、Arduino framework、ESP8266 / Wemos D1 |
| 桌面应用 | Python、PySide6、OpenCV、MediaPipe |
| 通信 | ESP8266 SoftAP、UDP、HTTP echo |
| AI Mentor | OpenAI-compatible SDK，当前默认 Dashscope compatible mode |

## Python 桌面端

### 建议启动目录

桌面端的图片、音频、题库等资源大量使用 `assets/...` 相对路径。因此建议从 `simulator/` 目录启动。

```powershell
cd D:\surgeryBoxProject\simulator
python main.py
```

如果从项目根目录直接运行，部分资源可能找不到。

### 安装依赖

```powershell
cd D:\surgeryBoxProject\simulator
pip install -r requirements.txt
```

当前 `requirements.txt` 内容：

```text
PySide6==6.4.3
mediapipe==0.10.0
opencv-python==4.8.0.74
numpy==1.24.3
requests==2.31.0
```

AI Nursing Mentor 代码还需要 `openai` SDK，但当前依赖文件未列出：

```powershell
pip install openai
```

### MediaPipe 模型

手势识别优先查找：

```text
D:\surgeryBoxProject\models\hand_landmarker.task
```

如果模型缺失，可运行：

```powershell
cd D:\surgeryBoxProject
python download_mediapipe_model.py
```

该脚本会从 MediaPipe 官方模型地址下载 `hand_landmarker.task` 到 `models/`。

## 登录账号

账号在 `simulator/app/auth.py` 中本地生成。

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| Trainee | `training01` 至 `training20` | `train123` |
| Trainer | `trainer01` 至 `trainer10` | `teach123` |

Trainer 登录后会额外显示 `Trainer Dashboard` 菜单项。

## MCU 固件

### PlatformIO 配置

`platformio.ini` 中当前环境：

```ini
[env:d1]
platform = espressif8266
board = d1
framework = arduino
upload_speed = 921600
monitor_speed = 115200
lib_deps =
    ArduinoJson@^6.18.5
    ESP8266WiFi
```

### 编译

```powershell
cd D:\surgeryBoxProject
pio run -e d1
```

### 上传

```powershell
cd D:\surgeryBoxProject
pio run -e d1 -t upload
```

### 串口监视

```powershell
cd D:\surgeryBoxProject
pio device monitor -b 115200
```

固件启动后串口应看到类似：

```text
[BOOT] SurgeryBox starting...
[WiFi UDP] Hotspot started. SSID=surgeryBox, Port=4210
[WiFi UDP] Board IP: 192.168.4.1
[HTTP] Echo server started on port 80
[Encoder] Initialized
[Servo] Brake initialized
[Motor] Initialized
```

## 硬件连接测试

### WiFi 连接

MCU 固件启动后会创建热点：

| 项目 | 默认值 |
| --- | --- |
| SSID | `surgeryBox` |
| Password | `12345678` |
| Board IP | `192.168.4.1` |

PC 需要连接到该热点后，才能访问 HTTP/UDP 服务。

桌面端 `Simulator` 页面提供：

- 显示当前 WiFi。
- 尝试连接 MCU WiFi。
- 测试 HTTP `/echo`。

### HTTP Echo 测试

桌面端使用 `simulator/app/hardware_connector.py` 中的 socket HTTP 请求测试：

```text
POST http://192.168.4.1/echo
Body: Hello
```

如果返回内容包含 `Hello`，连接测试显示成功。

### UDP Echo 测试

基础收发：

```powershell
cd D:\surgeryBoxProject
python udp_echo_tester.py --mcu-ip 192.168.4.1 --mcu-port 4210 --local-port 4211
```

脚本启动后会：

1. 绑定本地 UDP `4211`。
2. 发送 `HELLO_PC` 给 MCU。
3. 等待 MCU 回包。
4. 支持输入任意消息发送。

### UDP 全流程测试

```powershell
cd D:\surgeryBoxProject
python udp_flow_tester.py --mcu-ip 192.168.4.1 --mcu-port 4210 --local-port 4211 --start --auto
```

参数说明：

| 参数 | 作用 |
| --- | --- |
| `--start` | 启动后自动发送 `Start` |
| `--auto` | 自动响应阻力事件 |
| `--auto-ok2-delay` | `Continue` 后延迟多久发送 `OK2` |

自动响应规则：

| MCU 事件 | 脚本响应 |
| --- | --- |
| `HighDamp` | `OK` |
| `LowDamp` | `Continue` |
| `Keep` | `OK2` |

交互命令快捷方式：

```text
start, stop, winding, ok, ok1, ok2, continue, hello
```

## 常见问题

### 桌面端资源不显示

优先检查是否从 `simulator/` 目录启动。很多代码使用 `assets/...` 相对路径。

### AI Mentor 报 SDK 缺失

安装 `openai`：

```powershell
pip install openai
```

### AI Mentor 报 API Key 缺失

推荐使用环境变量：

```powershell
$env:DASHSCOPE_API_KEY="your-key"
```

不要把真实 key 写入 Git 跟踪文件。

### MediaPipe 初始化失败

检查模型文件是否存在：

```text
D:\surgeryBoxProject\models\hand_landmarker.task
```

如果没有，运行：

```powershell
python download_mediapipe_model.py
```

### UDP 收不到 MCU 回包

依次检查：

- PC 是否连接到 `surgeryBox` 热点。
- MCU 串口是否打印 Board IP 为 `192.168.4.1`。
- PC 端是否绑定 `4211`。
- 是否先发送了 `HELLO_PC` 或任意 UDP 消息，让 MCU 记录最近客户端地址和端口。
- Windows 防火墙是否阻止 Python UDP。

### TestFlow 脚本无效

`simulator/data/UDP_Test.py` 仍发送 `TestFlow`，但当前固件中 `runTestFlow()` 已禁用，UDP handler 也没有处理 `TestFlow`。建议使用 `udp_flow_tester.py` 替代。


# 数据、AI 与维护说明

本文档说明本地数据结构、AI Nursing Mentor、配置文件、安全注意事项、Git 工作区现状和后续维护建议。

## 本地数据目录

数据根目录由 `simulator/app/config.py` 定义：

```python
DATA_DIR_NAME = "data"
```

`simulator/app/storage.py` 使用当前运行目录作为应用根目录：

```python
def app_root_dir() -> Path:
    return Path.cwd()
```

因此如果从 `simulator/` 目录启动，数据会写入：

```text
D:\surgeryBoxProject\simulator\data\
```

如果从项目根目录启动，数据会写入：

```text
D:\surgeryBoxProject\data\
```

建议统一从 `simulator/` 目录启动，避免数据分散。

## 用户数据结构

登录后会为用户创建：

```text
data/<username>/
├─ profile.json
├─ training_logs/
├─ question_results/
├─ reports/
└─ media_cache/
```

`profile.json` 示例：

```json
{
  "username": "training01",
  "role": "trainee",
  "created_at": "2026-01-01T12:00:00"
}
```

## 训练记录

训练记录由 `simulator/app/training_records.py` 管理。

保存路径：

```text
data/<username>/training_logs/<timestamp>_<trainingtype>.json
```

记录结构：

```json
{
  "username": "training01",
  "completed_at": "2026-01-01T12:00:00.000000",
  "training_data": {
    "training_type": "remove_needle_no_simulator",
    "training_mode": "remove_needle_no_simulator",
    "elapsed_time": 25.4,
    "accuracy": 75.0,
    "events_triggered": {},
    "max_pull_distance": 20.0,
    "pull_config": {},
    "completed_at": "2026-01-01T12:00:00.000000"
  }
}
```

统计功能包括：

- 总训练次数。
- 总训练时间。
- 平均训练时间。
- 最快完成时间。
- 最近训练记录。
- 所有用户统计。

## 练习记录

Practice Questions 的记录逻辑位于 `simulator/app/ui/main_window.py`。题库来自：

```text
simulator/assets/epidural_quiz_questions.json
```

该题库同时用于：

- E-learning 后练习。
- 训练中事件弹题。
- AI Mentor 上下文材料。

## AI Nursing Mentor

核心文件：

```text
simulator/app/ai_mentor.py
simulator/app/ui/ai_mentor_widget.py
simulator/app/ai_config_example.py
simulator/app/ai_config_local.py
```

当前设计：

- 使用 OpenAI-compatible SDK。
- 默认模型：`qwen-plus`。
- 默认 Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`。
- 优先从配置或环境变量读取 API Key。
- Widget 初始化时会加载：
  - `assets/reading.md`
  - `assets/epidural_quiz_questions.json`

AI 系统角色是硬膜外导管拔除护理导师，默认要求用英文回答。

## AI 配置建议

推荐使用环境变量：

```powershell
$env:DASHSCOPE_API_KEY="your-key"
```

不要把真实 API Key 写入 Git 跟踪文件。

建议将 `ai_config_local.py` 改成只读环境变量：

```python
import os

API_URL = ""
API_KEY = os.getenv("DASHSCOPE_API_KEY")
TEMPERATURE = 0.7
MAX_TOKENS = 2000
TIMEOUT = 30
MODEL = "qwen-plus"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

## 当前安全风险

当前仓库中存在一个需要优先处理的问题：

```text
simulator/app/ai_config_example.py
simulator/app/ai_config_local.py
```

这两个文件中出现了 API Key 形态的密钥字符串，并且 `ai_config_local.py` 当前被 Git 跟踪。

建议处理顺序：

1. 立即在供应商后台轮换/吊销已暴露 key。
2. 从 `ai_config_example.py` 和 `ai_config_local.py` 移除真实 key。
3. 将 `simulator/app/ai_config_local.py` 加入 `.gitignore`。
4. 如果文件已提交到远端，按团队安全流程清理 Git 历史或至少确认 key 已失效。
5. 在部署环境中使用环境变量提供 key。

## Git 忽略建议

当前 `.gitignore` 主要忽略 `.pio` 和部分 `.vscode` 文件。建议补充：

```gitignore
# Python cache
__pycache__/
*.py[cod]

# Virtual environments
venv/
.venv/

# Local data and generated records
data/
simulator/data/

# Local AI secrets
simulator/app/ai_config_local.py

# Local settings
simulator/user_settings.json

# Downloaded models if not intended to version
models/

# PlatformIO
.pio/

# IDE
.vscode/settings.json
```

是否忽略 `models/` 取决于交付方式：

- 如果希望离线即用，可以保留模型文件但明确来源。
- 如果希望仓库轻量，忽略模型并要求运行 `download_mediapipe_model.py`。

## 当前已知不一致

| 项目 | 现状 | 建议 |
| --- | --- | --- |
| AI 依赖 | `ai_mentor.py` 需要 `openai`，但 `requirements.txt` 未列出 | 加入 `openai` 或在文档中明确单独安装 |
| AI local config | `ai_config_local.py` 被 Git 跟踪且含 key | 移除 key，加入 `.gitignore` |
| TCP WiFi 文件 | `wifi_server.txt` 是旧方案 | 移到 archive 或标注废弃 |
| TestFlow | 测试脚本仍发送 `TestFlow`，固件已禁用 | 更新脚本或删除旧入口 |
| MCU 事件来源 | MCU 有 `SEQ`，上位机也生成 `pull_config` | MCU 模式建议以 `SEQ` 为准 |
| 短拉距离 | `waitShortPull()` 等待 `0.5 m` | 和实际机械/训练长度复核 |
| Reset Simulator | UI 发送 HTTP `reset`，固件只 echo | 若需要 reset，固件需实现对应命令 |
| 数据目录 | 从不同 cwd 启动会写入不同 `data` | 固定启动目录或改成相对项目路径 |

## 维护建议

### 文档维护

建议每次修改以下内容时同步更新文档：

- UDP 协议字段。
- MCU 引脚。
- 训练阶段和事件逻辑。
- 题库内容。
- 默认账号。
- 依赖和运行命令。
- AI Provider 配置。

### 代码组织

后续可以考虑：

- 将 `training_remove_needle.py` 和 `training_remove_needle_mcu.py` 中重复的 UI/Success/Quiz 逻辑抽成共享组件。
- 将 UDP 协议字符串集中定义，避免 MCU 和 Python 两端散落硬编码。
- 将硬件参数，如端口、IP、舵机角度、编码器系数，集中到配置文件。
- 将训练阶段状态机显式建模，减少回调和计时器之间的隐式耦合。

### 测试建议

建议建立三层测试：

| 层级 | 工具 | 目标 |
| --- | --- | --- |
| 协议级 | `udp_echo_tester.py` | 确认 PC/MCU UDP 可达 |
| 流程级 | `udp_flow_tester.py --auto` | 确认事件状态机能跑完 |
| UI 集成 | 手动运行 `simulator/main.py` | 确认训练页面、记录和音视频资源正常 |

### 发布建议

如果要打包给使用者，建议准备：

- 固件烧录说明。
- 桌面端启动脚本。
- Python 运行环境或打包后的 exe。
- MediaPipe 模型文件或下载说明。
- 默认账号说明。
- WiFi 连接说明。
- 训练流程说明。
- 故障排查清单。
- 不包含 API Key 的 AI 配置模板。


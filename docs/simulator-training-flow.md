# 桌面端与训练流程

本文档说明 PySide6 桌面应用的模块、登录、训练入口、拔针训练流程、Quiz 触发和记录保存。

## 桌面端入口

入口文件：

```text
simulator/main.py
```

启动逻辑：

```python
app = QApplication(sys.argv)
win = App()
win.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
win.showFullScreen()
sys.exit(app.exec())
```

主窗口定义在：

```text
simulator/app/ui/main_window.py
```

## 应用模块

主菜单包含：

| 菜单 | 说明 |
| --- | --- |
| `Welcome` | 欢迎页、背景音乐、随机 quote |
| `Simulation Training` | 训练入口 |
| `E-learning Module` | 学习材料/视频入口 |
| `Practice Questions` | 题库练习 |
| `Practice Records` | 练习记录 |
| `Training Records` | 训练记录 |
| `AI Nursing Mentor` | AI 护理导师 |
| `Trainer Dashboard` | Trainer 用户可见 |

顶部按钮包含：

| 按钮 | 说明 |
| --- | --- |
| `Reset Simulator` | 通过 HTTP echo 发送 `reset`，当前固件只会 echo，不会真正 reset |
| `Mute` | 背景音乐静音 |
| `Simulator` | 硬件连接调试页 |
| `Settings` | 摄像头和字体设置 |
| `Logout` | 返回登录页 |

## 登录

登录逻辑在：

```text
simulator/app/auth.py
```

默认账号：

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| Trainee | `training01` 至 `training20` | `train123` |
| Trainer | `trainer01` 至 `trainer10` | `teach123` |

登录后会调用 `write_profile_if_missing()`，在 `data/<username>/profile.json` 创建用户资料。

## Simulation Training 入口

`Simulation Training` 页面当前显示四个按钮：

| 按钮 | training key |
| --- | --- |
| `Comprehensive Training` | `comprehensive` |
| `Change dressing of epidural catheter insertion site` | `change_dressing` |
| `Removal of epidural catheter (Simulator)` | `remove_needle_simulator` |
| `Removal of epidural catheter (No Simulator)` | `remove_needle_no_simulator` |

当前重点实现：

- `remove_needle_simulator`
- `remove_needle_no_simulator`

`change_dressing` 和 `comprehensive` 在主窗口中仍是 TODO。

## 拔针训练模块选择

在 `main_window.py` 中：

```python
if training_key == "remove_needle_simulator":
    from app.training_remove_needle_mcu import RemoveNeedleTraining
else:
    from app.training_remove_needle import RemoveNeedleTraining
```

也就是说：

| 模式 | 模块 | 说明 |
| --- | --- | --- |
| Simulator | `training_remove_needle_mcu.py` | MCU 外设驱动版 |
| No Simulator | `training_remove_needle.py` | 摄像头/手势版 |

## No Simulator 训练流程

模块：

```text
simulator/app/training_remove_needle.py
```

设计流程：

1. Phase 1：初始指导。
2. Phase 2：按住针头。
3. Phase 3：撕医用贴。
4. Phase 3.5：擦拭血迹。
5. Phase 4：拔出导管。
6. 到事件点触发 Quiz。
7. 完成后显示 Success / PASS。
8. 保存训练记录。

关键技术：

| 技术 | 用途 |
| --- | --- |
| OpenCV | 摄像头画面处理和绘制 |
| MediaPipe | 手部关键点、捏合、旋转/擦拭动作识别 |
| PySide6 QThread | 摄像头帧采集 |
| PySide6 QTimer | 阶段转换、动画、延迟完成 |
| QMediaPlayer | 音频播放 |

## Simulator / MCU 训练流程

模块：

```text
simulator/app/training_remove_needle_mcu.py
```

当前该模块中：

```python
self.disable_camera = True
```

所以 Simulator 模式会跳过 Phase 1-3，直接进入 Phase 4，由 MCU UDP 消息驱动。

流程：

1. 启动 `ExternalUDPListener`，绑定本地 UDP `4211`。
2. 发送 `HELLO_PC` 给 MCU `192.168.4.1:4210`。
3. 进入 Phase 4。
4. 监听线程 ready 后发送 `Start`。
5. 接收 MCU 的 `SEQ`、`POS`、`SPEED` 和事件消息。
6. 在黑色训练界面显示当前序列、最近事件、位置、速度。
7. 事件完成数达到 4，且位置达到 20 cm，且至少经过 10 秒后完成训练。
8. 保存训练记录。

MCU 版关键配置：

| 配置 | 默认值 |
| --- | --- |
| `board_ip` | `192.168.4.1` |
| `board_port` | `4210` |
| `local_udp_port` | `4211` |
| `needle_full_length_cm` | `20` |
| `min_phase4_duration` | `10.0` 秒 |

## MCU 消息处理

`_on_external_message()` 处理：

| 消息 | 处理 |
| --- | --- |
| `SEQ:...` | 保存到 `seq_info`，更新 UI |
| `POS:<cm>` | 调用 `_handle_phase4_external_progress()` |
| `SPEED:<cm/s>` | 更新速度显示 |
| `Pain` | 映射到 5 cm 进度 |
| `Pain2` | 映射到 10 cm 进度 |
| `HighDamp` | 映射到 14 cm 进度 |
| `LowDamp` | 映射到 18 cm 进度 |
| `Keep` | 映射到 19 cm 进度 |

注意：这里的映射值用于上位机 UI 进度兜底显示；真实位置优先来自 `POS`。

## 事件和 Quiz

Quiz 模块：

```text
simulator/app/quiz_module.py
```

题库：

```text
simulator/assets/epidural_quiz_questions.json
```

训练中事件到题目的对应关系：

| 训练事件 | Quiz |
| --- | --- |
| 患者尖叫/放射痛 | `Q3` |
| 高阻力 | `Q4` |
| 轻微阻力 | `Q5` |

No Simulator 模式中，Phase 4 触发 `_trigger_quiz_q3()`、`_trigger_quiz_q4()`、`_trigger_quiz_q5()`，主窗口收到 `quiz_triggered` 后：

1. 调用训练模块 `pause_phase4()`。
2. 显示半透明 Quiz 浮层。
3. 只启动对应题目。
4. Quiz 完成后记录结果。
5. 调用 `resume_phase4(quiz_correct=...)`。

Simulator / MCU 模式当前由于 `disable_camera = True`，在 `_handle_phase4_external_progress()` 中采用“自动计数，不弹 Quiz”的路径：

```text
MCU 全自动模式：直接计数，不弹 Quiz
```

后续如果希望 MCU 模式也弹 Quiz，需要统一设计：

- MCU 事件是否直接映射 Quiz。
- Quiz 完成后是否向 MCU 发送 `OK`、`OK1`、`Continue`、`OK2`。
- 训练记录中的正确率如何计算。

## Pull Config

两个训练模块都存在 `_generate_pull_config()`，用于生成 20 cm 虚拟导管上的随机事件点。

当前生成逻辑：

- 随机生成 4 个不同距离，范围 2.0 到 18.0 cm。
- 事件类型包括 `Q3`、`Q3`、`Q4`、`Q5`。
- 形成 `events_queue`。

需要注意：

MCU 固件本身也会在 `Start` 时随机选择一组真实事件距离并发送 `SEQ`。因此 MCU 模式中存在两个潜在事件来源：

- MCU 真实 `SEQ`。
- 上位机 `_generate_pull_config()`。

目前上位机主要显示 `SEQ`，事件完成计数仍基于本地 `pull_config`。后续建议统一为“MCU 模式以 MCU 的 `SEQ` 为准”。

## 训练完成

训练完成后：

1. 显示 `Needle removed successfully!`。
2. 播放 `assets/success.mp3`。
3. 显示 `PASS` 和耗时。
4. 调用 `_complete_training()`。
5. 保存训练记录。
6. 发出 `training_completed` 信号。
7. 主窗口清理训练 widget 并返回训练选项页。

## 训练记录

训练数据包含：

| 字段 | 说明 |
| --- | --- |
| `training_type` | 训练类型 |
| `training_mode` | 兼容旧字段 |
| `elapsed_time` | 完成耗时 |
| `accuracy` | Quiz 正确率 |
| `events_triggered` | 事件触发时间 |
| `max_pull_distance` | 最大拉出距离 |
| `pull_config` | 事件点配置 |
| `completed_at` | 完成时间 |

保存位置：

```text
data/<username>/training_logs/<timestamp>_<trainingtype>.json
```

## Settings

`Settings` 页面包含：

- Camera Settings：摄像头选择、预览、蓝色中心十字对齐。
- Font Settings：字体设置并保存到 `simulator/user_settings.json`。

摄像头预览使用 `CameraThread`，默认优先 Windows `cv2.CAP_DSHOW` 后端。

## Simulator 调试页

`Simulator` 页面包含：

- 当前 WiFi 显示。
- `Connect MCU WiFi`：Windows 下使用 `netsh wlan connect name=surgeryBox ssid=surgeryBox`。
- `Test Connection`：向 `http://192.168.4.1/echo` 发 HTTP 请求。

注意：自动连接要求 Windows 已经保存过同名 WiFi 配置文件。

## E-learning 和 Practice

`E-learning Module` 使用 `reading.md`、视频/素材等展示教学内容。

`Practice Questions` 使用同一份 `epidural_quiz_questions.json`，支持：

- 随机练习。
- 按主题练习。
- 完成后显示分数。
- 保存练习记录。


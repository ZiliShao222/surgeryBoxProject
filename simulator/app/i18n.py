"""Small translation layer for the simulator UI and AI reports.

The project is still moving quickly, so this module intentionally stays simple:
one JSON-backed language setting and a compact translation table. New screens can
use ``tr("some.key")`` without pulling in a larger i18n framework.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


LANG_EN = "en"
LANG_ZH = "zh"
SUPPORTED_LANGUAGES = (LANG_EN, LANG_ZH)

_SETTINGS_PATH = Path(__file__).resolve().parents[1] / "user_settings.json"
_current_language: str | None = None


def normalize_language(language: Any) -> str:
    text = str(language or "").strip().lower()
    if text.startswith("zh") or "中文" in text:
        return LANG_ZH
    return LANG_EN


def language_options() -> Tuple[Tuple[str, str], ...]:
    return (
        (LANG_EN, "English"),
        (LANG_ZH, "中文"),
    )


def _load_settings() -> Dict[str, Any]:
    if not _SETTINGS_PATH.exists():
        return {}
    try:
        with _SETTINGS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"[i18n] Failed to load settings: {exc}")
        return {}


def _save_settings(settings: Dict[str, Any]) -> None:
    try:
        _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except Exception as exc:
        print(f"[i18n] Failed to save settings: {exc}")


def get_language() -> str:
    global _current_language
    if _current_language in SUPPORTED_LANGUAGES:
        return _current_language

    settings = _load_settings()
    configured = settings.get("language") or os.getenv("SURGERYBOX_LANGUAGE")
    _current_language = normalize_language(configured)
    return _current_language


def set_language(language: Any, persist: bool = True) -> str:
    global _current_language
    _current_language = normalize_language(language)

    if persist:
        settings = _load_settings()
        settings["language"] = _current_language
        _save_settings(settings)

    return _current_language


def tr(key: str, **kwargs: Any) -> str:
    language = get_language()
    value = _TRANSLATIONS.get(language, {}).get(key)
    if value is None:
        value = _TRANSLATIONS[LANG_EN].get(key, key)
    if kwargs:
        try:
            return value.format(**kwargs)
        except Exception:
            return value
    return value


def tr_choice(key: str, value: Any) -> str:
    return tr(f"{key}.{str(value or '').strip().lower()}")


def tr_training_label(mode: Any) -> str:
    mode_key = str(mode or "unknown").strip().lower()
    return tr(f"training.{mode_key}")


def tr_list(key: str) -> Iterable[str]:
    language = get_language()
    value = _LIST_TRANSLATIONS.get(language, {}).get(key)
    if value is None:
        value = _LIST_TRANSLATIONS[LANG_EN].get(key, [])
    return list(value)


_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    LANG_EN: {
        "app.header": "Simulation Training for Epidural Analgesia Nursing Care",
        "common.language": "Language",
        "common.refresh": "Refresh",
        "common.settings": "Settings",
        "common.theme": "Theme",
        "common.switch_theme": "Switch Theme",
        "common.logout": "Logout",
        "common.logout_user": "Logout ({username})",
        "common.loading": "Loading...",
        "common.not_available": "Not available",
        "common.unknown": "unknown",
        "common.seconds": "{seconds}s",
        "common.minutes_seconds": "{minutes}m {seconds}s",
        "login.exit": "Exit",
        "login.debug": "Debug",
        "login.title": "Login",
        "login.student_registration": "Student Registration",
        "login.teacher_registration": "Teacher Registration",
        "login.username": "Username",
        "login.password": "Password",
        "login.confirm_password": "Confirm Password",
        "login.teacher_secret_key": "Teacher Secret Key",
        "login.create_account": "Create Account",
        "login.student_register": "Student Register",
        "login.teacher_register": "Teacher Register",
        "login.back_to_login": "Back to Login",
        "login.invalid_credentials": "Invalid username or password",
        "login.password_mismatch": "Passwords do not match.",
        "student.reset_simulator": "Reset Simulator",
        "student.mute": "Mute",
        "student.simulator": "Simulator",
        "student.modules": "Modules",
        "student.dashboard_title": "Student Dashboard",
        "student.dashboard_greeting": "Welcome, {username}. Choose a training task or review your latest progress.",
        "student.completed": "Completed",
        "student.dressing_changes": "Dressing Changes",
        "student.avg_time": "Avg Time",
        "student.best_time": "Best Time",
        "student.avg_accuracy": "Avg Accuracy",
        "student.start_dressing_change": "Start Dressing\nChange AR",
        "student.start_catheter_removal": "Start Catheter\nRemoval Training",
        "student.generate_ai_summary": "Generate AI\nSummary",
        "student.generate_ai_summary_inline": "Generate AI Summary",
        "student.view_records": "View My\nRecords",
        "student.rewind_line": "Rewind\nLine",
        "student.stop_rewind": "Stop\nRewind",
        "student.rewind_hint": "Use after training. Manual rewind stops automatically after {seconds}s.",
        "student.rewind_preparing": "Preparing manual rewind control...",
        "student.rewind_running": "Rewinding line. Click Stop Rewind to stop immediately.",
        "student.rewind_stopped": "Line rewind stopped.",
        "student.rewind_timeout": "Safety timeout reached. Rewind stopped.",
        "student.rewind_unavailable": "Manual rewind unavailable: {message}",
        "student.rewind_training_active": "Finish or exit the current training before rewinding.",
        "student.recent_training": "Recent Training",
        "student.ai_training_summary": "AI Training Summary",
        "student.ai_summary_placeholder": "After training, a summary is generated automatically. You can also click Generate AI Summary above.",
        "student.no_training_records": "No training records yet. Start with a training module.",
        "student.no_training_record_available": "No training record is available yet. Complete one training attempt first.",
        "student.ai_summary_failed": "AI training summary failed. Please check the API configuration and try again.",
        "student.training_records": "Training Records",
        "student.total_trainings": "Total Trainings: {count}",
        "student.total_time": "Total Time: {time}",
        "student.average_time": "Average Time: {time}",
        "student.training_time_trend": "Training Time Trend",
        "student.accuracy_trend": "Accuracy Trend",
        "student.steps": "steps",
        "student.elearning_module": "E-learning Module",
        "student.practice_questions": "Practice Questions",
        "student.practice_records": "Practice Records",
        "student.ai_mentor": "AI Nursing Mentor",
        "student.coming_soon": "Coming soon",
        "student.simulation_training": "Simulation Training",
        "student.comprehensive_training": "Comprehensive\nTraining",
        "student.change_dressing_training": "Change dressing of\nepidural catheter\ninsertion site",
        "student.removal_training": "Epidural catheter\nremoval training",
        "student.camera_settings": "Camera Settings",
        "student.font_settings": "Font Settings",
        "student.hardware_link": "Hardware Link:",
        "student.hardware_checking": "Checking hardware link...",
        "posture.ok_title": "Posture Check Passed: Side-Lying",
        "posture.ok_detail": "Please keep the patient side-lying. Training will start shortly.",
        "posture.bad_title": "Posture Check: Not Side-Lying",
        "posture.bad_detail": "Please adjust the patient to a side-lying position first.",
        "posture.error_title": "Posture Sensor Not Connected",
        "posture.error_detail": "Confirm the IMU is connected directly to computer port {port}.",
        "posture.waiting_title": "Checking Posture",
        "posture.waiting_detail": "Waiting for IMU data. Keep the sensor connected: {port}.",
        "student.ai_mentor_not_configured_title": "AI Mentor Not Configured",
        "student.ai_mentor_not_configured_body": "AI Mentor is not configured.\n\nPlease set API_KEY in app/ai_config_local.py.",
        "student.ai_mentor_error_title": "Error",
        "student.ai_mentor_error_body": "Failed to load AI Mentor.\n\nPlease ensure:\n1. API_KEY is set in app/ai_config_local.py\n2. MODEL / BASE_URL are set in app/ai_config_local.py\n3. Restart the application",
        "menu.welcome": "Welcome",
        "menu.simulation": "Simulation Training",
        "menu.elearning": "E-learning Module",
        "menu.practice": "Practice Questions",
        "menu.practice_records": "Practice Records",
        "menu.training_records": "Training Records",
        "menu.ai_mentor": "AI Nursing Mentor",
        "ai.loading_title": "AI is thinking",
        "ai.student_loading_detail": "Analyzing your latest training record and composing the report",
        "ai.teacher_loading_detail": "Reviewing this student's training history and drafting teaching guidance",
        "mentor.title": "AI Nursing Mentor",
        "mentor.description": "I am an AI nursing mentor to help you understand best practices for catheter care.\nAsk questions about catheter removal procedures, safety, and nursing guidance.",
        "mentor.placeholder": "Type your question... (Ctrl+Enter to send)",
        "mentor.send": "Send",
        "mentor.clear": "Clear",
        "mentor.waiting": "Waiting...",
        "mentor.loaded_context": "Loaded reading and quiz materials into context.",
        "mentor.notice_title": "Notice",
        "mentor.empty_question": "Please enter a question",
        "mentor.error_title": "Error",
        "mentor.not_initialized": "AI Mentor not initialized. Please check API configuration.",
        "mentor.no_response": "Sorry, could not get a response. Please check API configuration and network.",
        "mentor.confirm_title": "Confirm",
        "mentor.clear_confirm": "Clear all conversations?",
        "mentor.truncated": " ... (truncated to 300 words)",
        "teacher.title": "Teacher Console",
        "teacher.subtitle": "Class overview, student progress, and AI teaching workflow",
        "teacher.students": "Students",
        "teacher.with_records": "With Records",
        "teacher.trainings": "Trainings",
        "teacher.dressing_changes": "Dressing Changes",
        "teacher.avg_accuracy": "Avg Accuracy",
        "teacher.student_progress": "Student Progress",
        "teacher.select_student": "Select a student",
        "teacher.generate_advice": "Generate Teaching Advice",
        "teacher.placeholder": "Select a student and generate teaching advice after at least one training record is available.",
        "teacher.no_records": "No training records yet. Ask the student to complete one simulation or camera AR attempt.",
        "teacher.select_student_first": "Select a student first.",
        "teacher.no_records_for_student": "No training records are available for this student yet.",
        "teacher.ai_failed": "AI teaching advice failed. Please check the API configuration and try again.",
        "teacher.total_trainings": "Total trainings: {count}",
        "teacher.dressing_count": "Dressing changes: {count}",
        "teacher.avg_accuracy_scored": "Average accuracy (scored modules): {accuracy:.1f}%",
        "teacher.recent_attempts": "Recent attempts:",
        "teacher.student_row": "{username} | {trainings} trainings | {dressing} dressing | {accuracy:.0f}% avg",
        "report.student_title": "AI Student Debrief",
        "report.teacher_title": "AI Teacher Training Advisor",
        "report.workflow": "Workflow",
        "report.agent_workflow": "Agent Workflow",
        "report.performance_snapshot": "Performance Snapshot",
        "report.student_snapshot": "Student Snapshot",
        "report.decision_basis": "Decision Basis",
        "report.summary": "Summary",
        "report.score_risk": "Score & Risk",
        "report.score": "Score",
        "report.risk_level": "Risk Level",
        "report.strengths": "Strengths",
        "report.areas_to_improve": "Areas To Improve",
        "report.next_steps": "Next Steps",
        "report.recommendation": "Recommendation",
        "report.student_level": "Student Level",
        "report.difficulty_recommendation": "Difficulty Recommendation",
        "report.rationale": "Rationale",
        "report.teaching_focus": "Teaching Focus",
        "report.safety_notes": "Safety Notes",
        "report.metric": "Metric",
        "report.result": "Result",
        "report.training": "Training",
        "report.accuracy": "Accuracy",
        "report.risk": "Risk",
        "report.difficulty_plan": "Difficulty Plan",
        "report.default_summary": "Training summary is available.",
        "report.default_rationale": "Use the current record as the baseline.",
        "report.sequential_completed": "Sequential analysis completed",
        "report.memory_highlights": "Long-Term Memory",
        "report.memory_empty": "No long-term memory yet; reports will become more personalized after more analyzed sessions.",
        "report.memory_sessions": "Sessions remembered: {count}",
        "report.memory_level": "Current learner profile: {level}",
        "report.memory_focus": "Current focus: {focus}",
        "report.memory_strengths": "Recurring strengths: {items}",
        "report.memory_improvements": "Recurring improvement themes: {items}",
        "report.memory_next_steps": "Remembered next-step pattern: {items}",
        "report.memory_teacher_focus": "Teaching focus carried forward: {items}",
        "report.memory_safety": "Safety watchpoints to monitor: {items}",
        "training.remove_needle_simulator": "Catheter Removal Training",
        "training.remove_needle_no_simulator": "Full AR Removal Flow",
        "training.comprehensive": "Comprehensive AR Training",
        "training.change_dressing": "Dressing Change",
        "training.unknown": "Unknown Training",
        "risk.low": "low",
        "risk.medium": "medium",
        "risk.high": "high",
        "plan.increase": "increase",
        "plan.keep": "keep",
        "plan.decrease": "decrease",
    },
    LANG_ZH: {
        "app.header": "硬膜外镇痛护理模拟训练系统",
        "common.language": "语言",
        "common.refresh": "刷新",
        "common.settings": "设置",
        "common.theme": "配色",
        "common.switch_theme": "切换配色",
        "common.logout": "退出登录",
        "common.logout_user": "退出登录 ({username})",
        "common.loading": "加载中...",
        "common.not_available": "暂无数据",
        "common.unknown": "未知",
        "common.seconds": "{seconds}秒",
        "common.minutes_seconds": "{minutes}分{seconds}秒",
        "login.exit": "退出",
        "login.debug": "调试进入",
        "login.title": "登录",
        "login.student_registration": "学生注册",
        "login.teacher_registration": "教师注册",
        "login.username": "账户名称",
        "login.password": "密码",
        "login.confirm_password": "确认密码",
        "login.teacher_secret_key": "教师注册码",
        "login.create_account": "创建账户",
        "login.student_register": "学生注册",
        "login.teacher_register": "教师注册",
        "login.back_to_login": "返回登录",
        "login.invalid_credentials": "账户或密码错误",
        "login.password_mismatch": "两次输入的密码不一致。",
        "student.reset_simulator": "重置模拟器",
        "student.mute": "静音",
        "student.simulator": "模拟器",
        "student.modules": "功能模块",
        "student.dashboard_title": "学生主页",
        "student.dashboard_greeting": "欢迎，{username}。请选择训练任务，或查看最近训练表现。",
        "student.completed": "已完成",
        "student.dressing_changes": "换敷贴次数",
        "student.avg_time": "平均用时",
        "student.best_time": "最佳用时",
        "student.avg_accuracy": "平均正确率",
        "student.start_dressing_change": "开始换敷贴\nAR训练",
        "student.start_catheter_removal": "开始拔管\n训练",
        "student.generate_ai_summary": "生成AI\n总结",
        "student.generate_ai_summary_inline": "生成AI总结",
        "student.view_records": "查看我的\n记录",
        "student.rewind_line": "回收线",
        "student.stop_rewind": "停止回收",
        "student.rewind_hint": "训练结束后使用。手动回收会在 {seconds} 秒后自动停止。",
        "student.rewind_preparing": "正在准备手动回收控制...",
        "student.rewind_running": "正在回收线。点击停止回收可立即停止。",
        "student.rewind_stopped": "回收线已停止。",
        "student.rewind_timeout": "已触发安全超时，回收已停止。",
        "student.rewind_unavailable": "手动回收不可用：{message}",
        "student.rewind_training_active": "请先结束或退出当前训练，再进行回收。",
        "student.recent_training": "最近训练",
        "student.ai_training_summary": "AI训练总结",
        "student.ai_summary_placeholder": "训练结束后会自动生成总结。也可以点击上方按钮手动生成AI总结。",
        "student.no_training_records": "暂无训练记录。可以先开始一个训练模块。",
        "student.no_training_record_available": "当前还没有训练记录。请先完成一次训练。",
        "student.ai_summary_failed": "AI训练总结生成失败。请检查API配置后重试。",
        "student.training_records": "训练记录",
        "student.total_trainings": "训练总次数：{count}",
        "student.total_time": "总用时：{time}",
        "student.average_time": "平均用时：{time}",
        "student.training_time_trend": "训练用时趋势",
        "student.accuracy_trend": "正确率趋势",
        "student.steps": "步骤",
        "student.elearning_module": "在线学习",
        "student.practice_questions": "练习题",
        "student.practice_records": "练习记录",
        "student.ai_mentor": "AI护理助手",
        "student.coming_soon": "即将开放",
        "student.simulation_training": "模拟训练",
        "student.comprehensive_training": "综合\n训练",
        "student.change_dressing_training": "硬膜外导管\n置管处换敷贴",
        "student.removal_training": "硬膜外导管\n拔管训练",
        "student.camera_settings": "摄像头设置",
        "student.font_settings": "字体设置",
        "student.hardware_link": "硬件连接：",
        "student.hardware_checking": "正在检查硬件连接...",
        "posture.ok_title": "体位检查通过：已侧卧",
        "posture.ok_detail": "请保持侧卧状态，训练即将开始。",
        "posture.bad_title": "体位检查：未侧卧",
        "posture.bad_detail": "请先将病人调整为侧卧位。",
        "posture.error_title": "体位传感器未连接",
        "posture.error_detail": "请确认 IMU 已直连电脑串口 {port}。",
        "posture.waiting_title": "体位检查中",
        "posture.waiting_detail": "等待 IMU 数据，请保持传感器连接：{port}。",
        "student.ai_mentor_not_configured_title": "AI助手未配置",
        "student.ai_mentor_not_configured_body": "AI助手尚未配置。\n\n请在 app/ai_config_local.py 中设置 API_KEY。",
        "student.ai_mentor_error_title": "错误",
        "student.ai_mentor_error_body": "AI助手加载失败。\n\n请确认：\n1. app/ai_config_local.py 中已设置 API_KEY\n2. app/ai_config_local.py 中已设置 MODEL / BASE_URL\n3. 重启应用",
        "menu.welcome": "欢迎页",
        "menu.simulation": "模拟训练",
        "menu.elearning": "在线学习",
        "menu.practice": "练习题",
        "menu.practice_records": "练习记录",
        "menu.training_records": "训练记录",
        "menu.ai_mentor": "AI护理助手",
        "ai.loading_title": "AI正在思考",
        "ai.student_loading_detail": "正在分析最近训练记录，并生成结构化报告",
        "ai.teacher_loading_detail": "正在查看学生训练历史，并生成教学建议",
        "mentor.title": "AI护理助手",
        "mentor.description": "我是AI护理助手，可以帮助你理解导管护理的最佳实践。\n你可以询问拔管流程、安全注意事项和护理指导。",
        "mentor.placeholder": "请输入你的问题...（Ctrl+Enter 发送）",
        "mentor.send": "发送",
        "mentor.clear": "清空",
        "mentor.waiting": "思考中...",
        "mentor.loaded_context": "已将阅读材料和题库加载到上下文。",
        "mentor.notice_title": "提示",
        "mentor.empty_question": "请输入问题",
        "mentor.error_title": "错误",
        "mentor.not_initialized": "AI护理助手未初始化，请检查API配置。",
        "mentor.no_response": "抱歉，暂时没有获得回复。请检查API配置和网络连接。",
        "mentor.confirm_title": "确认",
        "mentor.clear_confirm": "确定清空所有对话吗？",
        "mentor.truncated": " ...（已截断至300词）",
        "teacher.title": "教师端",
        "teacher.subtitle": "班级概览、学生进度与AI教学建议",
        "teacher.students": "学生",
        "teacher.with_records": "有记录",
        "teacher.trainings": "训练次数",
        "teacher.dressing_changes": "换敷贴",
        "teacher.avg_accuracy": "平均正确率",
        "teacher.student_progress": "学生进度",
        "teacher.select_student": "请选择学生",
        "teacher.generate_advice": "生成教学建议",
        "teacher.placeholder": "选择学生后，可在至少有一条训练记录时生成教学建议。",
        "teacher.no_records": "暂无训练记录。请让学生先完成一次模拟训练或摄像头AR训练。",
        "teacher.select_student_first": "请先选择一名学生。",
        "teacher.no_records_for_student": "这名学生当前还没有训练记录。",
        "teacher.ai_failed": "AI教学建议生成失败。请检查API配置后重试。",
        "teacher.total_trainings": "训练总次数：{count}",
        "teacher.dressing_count": "换敷贴次数：{count}",
        "teacher.avg_accuracy_scored": "平均正确率（计分模块）：{accuracy:.1f}%",
        "teacher.recent_attempts": "最近训练：",
        "teacher.student_row": "{username} | {trainings}次训练 | {dressing}次换敷贴 | 平均{accuracy:.0f}%",
        "report.student_title": "AI学生训练复盘",
        "report.teacher_title": "AI教师训练建议",
        "report.workflow": "工作流",
        "report.agent_workflow": "智能体工作流",
        "report.performance_snapshot": "表现概览",
        "report.student_snapshot": "学生概览",
        "report.decision_basis": "判断依据",
        "report.summary": "总结",
        "report.score_risk": "得分与风险",
        "report.score": "得分",
        "report.risk_level": "风险等级",
        "report.strengths": "做得好的地方",
        "report.areas_to_improve": "需要改进",
        "report.next_steps": "下一步建议",
        "report.recommendation": "教学建议",
        "report.student_level": "学生水平",
        "report.difficulty_recommendation": "难度建议",
        "report.rationale": "理由",
        "report.teaching_focus": "教学重点",
        "report.safety_notes": "安全提醒",
        "report.metric": "指标",
        "report.result": "结果",
        "report.training": "训练项目",
        "report.accuracy": "正确率",
        "report.risk": "风险",
        "report.difficulty_plan": "难度计划",
        "report.default_summary": "训练总结已生成。",
        "report.default_rationale": "可将本次记录作为当前基线。",
        "report.sequential_completed": "顺序分析已完成",
        "report.memory_highlights": "长期记忆",
        "report.memory_empty": "暂无长期记忆；完成更多训练分析后，报告会变得更个性化。",
        "report.memory_sessions": "已记住训练次数：{count}",
        "report.memory_level": "当前学习画像：{level}",
        "report.memory_focus": "当前重点：{focus}",
        "report.memory_strengths": "稳定优势：{items}",
        "report.memory_improvements": "反复改进点：{items}",
        "report.memory_next_steps": "延续建议：{items}",
        "report.memory_teacher_focus": "延续教学重点：{items}",
        "report.memory_safety": "需要观察的安全点：{items}",
        "training.remove_needle_simulator": "拔管训练",
        "training.remove_needle_no_simulator": "完整AR拔管流程",
        "training.comprehensive": "综合AR训练",
        "training.change_dressing": "换敷贴训练",
        "training.unknown": "未知训练",
        "risk.low": "低",
        "risk.medium": "中",
        "risk.high": "高",
        "plan.increase": "提高难度",
        "plan.keep": "保持当前难度",
        "plan.decrease": "降低难度",
    },
}


_LIST_TRANSLATIONS: Dict[str, Dict[str, Iterable[str]]] = {
    LANG_EN: {},
    LANG_ZH: {},
}

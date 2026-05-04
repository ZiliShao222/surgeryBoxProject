"""Role-specific AI agents for teacher and student training feedback."""

import json
import os
from statistics import mean


def load_default_ai_config():
    """Load the shared OpenAI-compatible configuration used by the app."""
    try:
        from app.ai_config_local import API_URL, API_KEY, MODEL, BASE_URL
    except ImportError:
        from app.ai_config_example import API_URL, API_KEY, MODEL, BASE_URL

    return {
        "api_url": API_URL,
        "api_key": API_KEY or os.getenv("DASHSCOPE_API_KEY", ""),
        "model": MODEL,
        "base_url": BASE_URL or os.getenv("DASHSCOPE_BASE_URL", ""),
    }


def create_teacher_training_agent():
    """Create the teacher-facing training agent with the shared API config."""
    config = load_default_ai_config()
    return TeacherTrainingAgent(
        api_key=config["api_key"],
        model=config["model"],
        base_url=config["base_url"],
        api_url=config["api_url"],
    )


def create_student_training_agent():
    """Create the student-facing training agent with the shared API config."""
    config = load_default_ai_config()
    return StudentTrainingAgent(
        api_key=config["api_key"],
        model=config["model"],
        base_url=config["base_url"],
        api_url=config["api_url"],
    )


class TrainingAgentBase:
    """Shared OpenAI-compatible caller plus data compaction helpers."""

    def __init__(self, api_key=None, model="qwen-plus", base_url=None, api_url=""):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.model = model or os.getenv("DASHSCOPE_MODEL", "qwen-plus")
        self.base_url = base_url or os.getenv("DASHSCOPE_BASE_URL", "")
        self.api_url = api_url

    def _complete(self, system_prompt, payload, fallback_text, temperature=0.35):
        """Call the configured model; return fallback text when unavailable."""
        if not self.api_key or self.api_key == "your-api-key-here":
            return fallback_text

        try:
            from openai import OpenAI
        except Exception as exc:
            print(f"[TrainingAgent] OpenAI SDK not installed: {exc}")
            return fallback_text

        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False, indent=2),
                    },
                ],
                temperature=temperature,
            )
            content = completion.choices[0].message.content or ""
            return content.strip() or fallback_text
        except Exception as exc:
            print(f"[TrainingAgent] AI request failed: {exc}")
            return fallback_text

    def _compact_records(self, records, limit=6):
        compacted = []
        for record in (records or [])[:limit]:
            compacted.append(
                {
                    "completed_at": record.get("completed_at", ""),
                    "training_mode": record.get("training_mode", "unknown"),
                    "elapsed_time_seconds": round(self._to_float(record.get("elapsed_time")), 2),
                    "accuracy_percent": round(self._to_float(record.get("accuracy")), 2),
                    "events_count": record.get("events_count", 0),
                    "quiz_correct": record.get("quiz_correct", 0),
                    "quiz_total": record.get("quiz_total", 0),
                    "max_pull_distance_cm": round(
                        self._to_float(record.get("max_pull_distance")), 2
                    ),
                    "events": record.get("events", {}),
                    "quiz_results": record.get("quiz_results", []),
                    "performance_metrics": record.get("performance_metrics", {}),
                    "pull_config": record.get("pull_config", {}),
                }
            )
        return compacted

    def _aggregate_records(self, records):
        records = records or []
        accuracies = [
            self._to_float(record.get("accuracy"))
            for record in records
            if record.get("accuracy") is not None
        ]
        elapsed_times = [
            self._to_float(record.get("elapsed_time"))
            for record in records
            if record.get("elapsed_time") is not None
        ]
        event_counts = [
            self._to_float(record.get("events_count"))
            for record in records
            if record.get("events_count") is not None
        ]
        recent_accuracy = accuracies[0] if accuracies else 0
        earlier_accuracy = mean(accuracies[1:4]) if len(accuracies) > 1 else recent_accuracy
        recent_time = elapsed_times[0] if elapsed_times else 0
        earlier_time = mean(elapsed_times[1:4]) if len(elapsed_times) > 1 else recent_time

        return {
            "attempts": len(records),
            "avg_accuracy_percent": round(mean(accuracies), 2) if accuracies else 0,
            "latest_accuracy_percent": round(recent_accuracy, 2),
            "accuracy_delta_vs_recent_history": round(recent_accuracy - earlier_accuracy, 2),
            "avg_elapsed_time_seconds": round(mean(elapsed_times), 2) if elapsed_times else 0,
            "latest_elapsed_time_seconds": round(recent_time, 2),
            "time_delta_vs_recent_history": round(recent_time - earlier_time, 2),
            "best_elapsed_time_seconds": round(min(elapsed_times), 2) if elapsed_times else 0,
            "avg_events_count": round(mean(event_counts), 2) if event_counts else 0,
        }

    def _to_float(self, value):
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _level_from_records(self, records):
        aggregate = self._aggregate_records(records)
        attempts = aggregate["attempts"]
        accuracy = aggregate["avg_accuracy_percent"]

        if attempts == 0:
            return "未开始训练"
        if attempts >= 3 and accuracy >= 88:
            return "稳定进阶"
        if accuracy >= 75:
            return "基础达标"
        if accuracy >= 55:
            return "需要巩固"
        return "重点带教"

    def _difficulty_from_records(self, records):
        aggregate = self._aggregate_records(records)
        attempts = aggregate["attempts"]
        accuracy = aggregate["avg_accuracy_percent"]
        delta = aggregate["accuracy_delta_vs_recent_history"]

        if attempts == 0:
            return "基础演示难度"
        if accuracy >= 88 and delta >= -5:
            return "进阶难度"
        if accuracy >= 72:
            return "标准难度"
        return "分段巩固难度"


class TeacherTrainingAgent(TrainingAgentBase):
    """Suggest student level and next training difficulty for teachers."""

    SYSTEM_PROMPT = """
You are a teacher-side clinical training analysis agent for an epidural
catheter removal simulator.

Respond in Simplified Chinese. Use only the provided training data. Do not
invent hidden observations. Be concise, teacher-facing, and action-oriented.

Required structure:
1. 当前水平
2. 主要问题
3. 建议难度
4. 下一轮带教重点
5. 需要教师现场观察的点
""".strip()

    def suggest_for_teacher(self, student_username, records, student_profile=None):
        records = records or []
        aggregate = self._aggregate_records(records)
        payload = {
            "role": "teacher_agent",
            "student_username": student_username,
            "student_profile": student_profile or {},
            "aggregate": aggregate,
            "recent_records": self._compact_records(records),
            "instruction": (
                "Assess the student's current level, likely weak points, and "
                "recommend the next training difficulty for the teacher."
            ),
        }
        fallback = self._fallback_teacher_feedback(student_username, records)
        return self._complete(self.SYSTEM_PROMPT, payload, fallback)

    def _fallback_teacher_feedback(self, student_username, records):
        aggregate = self._aggregate_records(records)
        level = self._level_from_records(records)
        difficulty = self._difficulty_from_records(records)
        attempts = aggregate["attempts"]
        latest_accuracy = aggregate["latest_accuracy_percent"]
        avg_time = aggregate["avg_elapsed_time_seconds"]

        if attempts == 0:
            weak_points = "暂无训练记录，先观察学生是否理解流程、无菌意识和异常情况处理。"
            focus = "先做教师示范，再让学生完成低压力、分步骤练习。"
        elif latest_accuracy < 60:
            weak_points = "最近一次正确率偏低，可能需要重新拆解关键事件判断和问答反应。"
            focus = "放慢节奏，重点看学生对疼痛反馈、阻力变化和停止/上报时机的判断。"
        elif latest_accuracy < 80:
            weak_points = "流程基本能推进，但稳定性不足，容易在事件判断或细节动作上丢分。"
            focus = "维持标准难度，要求学生边操作边口述判断依据。"
        else:
            weak_points = "最近表现较稳定，可继续观察速度提升是否牺牲安全动作。"
            focus = "加入更复杂或更接近真实临床的随机事件组合。"

        return (
            f"1. 当前水平\n"
            f"{student_username}：{level}。已有训练 {attempts} 次，最近正确率 "
            f"{latest_accuracy:.0f}%，平均用时 {avg_time:.1f}s。\n\n"
            f"2. 主要问题\n{weak_points}\n\n"
            f"3. 建议难度\n建议使用：{difficulty}。\n\n"
            f"4. 下一轮带教重点\n{focus}\n\n"
            f"5. 需要教师现场观察的点\n"
            f"观察手部动作是否平稳、是否及时回应异常提示、是否保持无菌和安全优先。"
        )


class StudentTrainingAgent(TrainingAgentBase):
    """Summarize the latest training attempt for the student."""

    SYSTEM_PROMPT = """
You are a student-side training review agent for an epidural catheter removal
simulator.

Respond in Simplified Chinese. Use only the supplied training record. Be
encouraging but honest. Focus on what the student did, what is missing, and
what to practice next. Avoid medical diagnosis or unsupported claims.

Required structure:
1. 本次完成情况
2. 当前缺陷
3. 下一次训练建议
4. 给学生的一句话提醒
""".strip()

    def summarize_after_training(self, student_username, latest_record, recent_records=None):
        latest_record = latest_record or {}
        recent_records = recent_records or []
        payload = {
            "role": "student_agent",
            "student_username": student_username,
            "latest_record": self._compact_records([latest_record], limit=1)[0]
            if latest_record
            else {},
            "recent_history": self._compact_records(recent_records, limit=5),
            "history_aggregate": self._aggregate_records([latest_record] + recent_records),
            "instruction": (
                "Summarize the latest training completion, current defects, "
                "task completion state, and next training suggestions."
            ),
        }
        fallback = self._fallback_student_summary(student_username, latest_record, recent_records)
        return self._complete(self.SYSTEM_PROMPT, payload, fallback)

    def _fallback_student_summary(self, student_username, latest_record, recent_records=None):
        if not latest_record:
            return (
                "1. 本次完成情况\n"
                "当前还没有可复盘的训练记录。\n\n"
                "2. 当前缺陷\n"
                "暂时无法判断，需要先完成一次训练。\n\n"
                "3. 下一次训练建议\n"
                "从基础流程开始，先保证每一步动作和判断都完整。\n\n"
                "4. 给学生的一句话提醒\n"
                "先稳，再快。"
            )

        accuracy = self._to_float(latest_record.get("accuracy"))
        elapsed = self._to_float(latest_record.get("elapsed_time"))
        events_count = latest_record.get("events_count", 0)
        quiz_correct = latest_record.get("quiz_correct", 0)
        quiz_total = latest_record.get("quiz_total", 0)

        if accuracy >= 85:
            completion = "本次任务完成度较好，关键事件处理整体比较稳定。"
            defects = "主要继续关注速度提升时是否仍能保持安全动作和判断质量。"
            advice = "下一次可以尝试标准或进阶难度，并要求自己边操作边复述判断依据。"
        elif accuracy >= 65:
            completion = "本次任务基本完成，但正确率还有提升空间。"
            defects = "可能在异常事件识别、问答选择或流程细节上存在不稳定。"
            advice = "下一次先保持标准难度，重点练习疼痛反馈、阻力变化和停止操作的判断。"
        else:
            completion = "本次任务完成质量偏弱，需要回到分步骤练习。"
            defects = "关键事件处理和操作节奏可能还没有形成稳定模式。"
            advice = "下一次建议降低难度，先分段完成，再连贯完成完整流程。"

        quiz_line = "暂无问答记录"
        if quiz_total:
            quiz_line = f"问答正确 {quiz_correct}/{quiz_total}"

        return (
            f"1. 本次完成情况\n"
            f"{completion} 用时 {elapsed:.1f}s，正确率 {accuracy:.0f}%，触发事件 "
            f"{events_count} 个，{quiz_line}。\n\n"
            f"2. 当前缺陷\n{defects}\n\n"
            f"3. 下一次训练建议\n{advice}\n\n"
            f"4. 给学生的一句话提醒\n"
            f"{student_username}，把每一次异常提示都当成真实病人的信号，先判断清楚再继续。"
        )

"""Persistent memory for the training-analysis agents.

The graph already receives the latest record plus a few recent attempts. This
module adds a small, deterministic long-term memory layer so student and teacher
reports can become more personalized over time without depending on the LLM to
remember anything between calls.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from app.storage import user_dir
except Exception:  # pragma: no cover - import fallback for standalone tests
    user_dir = None


MEMORY_FILENAME = "agent_memory.json"
SCHEMA_VERSION = 1
MAX_SEEN_RECORDS = 200
MAX_PATTERN_ITEMS = 12
MAX_NOTES = 20


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_username(username: Any) -> str:
    text = str(username or "unknown").strip() or "unknown"
    return re.sub(r"[\\/:*?\"<>|]+", "_", text)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _useful_pattern(value: Any) -> bool:
    text = _clean_text(value)
    if not text:
        return False
    lowered = text.lower()
    blocked = (
        "none identified",
        "not available",
        "manual reset",
        "hardware reset",
        "reset required",
    )
    return not any(token in lowered for token in blocked)


def _append_unique(items: List[str], new_items: Iterable[Any], limit: int = MAX_PATTERN_ITEMS) -> List[str]:
    result = list(items or [])
    seen = {_clean_text(item).lower() for item in result}
    for item in new_items:
        text = _clean_text(item)
        key = text.lower()
        if not _useful_pattern(text) or key in seen:
            continue
        result.append(text)
        seen.add(key)
    return result[-limit:]


def _bounded(items: Iterable[Any], limit: int) -> List[Any]:
    values = list(items or [])
    return values[-limit:]


def _weighted_average(old_avg: float, old_count: int, new_value: float) -> float:
    if old_count <= 0:
        return new_value
    return ((old_avg * old_count) + new_value) / (old_count + 1)


def _record_id(metrics: Dict[str, Any]) -> str:
    raw = metrics.get("raw") if isinstance(metrics.get("raw"), dict) else {}
    candidates = (
        metrics.get("record_id"),
        metrics.get("file_path"),
        raw.get("record_id"),
        raw.get("file_path"),
        metrics.get("completed_at"),
    )
    for candidate in candidates:
        text = _clean_text(candidate)
        if text:
            return text

    parts = [
        metrics.get("training_mode", "unknown"),
        metrics.get("completed_at", ""),
        metrics.get("elapsed_time_s", ""),
        metrics.get("accuracy_pct", ""),
        metrics.get("expected_events", ""),
        metrics.get("events_completed", ""),
    ]
    return "|".join(_clean_text(part) for part in parts)


def _default_memory(username: Any) -> Dict[str, Any]:
    now = _now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "username": str(username or "unknown"),
        "created_at": now,
        "updated_at": now,
        "total_sessions_seen": 0,
        "total_reflections": 0,
        "seen_record_ids": [],
        "learner_profile": {
            "level": "new",
            "confidence": "unknown",
            "consistency": "unknown",
            "primary_focus": "Collect more training evidence.",
        },
        "long_term_patterns": {
            "recurring_strengths": [],
            "recurring_improvements": [],
            "safety_watchpoints": [],
            "preferred_next_steps": [],
            "teacher_focus_history": [],
        },
        "training_mode_stats": {},
        "last_session": {},
        "memory_notes": [],
    }


def compact_memory_for_prompt(memory: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a small, prompt-safe memory summary.

    The full memory contains bookkeeping such as seen record ids. The LLM only
    needs durable learning signals.
    """
    if not isinstance(memory, dict):
        return {}

    patterns = memory.get("long_term_patterns") if isinstance(memory.get("long_term_patterns"), dict) else {}
    profile = memory.get("learner_profile") if isinstance(memory.get("learner_profile"), dict) else {}
    mode_stats = memory.get("training_mode_stats") if isinstance(memory.get("training_mode_stats"), dict) else {}

    compact_modes: Dict[str, Any] = {}
    for mode, stats in mode_stats.items():
        if not isinstance(stats, dict):
            continue
        compact_modes[str(mode)] = {
            "attempts": stats.get("attempts", 0),
            "avg_accuracy_pct": stats.get("avg_accuracy_pct"),
            "best_accuracy_pct": stats.get("best_accuracy_pct"),
            "avg_completion_rate_pct": stats.get("avg_completion_rate_pct"),
            "last_risk_level": stats.get("last_risk_level"),
            "last_difficulty_plan": stats.get("last_difficulty_plan"),
        }

    return {
        "sessions_remembered": memory.get("total_sessions_seen", 0),
        "learner_profile": {
            "level": profile.get("level", "new"),
            "confidence": profile.get("confidence", "unknown"),
            "consistency": profile.get("consistency", "unknown"),
            "primary_focus": profile.get("primary_focus", "Collect more training evidence."),
        },
        "recurring_strengths": _as_list(patterns.get("recurring_strengths"))[-4:],
        "recurring_improvements": _as_list(patterns.get("recurring_improvements"))[-4:],
        "safety_watchpoints": _as_list(patterns.get("safety_watchpoints"))[-4:],
        "preferred_next_steps": _as_list(patterns.get("preferred_next_steps"))[-4:],
        "teacher_focus_history": _as_list(patterns.get("teacher_focus_history"))[-4:],
        "training_mode_stats": compact_modes,
        "last_session": memory.get("last_session", {}),
    }


class AgentMemoryStore:
    """File-backed memory store, scoped per student account."""

    def __init__(self, data_dir: Optional[Any] = None):
        self.data_dir = Path(data_dir) if data_dir is not None else None

    def _memory_path(self, username: Any) -> Path:
        safe = _safe_username(username)
        if self.data_dir is not None:
            base = self.data_dir / safe
            base.mkdir(parents=True, exist_ok=True)
            return base / MEMORY_FILENAME

        if user_dir is not None:
            return user_dir(safe) / MEMORY_FILENAME

        base = Path("data") / safe
        base.mkdir(parents=True, exist_ok=True)
        return base / MEMORY_FILENAME

    def load(self, username: Any) -> Dict[str, Any]:
        path = self._memory_path(username)
        if not path.exists():
            return _default_memory(username)
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return _default_memory(username)
        except Exception:
            return _default_memory(username)

        memory = _default_memory(username)
        memory.update(data)
        memory["schema_version"] = SCHEMA_VERSION
        memory["username"] = str(username or memory.get("username") or "unknown")
        return memory

    def save(self, username: Any, memory: Dict[str, Any]) -> Path:
        path = self._memory_path(username)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(memory or {})
        payload["schema_version"] = SCHEMA_VERSION
        payload["username"] = str(username or payload.get("username") or "unknown")
        payload["updated_at"] = _now_iso()
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def load_summary(self, username: Any) -> Dict[str, Any]:
        return compact_memory_for_prompt(self.load(username))

    def update_from_analysis(
        self,
        username: Any,
        metrics: Dict[str, Any],
        risk: Optional[Dict[str, Any]] = None,
        plan: Optional[Dict[str, Any]] = None,
        student_debrief: Optional[Dict[str, Any]] = None,
        teacher_advice: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        risk = risk or {}
        plan = plan or {}
        student_debrief = student_debrief or {}
        teacher_advice = teacher_advice or {}

        memory = self.load(username)
        now = _now_iso()
        record_id = _record_id(metrics)
        seen = _as_list(memory.get("seen_record_ids"))
        is_new_record = record_id not in seen

        memory["updated_at"] = now
        memory["total_reflections"] = int(_as_float(memory.get("total_reflections"))) + 1

        last_session = {
            "record_id": record_id,
            "training_mode": metrics.get("training_mode", "unknown"),
            "completed_at": metrics.get("completed_at") or now,
            "accuracy_pct": _as_float(metrics.get("accuracy_pct")),
            "completion_rate_pct": _as_float(metrics.get("completion_rate_pct")),
            "risk_level": risk.get("level", "medium"),
            "difficulty_plan": plan.get("action", "keep"),
            "summary": _clean_text(student_debrief.get("summary")),
        }
        memory["last_session"] = last_session

        if is_new_record:
            seen.append(record_id)
            memory["seen_record_ids"] = _bounded(seen, MAX_SEEN_RECORDS)
            memory["total_sessions_seen"] = int(_as_float(memory.get("total_sessions_seen"))) + 1
            self._update_mode_stats(memory, metrics, risk, plan)
            self._update_patterns(memory, student_debrief, teacher_advice)
            self._update_profile(memory)
            self._append_note(memory, last_session)
        else:
            memory["seen_record_ids"] = _bounded(seen, MAX_SEEN_RECORDS)

        self.save(username, memory)
        return memory

    def _update_mode_stats(
        self,
        memory: Dict[str, Any],
        metrics: Dict[str, Any],
        risk: Dict[str, Any],
        plan: Dict[str, Any],
    ) -> None:
        mode = _clean_text(metrics.get("training_mode")) or "unknown"
        all_stats = memory.setdefault("training_mode_stats", {})
        stats = all_stats.setdefault(
            mode,
            {
                "attempts": 0,
                "avg_accuracy_pct": 0.0,
                "best_accuracy_pct": 0.0,
                "avg_completion_rate_pct": 0.0,
                "best_completion_rate_pct": 0.0,
                "avg_elapsed_time_s": 0.0,
            },
        )

        attempts = int(_as_float(stats.get("attempts")))
        accuracy = _as_float(metrics.get("accuracy_pct"))
        completion = _as_float(metrics.get("completion_rate_pct"))
        elapsed = _as_float(metrics.get("elapsed_time_s"))

        stats["attempts"] = attempts + 1
        stats["last_accuracy_pct"] = round(accuracy, 1)
        stats["best_accuracy_pct"] = round(max(_as_float(stats.get("best_accuracy_pct")), accuracy), 1)
        stats["avg_accuracy_pct"] = round(_weighted_average(_as_float(stats.get("avg_accuracy_pct")), attempts, accuracy), 1)
        stats["last_completion_rate_pct"] = round(completion, 1)
        stats["best_completion_rate_pct"] = round(max(_as_float(stats.get("best_completion_rate_pct")), completion), 1)
        stats["avg_completion_rate_pct"] = round(
            _weighted_average(_as_float(stats.get("avg_completion_rate_pct")), attempts, completion),
            1,
        )
        if elapsed > 0:
            stats["last_elapsed_time_s"] = round(elapsed, 1)
            stats["avg_elapsed_time_s"] = round(_weighted_average(_as_float(stats.get("avg_elapsed_time_s")), attempts, elapsed), 1)
        stats["last_risk_level"] = risk.get("level", "medium")
        stats["last_difficulty_plan"] = plan.get("action", "keep")

    def _update_patterns(
        self,
        memory: Dict[str, Any],
        student_debrief: Dict[str, Any],
        teacher_advice: Dict[str, Any],
    ) -> None:
        patterns = memory.setdefault("long_term_patterns", {})
        patterns["recurring_strengths"] = _append_unique(
            _as_list(patterns.get("recurring_strengths")),
            _as_list(student_debrief.get("strengths")),
        )
        patterns["recurring_improvements"] = _append_unique(
            _as_list(patterns.get("recurring_improvements")),
            _as_list(student_debrief.get("areas_to_improve")),
        )
        patterns["preferred_next_steps"] = _append_unique(
            _as_list(patterns.get("preferred_next_steps")),
            _as_list(student_debrief.get("next_steps")),
        )
        patterns["teacher_focus_history"] = _append_unique(
            _as_list(patterns.get("teacher_focus_history")),
            _as_list(teacher_advice.get("teaching_focus")),
        )
        patterns["safety_watchpoints"] = _append_unique(
            _as_list(patterns.get("safety_watchpoints")),
            _as_list(teacher_advice.get("safety_notes")),
        )

    def _update_profile(self, memory: Dict[str, Any]) -> None:
        stats = memory.get("training_mode_stats") if isinstance(memory.get("training_mode_stats"), dict) else {}
        total_attempts = 0
        weighted_accuracy = 0.0
        weighted_completion = 0.0
        risk_levels: List[str] = []

        for item in stats.values():
            if not isinstance(item, dict):
                continue
            attempts = int(_as_float(item.get("attempts")))
            total_attempts += attempts
            weighted_accuracy += _as_float(item.get("avg_accuracy_pct")) * attempts
            weighted_completion += _as_float(item.get("avg_completion_rate_pct")) * attempts
            risk_levels.append(str(item.get("last_risk_level", "medium")).lower())

        avg_accuracy = weighted_accuracy / total_attempts if total_attempts else 0.0
        avg_completion = weighted_completion / total_attempts if total_attempts else 0.0

        if total_attempts <= 0:
            level = "new"
            confidence = "unknown"
            consistency = "unknown"
        elif avg_accuracy >= 90 and avg_completion >= 95 and "high" not in risk_levels:
            level = "advanced"
            confidence = "high"
            consistency = "stable"
        elif avg_accuracy >= 70 and avg_completion >= 80:
            level = "intermediate"
            confidence = "moderate"
            consistency = "developing"
        else:
            level = "foundation"
            confidence = "low"
            consistency = "needs repetition"

        patterns = memory.get("long_term_patterns") if isinstance(memory.get("long_term_patterns"), dict) else {}
        improvements = _as_list(patterns.get("recurring_improvements"))
        focus = _clean_text(improvements[-1]) if improvements else "Keep building stable, repeatable technique."

        memory["learner_profile"] = {
            "level": level,
            "confidence": confidence,
            "consistency": consistency,
            "primary_focus": focus,
        }

    def _append_note(self, memory: Dict[str, Any], last_session: Dict[str, Any]) -> None:
        note = (
            f"{last_session.get('completed_at')}: {last_session.get('training_mode')} "
            f"{last_session.get('accuracy_pct'):.1f}% accuracy, "
            f"{last_session.get('risk_level')} risk, plan={last_session.get('difficulty_plan')}"
        )
        notes = _as_list(memory.get("memory_notes"))
        notes.append(note)
        memory["memory_notes"] = _bounded(notes, MAX_NOTES)

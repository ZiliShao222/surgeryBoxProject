"""Training record persistence and normalization helpers."""

import json
from datetime import datetime
from pathlib import Path


class TrainingRecordManager:
    """Save, load, summarize, and normalize training records."""

    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def get_user_training_log_path(self, username):
        """Return the training log directory for a user, creating it if needed."""
        user_dir = self.data_dir / username
        user_dir.mkdir(exist_ok=True)

        training_logs_dir = user_dir / "training_logs"
        training_logs_dir.mkdir(exist_ok=True)
        return training_logs_dir

    def save_training_record(self, username, training_data):
        """Save a training record and return its file path."""
        logs_dir = self.get_user_training_log_path(username)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        training_type = training_data.get("training_mode", "unknown").replace("_", "")
        filepath = logs_dir / f"{timestamp}_{training_type}.json"

        record = {
            "username": username,
            "completed_at": datetime.now().isoformat(),
            "training_data": training_data,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        print(f"[TrainingRecordManager] Training record saved: {filepath}")
        return filepath

    def get_user_training_records(self, username, limit=None):
        """Return raw training records for a user, newest first."""
        logs_dir = self.get_user_training_log_path(username)
        records = []

        if logs_dir.exists():
            for file_path in sorted(logs_dir.glob("*.json"), reverse=True):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["file_path"] = str(file_path)
                    records.append(data)
                except Exception as e:
                    print(f"[TrainingRecordManager] Error reading {file_path}: {e}")

        return records[:limit] if limit else records

    def normalize_training_record(self, record):
        """Return a stable summary shape for old and new training record JSON files."""
        if not isinstance(record, dict):
            record = {}

        training_data = record.get("training_data", {})
        if not isinstance(training_data, dict):
            training_data = {}

        completed_at = record.get("completed_at") or training_data.get("completed_at") or ""
        training_mode = (
            training_data.get("training_mode")
            or training_data.get("training_type")
            or record.get("training_mode")
            or "unknown"
        )
        events = training_data.get("events") or training_data.get("events_triggered") or {}
        quiz_results = training_data.get("quiz_results") or training_data.get("quiz") or []
        quiz_correct, quiz_total = self._count_quiz_results(quiz_results)

        return {
            "username": record.get("username", ""),
            "completed_at": completed_at,
            "training_mode": training_mode,
            "elapsed_time": self._safe_float(training_data.get("elapsed_time")),
            "accuracy": self._safe_float(training_data.get("accuracy")),
            "events": events,
            "events_count": self._count_items(events),
            "quiz_results": quiz_results,
            "quiz_correct": quiz_correct,
            "quiz_total": quiz_total,
            "performance_metrics": training_data.get("performance_metrics") or {},
            "pull_config": training_data.get("pull_config") or {},
            "file_path": record.get("file_path", ""),
            "raw": record,
        }

    def get_user_training_summaries(self, username, limit=None):
        """Return normalized training summaries for one user."""
        records = self.get_user_training_records(username, limit=limit)
        return [self.normalize_training_record(record) for record in records]

    def get_all_users_training_summaries(self):
        """Return normalized training summaries grouped by username."""
        summaries = {}
        if self.data_dir.exists():
            for user_dir in self.data_dir.iterdir():
                if user_dir.is_dir() and (user_dir / "profile.json").exists():
                    summaries[user_dir.name] = self.get_user_training_summaries(user_dir.name)
        return summaries

    def get_training_statistics(self, username):
        """Return aggregate training statistics for one user."""
        records = self.get_user_training_records(username)
        if not records:
            return {
                "total_trainings": 0,
                "total_time": 0,
                "avg_time": 0,
                "last_training": None,
                "best_time": None,
                "details": [],
                "summaries": [],
            }

        summaries = [self.normalize_training_record(record) for record in records]
        times = [item["elapsed_time"] for item in summaries if item.get("elapsed_time")]
        total_trainings = len(records)
        total_time = sum(times)
        avg_time = total_time / total_trainings if total_trainings else 0
        best_time = min(times) if times else None

        return {
            "total_trainings": total_trainings,
            "total_time": total_time,
            "avg_time": avg_time,
            "last_training": records[0] if records else None,
            "best_time": best_time,
            "details": records,
            "summaries": summaries,
        }

    def get_all_users_statistics(self):
        """Return aggregate statistics for every user directory with a profile."""
        all_stats = {}
        if self.data_dir.exists():
            for user_dir in self.data_dir.iterdir():
                if user_dir.is_dir() and (user_dir / "profile.json").exists():
                    all_stats[user_dir.name] = self.get_training_statistics(user_dir.name)
        return all_stats

    def delete_training_record(self, username, filename):
        """Delete a specific training record by filename."""
        logs_dir = self.get_user_training_log_path(username)
        filepath = logs_dir / filename

        if filepath.exists():
            filepath.unlink()
            print(f"[TrainingRecordManager] Training record deleted: {filepath}")
            return True
        return False

    def _safe_float(self, value, default=0.0):
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _count_items(self, value):
        if isinstance(value, dict):
            return len(value)
        if isinstance(value, list):
            return len(value)
        return 0

    def _count_quiz_results(self, quiz_results):
        if isinstance(quiz_results, dict):
            items = quiz_results.get("answers") or quiz_results.get("results") or []
        else:
            items = quiz_results

        if not isinstance(items, list):
            return 0, 0

        total = len(items)
        correct = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("is_correct") is True or item.get("correct") is True:
                correct += 1
        return correct, total


_record_manager = None


def get_training_record_manager(data_dir="data"):
    """Return the process-wide training record manager."""
    global _record_manager
    if _record_manager is None:
        _record_manager = TrainingRecordManager(data_dir)
    return _record_manager

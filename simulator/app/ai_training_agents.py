"""
Compatibility wrappers for training-analysis agents.

The UI imports this module directly. Keep this file small and stable while the
actual graph logic evolves in ai_training_graph.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.ai_training_graph import TrainingAnalysisGraph


class StudentTrainingAgent:
    def __init__(self, graph: Optional[TrainingAnalysisGraph] = None, enable_llm: bool = True):
        self.graph = graph or TrainingAnalysisGraph(enable_llm=enable_llm)

    def analyze_training(
        self,
        username: str,
        latest_record: Dict[str, Any],
        recent_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return self.graph.analyze(username, latest_record, recent_records or [])

    def summarize_after_training(
        self,
        username: str,
        latest_record: Dict[str, Any],
        recent_records: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        result = self.analyze_training(username, latest_record, recent_records)
        return result.get("final_student_report") or "AI Student Debrief\n\nNo summary was generated."


class TeacherTrainingAgent:
    def __init__(self, graph: Optional[TrainingAnalysisGraph] = None, enable_llm: bool = True):
        self.graph = graph or TrainingAnalysisGraph(enable_llm=enable_llm)

    def analyze_student(
        self,
        student_username: str,
        latest_record: Optional[Dict[str, Any]] = None,
        recent_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if latest_record is None:
            latest_record, recent_records = self._load_latest_records(student_username)
        return self.graph.analyze(student_username, latest_record or {}, recent_records or [])

    def generate_teaching_advice(
        self,
        student_username: str,
        latest_record: Optional[Dict[str, Any]] = None,
        recent_records: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        result = self.analyze_student(student_username, latest_record, recent_records)
        return result.get("final_teacher_report") or "AI Teacher Training Advisor\n\nNo advice was generated."

    def _load_latest_records(self, student_username: str):
        try:
            from app.training_records import get_training_record_manager

            manager = get_training_record_manager()
            records = manager.get_user_training_records(student_username, limit=6)
        except Exception:
            records = []

        if not records:
            return {}, []
        return records[0], records[1:]


def create_student_training_agent(enable_llm: bool = True) -> StudentTrainingAgent:
    return StudentTrainingAgent(enable_llm=enable_llm)


def create_teacher_training_agent(enable_llm: bool = True) -> TeacherTrainingAgent:
    return TeacherTrainingAgent(enable_llm=enable_llm)


def create_training_analysis_graph(enable_llm: bool = True) -> TrainingAnalysisGraph:
    return TrainingAnalysisGraph(enable_llm=enable_llm)

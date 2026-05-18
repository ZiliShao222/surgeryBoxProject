from __future__ import annotations

from typing import Dict, List, Tuple

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.i18n import get_language, language_options, set_language, tr, tr_training_label
from app.ui.ai_report_widgets import AIReportWorker, AiLoadingIndicator
from app.ui.theme import Theme


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class TeacherShell(QWidget):
    """Teacher-facing console with class progress and AI coaching advice."""

    def __init__(self, user, on_logout, on_toggle_theme, parent=None):
        super().__init__(parent)
        self.user = user
        self.on_logout = on_logout
        self.on_toggle_theme = on_toggle_theme
        self.theme = Theme("light")
        self.theme_names = ("light", "dark")
        self._student_rows: Dict[str, Dict] = {}

        self._build_ui()
        self.apply_theme(self.theme)
        QTimer.singleShot(100, self.refresh_data)

    def start_welcome(self):
        self.refresh_data()

    def apply_theme(self, theme: Theme):
        self.theme = theme
        self._apply_styles()

    def _palette(self):
        if self.theme.name == "dark":
            return {
                "bg": "#101923",
                "panel": "#172433",
                "panel_2": "#1D3045",
                "border": "#31506E",
                "text": "#EEF7FF",
                "muted": "#ABC2D8",
                "accent": "#5BB8A8",
                "accent_2": "#F0B85B",
                "soft": "rgba(91, 184, 168, 0.16)",
            }
        return {
            "bg": "#F3F8F6",
            "panel": "#FFFFFF",
            "panel_2": "#E9F5F2",
            "border": "#C9DFD9",
            "text": "#18312E",
            "muted": "#5B716D",
            "accent": "#218C7E",
            "accent_2": "#C98222",
            "soft": "rgba(33, 140, 126, 0.12)",
        }

    def _build_ui(self):
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(28, 24, 28, 24)
        self.root.setSpacing(18)

        top = QHBoxLayout()
        top.setSpacing(12)
        title_box = QVBoxLayout()
        self.title = QLabel(tr("teacher.title"))
        self.title.setFont(QFont("Aptos Display", 26, QFont.Bold))
        self.subtitle = QLabel(tr("teacher.subtitle"))
        self.subtitle.setFont(QFont("Aptos", 12))
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        top.addLayout(title_box, 1)

        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("TeacherLanguageCombo")
        for code, label in language_options():
            self.lang_combo.addItem(label, code)
        current_lang = get_language()
        for idx in range(self.lang_combo.count()):
            if self.lang_combo.itemData(idx) == current_lang:
                self.lang_combo.setCurrentIndex(idx)
                break
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)

        self.theme_btn = QPushButton(tr("common.switch_theme"))
        self.refresh_btn = QPushButton(tr("common.refresh"))
        self.logout_btn = QPushButton(tr("common.logout"))
        self.theme_btn.clicked.connect(self.on_toggle_theme)
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.logout_btn.clicked.connect(self.on_logout)
        top.addWidget(self.lang_combo)
        top.addWidget(self.theme_btn)
        top.addWidget(self.refresh_btn)
        top.addWidget(self.logout_btn)
        self.root.addLayout(top)

        overview = QHBoxLayout()
        overview.setSpacing(14)
        self.card_students = self._metric_card(tr("teacher.students"), "0")
        self.card_with_records = self._metric_card(tr("teacher.with_records"), "0")
        self.card_trainings = self._metric_card(tr("teacher.trainings"), "0")
        self.card_dressing = self._metric_card(tr("teacher.dressing_changes"), "0")
        self.card_accuracy = self._metric_card(tr("teacher.avg_accuracy"), "0%")
        for card in (self.card_students, self.card_with_records, self.card_trainings, self.card_dressing, self.card_accuracy):
            overview.addWidget(card["frame"])
        self.root.addLayout(overview)

        body = QHBoxLayout()
        body.setSpacing(16)

        left = QFrame()
        left.setObjectName("TeacherPanel")
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(16, 16, 16, 16)
        left_l.setSpacing(10)
        self.student_list_title = QLabel(tr("teacher.student_progress"))
        self.student_list_title.setFont(QFont("Aptos", 15, QFont.Bold))
        self.student_list = QListWidget()
        self.student_list.currentItemChanged.connect(self._on_student_selected)
        left_l.addWidget(self.student_list_title)
        left_l.addWidget(self.student_list, 1)
        body.addWidget(left, 1)

        right = QFrame()
        right.setObjectName("TeacherPanel")
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(18, 18, 18, 18)
        right_l.setSpacing(12)

        self.student_title = QLabel(tr("teacher.select_student"))
        self.student_title.setFont(QFont("Aptos Display", 20, QFont.Bold))
        self.student_snapshot = QTextEdit()
        self.student_snapshot.setReadOnly(True)
        self.student_snapshot.setMaximumHeight(150)

        action_row = QHBoxLayout()
        self.generate_advice_btn = QPushButton(tr("teacher.generate_advice"))
        self.generate_advice_btn.clicked.connect(self.generate_teacher_advice)
        action_row.addWidget(self.generate_advice_btn)
        action_row.addStretch(1)

        self.teacher_ai_advice = QTextEdit()
        self.teacher_ai_advice.setReadOnly(True)
        self.teacher_ai_advice.setText(tr("teacher.placeholder"))
        self.teacher_ai_loading = AiLoadingIndicator()
        self.teacher_ai_loading.setVisible(False)

        right_l.addWidget(self.student_title)
        right_l.addWidget(self.student_snapshot)
        right_l.addLayout(action_row)
        right_l.addWidget(self.teacher_ai_loading)
        right_l.addWidget(self.teacher_ai_advice, 1)
        body.addWidget(right, 2)

        self.root.addLayout(body, 1)

    def _metric_card(self, label: str, value: str):
        frame = QFrame()
        frame.setObjectName("TeacherMetricCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)
        value_label = QLabel(value)
        value_label.setFont(QFont("Aptos Display", 24, QFont.Bold))
        label_label = QLabel(label)
        label_label.setFont(QFont("Aptos", 11))
        layout.addWidget(value_label)
        layout.addWidget(label_label)
        return {"frame": frame, "value": value_label, "label": label_label}

    def _apply_styles(self):
        p = self._palette()
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {p['bg']};
                color: {p['text']};
                font-family: 'Aptos', 'Segoe UI', Arial;
            }}
            QLabel {{
                background: transparent;
                color: {p['text']};
            }}
            QLabel#Muted {{
                color: {p['muted']};
            }}
            QFrame#TeacherPanel, QFrame#TeacherMetricCard {{
                background: {p['panel']};
                border: 1px solid {p['border']};
                border-radius: 18px;
            }}
            QPushButton {{
                background: {p['panel_2']};
                color: {p['text']};
                border: 1px solid {p['border']};
                border-radius: 13px;
                padding: 10px 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {p['soft']};
                border-color: {p['accent']};
            }}
            QComboBox {{
                background: {p['panel_2']};
                color: {p['text']};
                border: 1px solid {p['border']};
                border-radius: 13px;
                padding: 8px 26px 8px 12px;
                font-weight: 700;
                min-width: 92px;
            }}
            QComboBox:hover {{
                background: {p['soft']};
                border-color: {p['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox QAbstractItemView {{
                background: {p['panel']};
                color: {p['text']};
                border: 1px solid {p['border']};
                selection-background-color: {p['accent']};
            }}
            QListWidget, QTextEdit {{
                background: {p['panel_2']};
                color: {p['text']};
                border: 1px solid {p['border']};
                border-radius: 14px;
                padding: 10px;
                selection-background-color: {p['accent']};
                selection-color: white;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 12px;
                margin: 6px 3px 6px 3px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {p['accent']};
                border-radius: 5px;
                min-height: 42px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {p['accent_2']};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
                background: transparent;
                border: none;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 10px;
                margin: 3px 6px 3px 6px;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {p['accent']};
                border-radius: 4px;
                min-width: 42px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {p['accent_2']};
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0px;
                background: transparent;
                border: none;
            }}
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
            """
        )
        self.subtitle.setStyleSheet(f"color: {p['muted']}; background: transparent;")
        self.student_list_title.setStyleSheet("background: transparent;")
        if hasattr(self, "teacher_ai_loading"):
            self.teacher_ai_loading.apply_palette(p)
        for card in (self.card_students, self.card_with_records, self.card_trainings, self.card_dressing, self.card_accuracy):
            card["frame"].setStyleSheet("")
            card["value"].setStyleSheet(f"color: {p['accent']}; background: transparent;")
            card["label"].setStyleSheet(f"color: {p['muted']}; background: transparent;")

    def _on_language_changed(self):
        if not hasattr(self, "lang_combo"):
            return
        set_language(self.lang_combo.currentData())
        self._apply_language_texts()
        self.refresh_data()

    def _apply_language_texts(self):
        self.title.setText(tr("teacher.title"))
        self.subtitle.setText(tr("teacher.subtitle"))
        self.theme_btn.setText(tr("common.switch_theme"))
        self.refresh_btn.setText(tr("common.refresh"))
        self.logout_btn.setText(tr("common.logout"))
        self.card_students["label"].setText(tr("teacher.students"))
        self.card_with_records["label"].setText(tr("teacher.with_records"))
        self.card_trainings["label"].setText(tr("teacher.trainings"))
        self.card_dressing["label"].setText(tr("teacher.dressing_changes"))
        self.card_accuracy["label"].setText(tr("teacher.avg_accuracy"))
        self.student_list_title.setText(tr("teacher.student_progress"))
        self.generate_advice_btn.setText(tr("teacher.generate_advice"))
        if self.student_title.text() == "Select a student" or self.student_title.text() == "请选择学生":
            self.student_title.setText(tr("teacher.select_student"))
        if self.teacher_ai_advice.toPlainText().strip() in {
            "Select a student and generate teaching advice after at least one training record is available.",
            "选择学生后，可在至少有一条训练记录时生成教学建议。",
        }:
            self.teacher_ai_advice.setText(tr("teacher.placeholder"))

    def refresh_data(self):
        students = self._student_names()
        self._student_rows = {}

        total_trainings = 0
        total_dressing_changes = 0
        with_records = 0
        all_accuracies: List[float] = []

        self.student_list.blockSignals(True)
        self.student_list.clear()

        for username in students:
            row = self._student_row(username)
            self._student_rows[username] = row
            total_trainings += row["total_trainings"]
            total_dressing_changes += row.get("change_dressing_count", 0)
            if row["total_trainings"] > 0:
                with_records += 1
            all_accuracies.extend(row["accuracies"])

            label = tr(
                "teacher.student_row",
                username=username,
                trainings=row["total_trainings"],
                dressing=row.get("change_dressing_count", 0),
                accuracy=row["avg_accuracy"],
            )
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, username)
            self.student_list.addItem(item)

        self.student_list.blockSignals(False)

        avg_accuracy = sum(all_accuracies) / len(all_accuracies) if all_accuracies else 0
        self.card_students["value"].setText(str(len(students)))
        self.card_with_records["value"].setText(str(with_records))
        self.card_trainings["value"].setText(str(total_trainings))
        self.card_dressing["value"].setText(str(total_dressing_changes))
        self.card_accuracy["value"].setText(f"{avg_accuracy:.0f}%")

        if self.student_list.count() > 0 and self.student_list.currentRow() < 0:
            self.student_list.setCurrentRow(0)
        elif self.student_list.currentItem():
            self._on_student_selected(self.student_list.currentItem(), None)

    def _student_names(self) -> List[str]:
        try:
            from app.auth import ACCOUNTS

            return sorted([name for name, (_, role) in ACCOUNTS.items() if role == "trainee"])
        except Exception:
            return []

    def _student_row(self, username: str) -> Dict:
        records = []
        stats = {}
        try:
            from app.training_records import get_training_record_manager

            manager = get_training_record_manager()
            stats = manager.get_training_statistics(username)
            records = stats.get("details", [])
        except Exception as exc:
            print(f"[TeacherShell] Failed to load records for {username}: {exc}")

        accuracies = []
        for record in records:
            data = record.get("training_data", {}) if isinstance(record, dict) else {}
            mode = data.get("training_mode") or data.get("training_type") or "unknown"
            if mode == "change_dressing":
                continue
            try:
                accuracy = float(data.get("accuracy", 0))
                if accuracy > 0:
                    accuracies.append(accuracy)
            except (TypeError, ValueError):
                pass

        avg_accuracy = stats.get("avg_accuracy") or (sum(accuracies) / len(accuracies) if accuracies else 0)
        return {
            "username": username,
            "records": records,
            "total_trainings": len(records),
            "change_dressing_count": stats.get("change_dressing_count", 0),
            "training_type_counts": stats.get("training_type_counts", {}),
            "accuracies": accuracies,
            "avg_accuracy": avg_accuracy,
        }

    def _on_student_selected(self, current, previous):
        if current is None:
            return
        username = current.data(Qt.UserRole)
        row = self._student_rows.get(username) or self._student_row(username)
        self.student_title.setText(username)
        self.student_snapshot.setText(self._format_student_snapshot(row))

    def _format_student_snapshot(self, row: Dict) -> str:
        records = row.get("records", [])
        if not records:
            return tr("teacher.no_records")

        lines = [
            tr("teacher.total_trainings", count=row.get("total_trainings", 0)),
            tr("teacher.dressing_count", count=row.get("change_dressing_count", 0)),
            tr("teacher.avg_accuracy_scored", accuracy=row.get("avg_accuracy", 0)),
            "",
            tr("teacher.recent_attempts"),
        ]
        for record in records[:5]:
            data = record.get("training_data", {})
            completed_at = record.get("completed_at", "-")
            mode = data.get("training_mode") or data.get("training_type") or "unknown"
            elapsed = _as_float(data.get("elapsed_time", 0))
            accuracy = _as_float(data.get("accuracy", 0))
            if mode == "change_dressing":
                completed = int(_as_float(data.get("phase4_events_completed") or len(data.get("events_results", [])) or 0))
                expected = int(_as_float(data.get("expected_events") or completed or 3))
                result = f"{completed}/{expected} {tr('student.steps')}"
            else:
                result = f"{accuracy:.0f}%"
            label = tr_training_label(mode)
            if label.startswith("training."):
                label = mode
            lines.append(f"- {completed_at} | {label} | {elapsed:.1f}s | {result}")
        return "\n".join(lines)

    def generate_teacher_advice(self):
        if getattr(self, "_teacher_ai_worker", None) and self._teacher_ai_worker.isRunning():
            return

        item = self.student_list.currentItem()
        if item is None:
            self.teacher_ai_advice.setText(tr("teacher.select_student_first"))
            return

        username = item.data(Qt.UserRole)
        row = self._student_rows.get(username) or self._student_row(username)
        records = row.get("records", [])
        if not records:
            self.teacher_ai_advice.setText(tr("teacher.no_records_for_student"))
            return

        self.generate_advice_btn.setEnabled(False)
        self.teacher_ai_loading.start(
            tr("ai.loading_title"),
            tr("ai.teacher_loading_detail"),
        )
        self.teacher_ai_advice.clear()
        QApplication.processEvents()

        def build_report():
            from app.ai_training_agents import create_teacher_training_agent

            agent = create_teacher_training_agent()
            return agent.generate_teaching_advice(username, records[0], records[1:6])

        def on_result(advice):
            self._set_ai_report_content(self.teacher_ai_advice, advice)

        def on_error(message):
            print(f"[TeacherShell] AI advice failed: {message}")
            self.teacher_ai_advice.setText(tr("teacher.ai_failed"))

        def on_finished():
            self.teacher_ai_loading.stop()
            self.generate_advice_btn.setEnabled(True)
            self._teacher_ai_worker = None

        self._teacher_ai_worker = AIReportWorker(build_report, self)
        self._teacher_ai_worker.result_ready.connect(on_result)
        self._teacher_ai_worker.error_ready.connect(on_error)
        self._teacher_ai_worker.finished.connect(on_finished)
        self._teacher_ai_worker.start()

    def _set_ai_report_content(self, widget, content):
        try:
            if hasattr(widget, "setMarkdown"):
                widget.setMarkdown(content)
            else:
                widget.setPlainText(content)
        except Exception:
            try:
                widget.setPlainText(content)
            except Exception:
                widget.setText(content)

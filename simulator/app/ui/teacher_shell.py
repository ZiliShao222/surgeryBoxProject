import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.auth import ACCOUNTS
from app.training_records import get_training_record_manager


class TeacherShell(QWidget):
    """Teacher-facing shell.

    The teacher side intentionally avoids camera, simulator, and hardware modules.
    It focuses on class-level training oversight and teaching workflow.
    """

    def __init__(self, user, on_logout, on_toggle_theme, parent=None):
        super().__init__(parent)
        self.setObjectName("TeacherShell")
        self.user = user
        self.on_logout = on_logout
        self.on_toggle_theme = on_toggle_theme
        self.record_manager = get_training_record_manager()
        self.student_rows = []
        self.records_by_user = {}

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.setStyleSheet(
            """
            QWidget#TeacherShell {
                background: #eef6f1;
                color: #173b2f;
                font-family: 'Segoe UI', Arial;
            }
            QFrame#TeacherTopBar, QFrame#TeacherCard, QFrame#TeacherMenu {
                background: rgba(255, 255, 255, 0.86);
                border: 1px solid rgba(32, 92, 72, 0.12);
                border-radius: 14px;
            }
            QLabel#TeacherTitle {
                color: #12392d;
                font-size: 28px;
                font-weight: 800;
            }
            QLabel#TeacherSubtitle {
                color: #4c6b60;
                font-size: 13px;
            }
            QLabel#CardValue {
                color: #0f513f;
                font-size: 28px;
                font-weight: 800;
            }
            QLabel#CardLabel {
                color: #60786f;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton {
                background: #1f7a5c;
                color: white;
                border: none;
                border-radius: 9px;
                padding: 8px 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #17664c;
            }
            QListWidget {
                border: none;
                background: transparent;
                outline: none;
            }
            QListWidget::item {
                padding: 13px 12px;
                border-radius: 10px;
                color: #173b2f;
                font-size: 15px;
                font-weight: 650;
            }
            QListWidget::item:selected {
                background: rgba(31, 122, 92, 0.14);
                border-left: 4px solid #1f7a5c;
            }
            QTableWidget {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(32, 92, 72, 0.14);
                border-radius: 10px;
                gridline-color: rgba(32, 92, 72, 0.12);
            }
            QHeaderView::section {
                background: #d9eee5;
                color: #173b2f;
                border: none;
                padding: 8px;
                font-weight: 800;
            }
            QTextEdit {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(32, 92, 72, 0.14);
                border-radius: 10px;
                padding: 10px;
                color: #173b2f;
            }
            """
        )

        root.addWidget(self._build_top_bar())

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        body.addWidget(self._build_menu(), 0)

        self.stack = QStackedWidget()
        self.dashboard_page = self._build_dashboard_page()
        self.records_page = self._build_records_page()
        self.assignments_page = self._build_assignments_page()
        self.notes_page = self._build_notes_page()
        for page in (
            self.dashboard_page,
            self.records_page,
            self.assignments_page,
            self.notes_page,
        ):
            self.stack.addWidget(page)
        body.addWidget(self.stack, 1)

        self.menu_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.menu_list.setCurrentRow(0)

    def _build_top_bar(self):
        top = QFrame()
        top.setObjectName("TeacherTopBar")
        layout = QHBoxLayout(top)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        title_box = QVBoxLayout()
        title = QLabel("Teacher Console")
        title.setObjectName("TeacherTitle")
        subtitle = QLabel("Class overview, student progress, and teaching workflow")
        subtitle.setObjectName("TeacherSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)
        layout.addStretch(1)

        user_label = QLabel(f"{self.user.username} | trainer")
        user_label.setObjectName("TeacherSubtitle")
        layout.addWidget(user_label)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(refresh_btn)

        theme_btn = QPushButton("Theme")
        theme_btn.clicked.connect(self.on_toggle_theme)
        layout.addWidget(theme_btn)

        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.on_logout)
        layout.addWidget(logout_btn)

        return top

    def _build_menu(self):
        menu = QFrame()
        menu.setObjectName("TeacherMenu")
        menu.setFixedWidth(250)
        layout = QVBoxLayout(menu)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        label = QLabel("Teacher Modules")
        label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        label.setStyleSheet("color: #12392d;")
        layout.addWidget(label)

        self.menu_list = QListWidget()
        for text in ("Dashboard", "Student Records", "Assignments", "Teaching Notes"):
            self.menu_list.addItem(QListWidgetItem(text))
        layout.addWidget(self.menu_list, 1)

        hint = QLabel("No camera or hardware connection is opened in teacher mode.")
        hint.setWordWrap(True)
        hint.setObjectName("TeacherSubtitle")
        layout.addWidget(hint)

        return menu

    def _build_dashboard_page(self):
        page = self._page_frame()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        layout.addWidget(self._page_title("Dashboard", "A quick snapshot of the class training status."))

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.total_students_value = self._metric_card(cards, "Students", "0")
        self.active_students_value = self._metric_card(cards, "With Records", "0")
        self.total_trainings_value = self._metric_card(cards, "Trainings", "0")
        self.avg_accuracy_value = self._metric_card(cards, "Avg Accuracy", "0%")
        layout.addLayout(cards)

        recent_title = QLabel("Recent Training Activity")
        recent_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(recent_title)

        self.recent_activity = QTextEdit()
        self.recent_activity.setReadOnly(True)
        layout.addWidget(self.recent_activity, 1)
        return page

    def _build_records_page(self):
        page = self._page_frame()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        layout.addWidget(
            self._page_title(
                "Student Records",
                "Students are listed separately from the student training interface.",
            )
        )

        self.records_table = QTableWidget(0, 7)
        self.records_table.setHorizontalHeaderLabels(
            ["Student", "Role", "Trainings", "Avg Time", "Best Time", "Avg Accuracy", "Last Training"]
        )
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.verticalHeader().setVisible(False)
        self.records_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.records_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.records_table.itemSelectionChanged.connect(self._show_selected_student_detail)
        layout.addWidget(self.records_table, 2)

        detail_title = QLabel("Selected Student Detail")
        detail_title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        layout.addWidget(detail_title)

        self.student_detail = QTextEdit()
        self.student_detail.setReadOnly(True)
        layout.addWidget(self.student_detail, 1)
        return page

    def _build_assignments_page(self):
        page = self._page_frame()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        layout.addWidget(
            self._page_title(
                "Assignments",
                "This is the teacher-side placeholder for assigning training tasks later.",
            )
        )

        text = QTextEdit()
        text.setReadOnly(True)
        text.setText(
            "Planned teacher workflow:\n\n"
            "1. Create a training task, for example epidural catheter removal.\n"
            "2. Assign it to one or more students.\n"
            "3. Let students complete the task on the student side.\n"
            "4. Review completion time, accuracy, quiz results, and notes here.\n\n"
            "Current version: role-separated shell is ready; networked assignment sync is not implemented yet."
        )
        layout.addWidget(text, 1)
        return page

    def _build_notes_page(self):
        page = self._page_frame()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        layout.addWidget(
            self._page_title(
                "Teaching Notes",
                "A lightweight teacher-only area for class guidance and follow-up notes.",
            )
        )

        text = QTextEdit()
        text.setReadOnly(True)
        text.setText(
            "Teacher-side responsibilities in this architecture:\n\n"
            "- Review student training records.\n"
            "- Track repeated mistakes and completion trends.\n"
            "- Prepare teaching feedback after students finish training.\n"
            "- Avoid opening the simulator camera or hardware connection on the teacher device.\n\n"
            "Next step: add persistent notes and a real student/task data sync layer."
        )
        layout.addWidget(text, 1)
        return page

    def _page_frame(self):
        frame = QFrame()
        frame.setObjectName("TeacherCard")
        return frame

    def _page_title(self, title, subtitle):
        box = QFrame()
        box.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title_label.setStyleSheet("color: #12392d;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("TeacherSubtitle")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return box

    def _metric_card(self, parent_layout, label, value):
        card = QFrame()
        card.setObjectName("TeacherCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        value_label = QLabel(value)
        value_label.setObjectName("CardValue")
        label_label = QLabel(label)
        label_label.setObjectName("CardLabel")
        layout.addWidget(value_label)
        layout.addWidget(label_label)
        parent_layout.addWidget(card)
        return value_label

    def refresh_data(self):
        self.student_rows = self._collect_student_rows()
        self._update_dashboard()
        self._update_records_table()

    def _collect_student_rows(self):
        profiles = self._load_profiles()
        stats_by_user = self.record_manager.get_all_users_statistics()
        student_names = set()

        for username, (_, role) in ACCOUNTS.items():
            if role == "trainee":
                student_names.add(username)

        for username, profile in profiles.items():
            if profile.get("role") == "trainee":
                student_names.add(username)

        rows = []
        self.records_by_user = {}
        for username in sorted(student_names):
            profile = profiles.get(username, {"role": "trainee"})
            stats = stats_by_user.get(username, self._empty_stats())
            records = stats.get("details", [])
            self.records_by_user[username] = records
            rows.append(
                {
                    "username": username,
                    "role": profile.get("role", "trainee"),
                    "total": stats.get("total_trainings", 0),
                    "avg_time": stats.get("avg_time", 0),
                    "best_time": stats.get("best_time"),
                    "avg_accuracy": self._average_accuracy(records),
                    "last_training": self._format_last_training(stats.get("last_training")),
                }
            )
        return rows

    def _load_profiles(self):
        profiles = {}
        data_root = Path("data")
        if not data_root.exists():
            return profiles

        for profile_path in data_root.glob("*/profile.json"):
            try:
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
                username = profile.get("username") or profile_path.parent.name
                profiles[username] = profile
            except Exception as exc:
                print(f"[TeacherShell] Failed to read profile {profile_path}: {exc}")
        return profiles

    def _empty_stats(self):
        return {
            "total_trainings": 0,
            "total_time": 0,
            "avg_time": 0,
            "last_training": None,
            "best_time": None,
            "details": [],
        }

    def _average_accuracy(self, records):
        values = []
        for record in records:
            value = record.get("training_data", {}).get("accuracy")
            if isinstance(value, (int, float)):
                values.append(float(value))
        return sum(values) / len(values) if values else 0

    def _format_last_training(self, record):
        if not record:
            return "-"
        raw = record.get("completed_at", "")
        try:
            return datetime.fromisoformat(raw).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return raw[:16] if raw else "-"

    def _format_seconds(self, seconds):
        if seconds is None:
            return "-"
        seconds = int(seconds)
        minutes, sec = divmod(seconds, 60)
        return f"{minutes}m {sec}s" if minutes else f"{sec}s"

    def _update_dashboard(self):
        total_students = len(self.student_rows)
        active_students = sum(1 for row in self.student_rows if row["total"] > 0)
        total_trainings = sum(row["total"] for row in self.student_rows)
        accuracy_values = [row["avg_accuracy"] for row in self.student_rows if row["avg_accuracy"] > 0]
        avg_accuracy = sum(accuracy_values) / len(accuracy_values) if accuracy_values else 0

        self.total_students_value.setText(str(total_students))
        self.active_students_value.setText(str(active_students))
        self.total_trainings_value.setText(str(total_trainings))
        self.avg_accuracy_value.setText(f"{avg_accuracy:.0f}%")

        recent_lines = []
        recent_records = []
        for username, records in self.records_by_user.items():
            for record in records[:3]:
                recent_records.append((username, record))
        recent_records.sort(key=lambda item: item[1].get("completed_at", ""), reverse=True)

        for username, record in recent_records[:12]:
            training = record.get("training_data", {})
            recent_lines.append(
                f"{self._format_last_training(record)} | {username} | "
                f"{training.get('training_mode', 'unknown')} | "
                f"{self._format_seconds(training.get('elapsed_time', 0))} | "
                f"{training.get('accuracy', 0):.0f}%"
            )

        if not recent_lines:
            recent_lines.append("No student training records yet.")
        self.recent_activity.setText("\n".join(recent_lines))

    def _update_records_table(self):
        self.records_table.setRowCount(len(self.student_rows))
        for row_index, row in enumerate(self.student_rows):
            values = [
                row["username"],
                row["role"],
                str(row["total"]),
                self._format_seconds(row["avg_time"]),
                self._format_seconds(row["best_time"]),
                f"{row['avg_accuracy']:.0f}%",
                row["last_training"],
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.records_table.setItem(row_index, col, item)

        if self.student_rows:
            self.records_table.selectRow(0)
        else:
            self.student_detail.setText("No students found.")

    def _show_selected_student_detail(self):
        selected = self.records_table.selectionModel().selectedRows()
        if not selected:
            return

        row = selected[0].row()
        username_item = self.records_table.item(row, 0)
        if username_item is None:
            return

        username = username_item.text()
        records = self.records_by_user.get(username, [])
        lines = [f"Student: {username}", ""]
        if not records:
            lines.append("No training records for this student yet.")
        else:
            lines.append("Recent records:")
            for record in records[:8]:
                training = record.get("training_data", {})
                lines.append(
                    f"- {self._format_last_training(record)} | "
                    f"{training.get('training_mode', 'unknown')} | "
                    f"time {self._format_seconds(training.get('elapsed_time', 0))} | "
                    f"accuracy {training.get('accuracy', 0):.0f}%"
                )
        self.student_detail.setText("\n".join(lines))

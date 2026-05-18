from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QRectF, QThread, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


def _to_qcolor(value: str, fallback: str) -> QColor:
    text = str(value or "").strip()
    if text.lower().startswith("rgba(") and text.endswith(")"):
        try:
            raw = text[text.find("(") + 1 : -1]
            parts = [part.strip() for part in raw.split(",")]
            red, green, blue = [int(float(part)) for part in parts[:3]]
            alpha_raw = float(parts[3]) if len(parts) > 3 else 1.0
            alpha = int(max(0.0, min(1.0, alpha_raw)) * 255)
            return QColor(red, green, blue, alpha)
        except Exception:
            pass

    color = QColor(text)
    return color if color.isValid() else QColor(fallback)


def _palette_value(palette, *keys, default="#4DA3FF"):
    for key in keys:
        value = palette.get(key) if isinstance(palette, dict) else None
        if value:
            return value
    return default


class AIReportWorker(QThread):
    result_ready = Signal(str)
    error_ready = Signal(str)

    def __init__(self, job: Callable[[], str], parent=None):
        super().__init__(parent)
        self._job = job

    def run(self):
        try:
            self.result_ready.emit(str(self._job()))
        except Exception as exc:
            self.error_ready.emit(str(exc))


class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._accent = "#4DA3FF"
        self._track = "rgba(77, 163, 255, 0.18)"
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(34, 34)

    def set_colors(self, accent: str, track: str):
        self._accent = accent
        self._track = track
        self.update()

    def start(self):
        self._timer.start(28)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _rotate(self):
        self._angle = (self._angle - 12) % 360
        self.update()

    def paintEvent(self, _event):
        side = min(self.width(), self.height()) - 6
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        track_pen = QPen(_to_qcolor(self._track, "#B8D8FF"), 4)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        accent_pen = QPen(_to_qcolor(self._accent, "#4DA3FF"), 4)
        accent_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(accent_pen)
        painter.drawArc(rect, self._angle * 16, 115 * 16)


class AiLoadingIndicator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_title = "AI is thinking"
        self._dot_step = 0

        self.spinner = LoadingSpinner(self)
        self.title = QLabel(self._base_title)
        self.detail = QLabel("Building a structured training report")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(self.title)
        text_layout.addWidget(self.detail)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        layout.addWidget(self.spinner, 0, Qt.AlignVCenter)
        layout.addLayout(text_layout, 1)

        self._text_timer = QTimer(self)
        self._text_timer.timeout.connect(self._tick)
        self.setVisible(False)

    def apply_palette(self, palette):
        bg = _palette_value(palette, "accent_soft", "soft", "panel_2", default="rgba(77, 163, 255, 0.14)")
        border = _palette_value(palette, "border", default="rgba(77, 163, 255, 0.32)")
        text = _palette_value(palette, "text", default="#003366")
        muted = _palette_value(palette, "muted", default="#446A8F")
        accent = _palette_value(palette, "accent", default="#4DA3FF")
        track = _palette_value(palette, "soft", "accent_soft", default="rgba(77, 163, 255, 0.18)")

        self.setStyleSheet(
            f"""
            QFrame {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )
        self.title.setStyleSheet(f"color: {text}; font-size: 15px; font-weight: 800;")
        self.detail.setStyleSheet(f"color: {muted}; font-size: 12px; font-weight: 600;")
        self.spinner.set_colors(accent, track)

    def start(self, title="AI is thinking", detail="Building a structured training report"):
        self._base_title = title
        self._dot_step = 0
        self.title.setText(title)
        self.detail.setText(detail)
        self.setVisible(True)
        self.spinner.start()
        self._text_timer.start(360)

    def stop(self):
        self._text_timer.stop()
        self.spinner.stop()
        self.setVisible(False)

    def _tick(self):
        self._dot_step = (self._dot_step + 1) % 4
        self.title.setText(f"{self._base_title}{'.' * self._dot_step}")

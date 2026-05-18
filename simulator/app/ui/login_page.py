from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QApplication, QComboBox
)

from types import SimpleNamespace
from pathlib import Path

from app.config import APP_NAME
from app.auth import authenticate, register_user
from app.i18n import get_language, language_options, set_language, tr


class LoginPage(QWidget):
    logged_in = Signal(object)

    def __init__(self):
        super().__init__()
        self.mode = "login"
        self._setup_window()
        self._build_ui()

    # --------------------------------------------------
    # Window: real fullscreen (game style)
    # --------------------------------------------------
    def _setup_window(self):
        # Only make it a frameless fullscreen window when used standalone
        if self.parent() is None:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
            self.showFullScreen()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # ===== Background =====
        self.bg_label = QLabel()
        background_path = self._background_path()
        pixmap = QPixmap(str(background_path))
        if pixmap.isNull():
            print(f"[LoginPage] Failed to load background: {background_path}")
        else:
            print(f"[LoginPage] Loaded background: {background_path}")
        self.bg_label.setPixmap(pixmap)
        self.bg_label.setScaledContents(True)
        root.addWidget(self.bg_label)

        # ===== Overlay =====
        self.overlay = QFrame(self.bg_label)
        self.overlay.setGeometry(self.rect())
        self.overlay.setStyleSheet("QFrame { background: rgba(255,255,255,0.25); }")

        overlay_l = QVBoxLayout(self.overlay)
        overlay_l.setContentsMargins(32, 24, 32, 24)

        # ===== Top bar =====
        top = QHBoxLayout()
        top.addStretch()

        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("LoginLanguageCombo")
        for code, label in language_options():
            self.lang_combo.addItem(label, code)
        current_lang = get_language()
        for idx in range(self.lang_combo.count()):
            if self.lang_combo.itemData(idx) == current_lang:
                self.lang_combo.setCurrentIndex(idx)
                break
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255,255,255,0.45);
                border: 1px solid rgba(77,163,255,0.35);
                border-radius: 14px;
                padding: 5px 24px 5px 10px;
                color: #003366;
                font-family: 'Segoe UI', Arial;
                font-size: 13px;
                min-width: 88px;
            }
            QComboBox::drop-down { border: none; width: 22px; }
        """)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        top.addWidget(self.lang_combo)

        self.exit_btn = QPushButton(tr("login.exit"))
        self.exit_btn.setCursor(Qt.PointingHandCursor)
        f = QFont("Segoe Script", 20, QFont.Bold)
        f.setItalic(True)
        self.exit_btn.setFont(f)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #003366;
                font-family: 'Segoe Script', 'Brush Script MT', cursive;
                font-size: 20px;
            }
            QPushButton:hover {
                color: #001a33;
            }
        """)
        self.exit_btn.clicked.connect(QApplication.quit)
        top.addWidget(self.exit_btn)

        overlay_l.addLayout(top)
        overlay_l.addStretch(2)
        overlay_l.addSpacing(320)

        # ===== Login Card =====
        card = QFrame()
        card.setFixedWidth(420)
        card.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.4);
                border-radius: 20px;
            }
        """)

        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(32, 32, 32, 32)
        card_l.setSpacing(18)

        # Title
        self.title = QLabel(tr("login.title"))
        self.title.setAlignment(Qt.AlignCenter)
        f_title = QFont("Segoe Script", 28, QFont.Bold)
        f_title.setItalic(True)
        self.title.setFont(f_title)
        self.title.setStyleSheet("""
            color: #003366;
            font-family: 'Segoe Script', 'Brush Script MT', cursive;
            font-size: 28px;
        """)

        # Username
        self.user = QLineEdit()
        self.user.setPlaceholderText(tr("login.username"))
        self._style_input(self.user)

        # Password
        self.pw = QLineEdit()
        self.pw.setPlaceholderText(tr("login.password"))
        self.pw.setEchoMode(QLineEdit.Password)
        self._style_input(self.pw)

        # Confirm password, only used while registering.
        self.confirm_pw = QLineEdit()
        self.confirm_pw.setPlaceholderText(tr("login.confirm_password"))
        self.confirm_pw.setEchoMode(QLineEdit.Password)
        self._style_input(self.confirm_pw)
        self.confirm_pw.setVisible(False)

        # Teacher secret key, only used while registering teachers.
        self.secret_key = QLineEdit()
        self.secret_key.setPlaceholderText(tr("login.teacher_secret_key"))
        self.secret_key.setEchoMode(QLineEdit.Password)
        self._style_input(self.secret_key)
        self.secret_key.setVisible(False)

        # Error
        self.err = QLabel("")
        self.err.setVisible(False)
        self.err.setAlignment(Qt.AlignCenter)
        self.err.setStyleSheet("""
            QLabel {
                color: #d12b2b;
                font-size: 13px;
            }
        """)

        # Login button
        self.primary_btn = QPushButton(tr("login.title"))
        self.primary_btn.setCursor(Qt.PointingHandCursor)
        self.primary_btn.setFixedHeight(44)
        self.primary_btn.setFont(QFont("Segoe UI", 15))
        self.primary_btn.setStyleSheet("""
            QPushButton {
                background-color: #4da3ff;
                color: white;
                border-radius: 22px;
            }
            QPushButton:hover {
                background-color: #3b92ec;
            }
        """)
        self.primary_btn.clicked.connect(self._submit)

        self.register_student_btn = QPushButton(tr("login.student_register"))
        self.register_teacher_btn = QPushButton(tr("login.teacher_register"))
        self.back_login_btn = QPushButton(tr("login.back_to_login"))
        for btn in (self.register_student_btn, self.register_teacher_btn, self.back_login_btn):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setFont(QFont("Segoe UI", 11))
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.35);
                    border: 1px solid rgba(77,163,255,0.35);
                    color: #003366;
                    border-radius: 16px;
                    padding: 4px 10px;
                }
                QPushButton:hover {
                    background: rgba(77,163,255,0.16);
                }
            """)
        self.register_student_btn.clicked.connect(lambda: self._set_mode("student_register"))
        self.register_teacher_btn.clicked.connect(lambda: self._set_mode("teacher_register"))
        self.back_login_btn.clicked.connect(lambda: self._set_mode("login"))
        self.back_login_btn.setVisible(False)

        # Assemble card
        card_l.addWidget(self.title)
        card_l.addSpacing(6)
        card_l.addWidget(self.user)
        card_l.addWidget(self.pw)
        card_l.addWidget(self.confirm_pw)
        card_l.addWidget(self.secret_key)
        card_l.addWidget(self.err)
        card_l.addSpacing(8)
        card_l.addWidget(self.primary_btn)

        register_l = QHBoxLayout()
        register_l.setSpacing(8)
        register_l.addWidget(self.register_student_btn)
        register_l.addWidget(self.register_teacher_btn)
        register_l.addWidget(self.back_login_btn)
        card_l.addLayout(register_l)

        # Debug button to skip login (development convenience)
        self.debug_btn = QPushButton(tr("login.debug"))
        self.debug_btn.setCursor(Qt.PointingHandCursor)
        self.debug_btn.setFixedHeight(36)
        self.debug_btn.setFont(QFont("Segoe Script", 14, QFont.Bold))
        self.debug_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #003366;
                font-family: 'Segoe Script', 'Brush Script MT', cursive;
                font-size: 14px;
            }
            QPushButton:hover { color: #001a33; }
        """)
        self.debug_btn.clicked.connect(self._debug_login)
        card_l.addSpacing(6)
        card_l.addWidget(self.debug_btn)

        overlay_l.addWidget(card, alignment=Qt.AlignCenter)
        overlay_l.addStretch(3)

        # Keyboard
        self.user.returnPressed.connect(self._submit)
        self.pw.returnPressed.connect(self._submit)
        self.confirm_pw.returnPressed.connect(self._submit)
        self.secret_key.returnPressed.connect(self._submit)

    def _on_language_changed(self):
        if not hasattr(self, "lang_combo"):
            return
        set_language(self.lang_combo.currentData())
        self._apply_language_texts()

    def _apply_language_texts(self):
        if hasattr(self, "lang_combo"):
            current_lang = get_language()
            self.lang_combo.blockSignals(True)
            for idx in range(self.lang_combo.count()):
                if self.lang_combo.itemData(idx) == current_lang:
                    self.lang_combo.setCurrentIndex(idx)
                    break
            self.lang_combo.blockSignals(False)
        if hasattr(self, "exit_btn"):
            self.exit_btn.setText(tr("login.exit"))
        if hasattr(self, "debug_btn"):
            self.debug_btn.setText(tr("login.debug"))
        self.user.setPlaceholderText(tr("login.username"))
        self.pw.setPlaceholderText(tr("login.password"))
        self.confirm_pw.setPlaceholderText(tr("login.confirm_password"))
        self.secret_key.setPlaceholderText(tr("login.teacher_secret_key"))
        self.register_student_btn.setText(tr("login.student_register"))
        self.register_teacher_btn.setText(tr("login.teacher_register"))
        self.back_login_btn.setText(tr("login.back_to_login"))
        self._set_mode_texts()

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------
    def _background_path(self):
        """Prefer the project-level generated background, with the old asset as fallback."""
        project_root = Path(__file__).resolve().parents[3]
        candidates = [
            project_root / "back.png",
            project_root / "back (2).png",
            Path.cwd() / "back.png",
            Path.cwd() / "back (2).png",
            Path.cwd().parent / "back.png",
            Path.cwd().parent / "back (2).png",
            Path.cwd() / "assets" / "background.jpg",
            project_root / "simulator" / "assets" / "background.jpg",
        ]
        for path in candidates:
            if path.exists():
                return path
        return candidates[-1]

    def _style_input(self, w):
        w.setFixedHeight(42)
        w.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cfe3ff;
                border-radius: 21px;
                padding-left: 14px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4da3ff;
            }
        """)

    def _set_message(self, text, is_error=True):
        self.err.setText(text)
        self.err.setVisible(bool(text))
        color = "#d12b2b" if is_error else "#0f7b4c"
        self.err.setStyleSheet(f"QLabel {{ color: {color}; font-size: 13px; }}")

    def _set_mode(self, mode):
        self.mode = mode
        self.clear_fields()

        self._set_mode_texts()

    def _set_mode_texts(self):
        is_login = self.mode == "login"
        is_teacher_registration = self.mode == "teacher_register"

        if self.mode == "student_register":
            self.title.setText(tr("login.student_registration"))
        elif self.mode == "teacher_register":
            self.title.setText(tr("login.teacher_registration"))
        else:
            self.title.setText(tr("login.title"))

        self.confirm_pw.setVisible(not is_login)
        self.secret_key.setVisible(is_teacher_registration)
        self.primary_btn.setText(tr("login.title") if is_login else tr("login.create_account"))
        self.register_student_btn.setVisible(is_login)
        self.register_teacher_btn.setVisible(is_login)
        self.back_login_btn.setVisible(not is_login)
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "overlay"):
            # keep overlay covering the full widget when resized (e.g., fullscreen)
            self.overlay.setGeometry(self.rect())

    def _debug_login(self):
        """Emit a debug user to bypass login (development helper)."""
        user = SimpleNamespace(username="debug", role="trainer")
        self.clear_fields()
        self.logged_in.emit(user)

    def clear_fields(self):
        """Clear login inputs so the next user starts from a blank form."""
        self.user.clear()
        self.pw.clear()
        if hasattr(self, "confirm_pw"):
            self.confirm_pw.clear()
        if hasattr(self, "secret_key"):
            self.secret_key.clear()
        self.err.clear()
        self.err.setVisible(False)
        self.user.setFocus()

    # --------------------------------------------------
    # Login logic
    # --------------------------------------------------
    def _submit(self):
        if self.mode == "login":
            self._do_login()
        else:
            self._do_register()

    def _do_login(self):
        u = self.user.text().strip()
        p = self.pw.text()

        user = authenticate(u, p)
        if not user:
            self._set_message(tr("login.invalid_credentials"))
            return

        self.err.setVisible(False)
        self.clear_fields()
        self.logged_in.emit(user)

    def _do_register(self):
        username = self.user.text().strip()
        password = self.pw.text()
        confirm_password = self.confirm_pw.text()
        secret_key = self.secret_key.text() if self.mode == "teacher_register" else ""
        role = "trainer" if self.mode == "teacher_register" else "trainee"

        if password != confirm_password:
            self._set_message(tr("login.password_mismatch"))
            return

        ok, message = register_user(username, password, role, secret_key=secret_key)
        if not ok:
            self._set_message(message)
            return

        self._set_mode("login")
        self._set_message(message, is_error=False)

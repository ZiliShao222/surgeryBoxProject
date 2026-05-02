"""Legacy helper methods for integrating AI Nursing Mentor into MainWindow."""

import os


def _init_ai_mentor(self):
    """Initialize AI Nursing Mentor."""
    try:
        from app.ai_mentor import AIMentor

        try:
            from app.ai_config_local import API_URL, API_KEY, MODEL, BASE_URL
        except ImportError:
            from app.ai_config_example import API_URL, API_KEY, MODEL, BASE_URL
            print("[MainWindow] Warning: Using example AI config. Prefer DASHSCOPE_API_KEY env var for secrets")

        api_key = API_KEY or os.getenv("DASHSCOPE_API_KEY", "")
        if api_key == "your-api-key-here" or not api_key:
            print("[MainWindow] Error: API key not configured. Please set API_KEY in app/ai_config_local.py")
            return None

        self.ai_mentor = AIMentor(API_URL, api_key, model=MODEL, base_url=BASE_URL)
        print("[MainWindow] AI Mentor initialized successfully")
        return self.ai_mentor

    except ImportError as e:
        print(f"[MainWindow] Error importing AI Mentor: {e}")
        return None
    except Exception as e:
        print(f"[MainWindow] Error initializing AI Mentor: {e}")
        return None


def _show_ai_mentor(self):
    """Show AI Nursing Mentor dialog widget."""
    try:
        from app.ui.ai_mentor_widget import AIMentorWidget

        if not hasattr(self, "ai_mentor") or self.ai_mentor is None:
            self._init_ai_mentor()

        if not hasattr(self, "ai_mentor") or self.ai_mentor is None:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "AI Mentor Not Configured",
                "AI Mentor is not configured.\n\nPlease set API_KEY in app/ai_config_local.py.",
            )
            return

        if not hasattr(self, "ai_mentor_widget") or self.ai_mentor_widget is None:
            self.ai_mentor_widget = AIMentorWidget(self.ai_mentor, self.content)
            content_l = self.content.layout()
            content_l.insertWidget(2, self.ai_mentor_widget)

        self._hide_all_content_containers()

        self.ai_mentor_widget.setVisible(True)
        self.content_title.setText("AI Nursing Mentor")
        self.content_title.setVisible(True)

    except Exception as e:
        print(f"Error showing AI Mentor: {e}")
        import traceback

        traceback.print_exc()

        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(
            self,
            "Error",
            "Failed to load AI Mentor.\n\n"
            "Please ensure:\n"
            "1. API_KEY is set in app/ai_config_local.py\n"
            "2. MODEL / BASE_URL are set in app/ai_config_local.py\n"
            "3. Restart the application",
        )

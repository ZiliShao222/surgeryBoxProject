#conda activate epidural310

import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from app.ui.main_window import App

def main():
    # Keep legacy assets/... lookups working no matter where Python is launched from.
    os.chdir(Path(__file__).resolve().parent)

    app = QApplication(sys.argv)
    win = App()
    from PySide6.QtCore import Qt
    win.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
    win.showFullScreen()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

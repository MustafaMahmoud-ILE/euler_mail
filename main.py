"""
Euler Mail — Application Entry Point.
Run with: python main.py
"""
import sys
import os
from pathlib import Path

# Allow running from the euler_mail/ directory or from its parent
_HERE = Path(__file__).parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

# Load .env before any other euler_mail imports
from dotenv import load_dotenv
load_dotenv(dotenv_path=_HERE / ".env", override=False)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt

from euler_mail.utils.logging_config import setup_logging
from euler_mail.ui.main_window import MainWindow
from euler_mail.config.settings import APP_NAME, APP_VERSION, ASSETS_DIR


def main() -> None:
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("EUI")

    # App icon
    icon_path = ASSETS_DIR / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Global stylesheet tweaks (tooltips, scrollbars)
    app.setStyleSheet("""
        QToolTip {
            background:#1B2A4A; color:#FFFFFF; border:1px solid #C9A227;
            border-radius:4px; padding:4px 8px; font-size:12px;
        }
        QScrollBar:vertical {
            background:#F0F2F5; width:8px; margin:0;
        }
        QScrollBar::handle:vertical {
            background:#CBD5E0; border-radius:4px; min-height:20px;
        }
        QScrollBar::handle:vertical:hover { background:#AAB4C0; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        QScrollBar:horizontal {
            background:#F0F2F5; height:8px; margin:0;
        }
        QScrollBar::handle:horizontal {
            background:#CBD5E0; border-radius:4px; min-width:20px;
        }
        QScrollBar::handle:horizontal:hover { background:#AAB4C0; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }
        QMessageBox {
            background:#FFFFFF;
        }
        QMessageBox QLabel { color:#1B2A4A; font-size:13px; }
        QMessageBox QPushButton {
            background:#1B2A4A; color:#FFF; border:none; border-radius:8px;
            padding:6px 20px; font-size:13px; min-width:80px;
        }
        QMessageBox QPushButton:hover { background:#243853; }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

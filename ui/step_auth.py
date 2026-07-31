"""
Step 0 — Google Authentication.
Shows a sign-in card; runs OAuth in a background thread so the UI stays responsive.
"""
import logging
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy,
)
from euler_mail.auth.google_auth import get_credentials, get_user_email, build_gmail_service

logger = logging.getLogger(__name__)


class _AuthWorker(QObject):
    success = Signal(object, str)   # (credentials, user_email)
    failure = Signal(str)           # error message

    def run(self):
        try:
            creds, error = get_credentials()
            if error or creds is None:
                self.failure.emit(error or "Authentication failed.")
                return
            email = get_user_email(creds) or "unknown@email.com"
            self.success.emit(creds, email)
        except Exception as exc:
            logger.exception("Auth worker error")
            self.failure.emit(str(exc))


class StepAuth(QWidget):
    """
    Signals:
        auth_complete(creds, user_email, gmail_service)
    """
    auth_complete = Signal(object, str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(12)

        root.addStretch(1)  # push card to vertical center

        # ── Card ──────────────────────────────────────────────────────────
        card = QFrame()
        card.setFixedWidth(460)
        card.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border-radius: 16px;
                border: 1px solid #E2E5EA;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)
        card_layout.setContentsMargins(40, 36, 40, 36)

        # Lock icon (unicode)
        lock_lbl = QLabel("🔐")
        lock_lbl.setAlignment(Qt.AlignCenter)
        lock_lbl.setStyleSheet("font-size:48px; border:none;")
        card_layout.addWidget(lock_lbl)

        title = QLabel("Sign in to Euler Mail")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:22px; font-weight:700; color:#1B2A4A;
            border:none; margin-top:4px;
        """)
        card_layout.addWidget(title)

        subtitle = QLabel(
            "Use your Google / Gmail account to authenticate.\n"
            "Your sign-in stays on your device — no credentials are shared."
        )
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        subtitle.setStyleSheet("color:#6B6F76; font-size:13px; border:none; margin-bottom:4px;")
        card_layout.addWidget(subtitle)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("border:none; border-top:1px solid #E2E5EA;")
        card_layout.addWidget(div)

        # Sign-in button
        self._btn_signin = QPushButton("  Sign in with Google")
        self._btn_signin.setFixedHeight(48)
        self._btn_signin.setCursor(Qt.PointingHandCursor)
        self._btn_signin.setStyleSheet("""
            QPushButton {
                background: #1B2A4A;
                color: #FFFFFF;
                border: none;
                border-radius: 24px;
                font-size: 15px;
                font-weight: 700;
                padding: 0 24px;
            }
            QPushButton:hover { background: #243853; }
            QPushButton:pressed { background: #0F1A2E; }
            QPushButton:disabled { background: #AAB4C0; }
        """)
        self._btn_signin.clicked.connect(self._start_auth)
        card_layout.addWidget(self._btn_signin)

        # Status label
        self._status_lbl = QLabel("")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        self._status_lbl.setStyleSheet("color:#6B6F76; font-size:12px; border:none;")
        card_layout.addWidget(self._status_lbl)

        root.addWidget(card, alignment=Qt.AlignHCenter)

        # Note below card
        note = QLabel(
            "A browser window will open — sign in and grant permission.\n"
            "This only needs to be done once per machine."
        )
        note.setAlignment(Qt.AlignCenter)
        note.setWordWrap(True)
        note.setStyleSheet("color:#8A9BB0; font-size:12px; margin-top:12px;")
        root.addWidget(note, alignment=Qt.AlignHCenter)

        root.addStretch(1)  # push card to vertical center

    def _start_auth(self):
        self._btn_signin.setEnabled(False)
        self._btn_signin.setText("  Opening browser…")
        self._status_lbl.setText("Please complete sign-in in the browser window that opened.")

        self._worker = _AuthWorker()
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.success.connect(self._on_success)
        self._worker.failure.connect(self._on_failure)
        self._worker.success.connect(self._thread.quit)
        self._worker.failure.connect(self._thread.quit)
        self._thread.start()

    def _on_success(self, creds, email: str):
        service = build_gmail_service(creds)
        self._btn_signin.setText("  Signed in ✓")
        self._status_lbl.setText(f"Authenticated as: {email}")
        self._status_lbl.setStyleSheet("color:#2E7D32; font-size:13px; font-weight:600; border:none;")
        self.auth_complete.emit(creds, email, service)

    def _on_failure(self, error: str):
        self._btn_signin.setEnabled(True)
        self._btn_signin.setText("  Sign in with Google")
        self._status_lbl.setText(f"❌ {error}")
        self._status_lbl.setStyleSheet("color:#B3261E; font-size:12px; border:none;")

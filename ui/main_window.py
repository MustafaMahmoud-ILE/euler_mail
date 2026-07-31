"""
Euler Mail — Main Application Window.
Single QMainWindow with a dark-navy stepper sidebar and a stacked content area.
Orchestrates state flow between all 5 wizard steps.
"""
import os
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap, QPalette, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QLabel, QPushButton, QFrame, QSizePolicy, QScrollArea, QApplication,
)

from euler_mail.config.settings import APP_NAME, APP_VERSION, ASSETS_DIR
from euler_mail.ui.widgets.stepper_sidebar import StepperSidebar
from euler_mail.ui.step_auth import StepAuth
from euler_mail.ui.step_load_excel import StepLoadExcel
from euler_mail.ui.step_compose import StepCompose
from euler_mail.ui.step_ai_enhance import StepAIEnhance
from euler_mail.ui.step_test_preview import StepTestPreview
from euler_mail.ui.step_send_progress import StepSendProgress

logger = logging.getLogger(__name__)

STEP_LABELS = [
    "Sign In",
    "Recipients",
    "Compose",
    "AI Enhance",
    "Test Preview",
    "Send All",
]

# ─── Shared application state ─────────────────────────────────────────────────

@dataclass
class AppState:
    # Auth
    creds: object = None
    user_email: str = ""
    gmail_service: object = None
    # Excel
    headers: List[str] = field(default_factory=list)
    rows: List[dict] = field(default_factory=list)
    mail_column: str = ""
    # Compose
    subject: str = ""
    body_plain: str = ""
    att_folder: Optional[Path] = None
    att_patterns: str = ""
    # AI
    html_body: str = ""
    ai_subject: str = ""
    # Runtime
    current_step: int = 0


# ─── Main Window ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._state = AppState()
        self._setup_window()
        self._build_ui()
        self._connect_signals()
        # Load env key into enhance step
        from euler_mail.config.settings import OPENROUTER_API_URL
        # Done at widget level (reads os.environ directly)

    # ── Window setup ──────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.setMinimumSize(1100, 700)
        self.resize(1260, 780)

        icon_path = ASSETS_DIR / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Global app font
        font = QFont("Segoe UI", 10)
        QApplication.setFont(font)

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── LEFT: Sidebar ─────────────────────────────────────────────────
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(240)
        sidebar_container.setStyleSheet("background:#0D1B2E;")
        sidebar_vbox = QVBoxLayout(sidebar_container)
        sidebar_vbox.setContentsMargins(0, 0, 0, 0)
        sidebar_vbox.setSpacing(0)

        # Logo header
        logo_bar = QWidget()
        logo_bar.setFixedHeight(80)
        logo_bar.setStyleSheet("background:#091525;")
        logo_hbox = QHBoxLayout(logo_bar)
        logo_hbox.setContentsMargins(16, 12, 16, 12)
        logo_hbox.setSpacing(10)

        logo_lbl = QLabel()
        logo_path = ASSETS_DIR / "Logo.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(
                36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("✉")
            logo_lbl.setStyleSheet("color:#C9A227; font-size:24px;")
        logo_hbox.addWidget(logo_lbl)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(0)
        app_title = QLabel(APP_NAME)
        app_title.setStyleSheet(
            "color:#FFFFFF; font-size:15px; font-weight:700; background:transparent;"
        )
        title_vbox.addWidget(app_title)
        app_sub = QLabel("EUI Mail Merge")
        app_sub.setStyleSheet("color:#4A6080; font-size:11px; background:transparent;")
        title_vbox.addWidget(app_sub)
        logo_hbox.addLayout(title_vbox)
        logo_hbox.addStretch()

        sidebar_vbox.addWidget(logo_bar)

        # Thin gold divider
        divider = QFrame()
        divider.setFixedHeight(2)
        divider.setStyleSheet("background:#C9A227; border:none;")
        sidebar_vbox.addWidget(divider)

        # Stepper
        self._stepper = StepperSidebar(STEP_LABELS)
        sidebar_vbox.addWidget(self._stepper, stretch=1)

        # Bottom: signed-in user label
        self._user_bar = QWidget()
        self._user_bar.setFixedHeight(56)
        self._user_bar.setStyleSheet("background:#091525;")
        user_hbox = QHBoxLayout(self._user_bar)
        user_hbox.setContentsMargins(16, 8, 16, 8)
        user_hbox.setSpacing(6)

        self._user_icon = QLabel("👤")
        self._user_icon.setStyleSheet("color:#4A6080; font-size:14px; background:transparent;")
        user_hbox.addWidget(self._user_icon)

        self._user_lbl = QLabel("Not signed in")
        self._user_lbl.setStyleSheet("color:#4A6080; font-size:11px; background:transparent;")
        self._user_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        user_hbox.addWidget(self._user_lbl)

        self._btn_signout = QPushButton("Sign out")
        self._btn_signout.setVisible(False)
        self._btn_signout.setFixedHeight(24)
        self._btn_signout.setCursor(Qt.PointingHandCursor)
        self._btn_signout.setStyleSheet("""
            QPushButton {
                background:transparent; color:#4A6080; border:1px solid #2A3F5C;
                border-radius:12px; font-size:10px; padding:0 8px;
            }
            QPushButton:hover { color:#C9A227; border-color:#C9A227; }
        """)
        self._btn_signout.clicked.connect(self._sign_out)
        user_hbox.addWidget(self._btn_signout)

        sidebar_vbox.addWidget(self._user_bar)

        root.addWidget(sidebar_container)

        # ── RIGHT: Content area ───────────────────────────────────────────
        content_area = QWidget()
        content_area.setStyleSheet("background:#EEF0F4;")
        content_vbox = QVBoxLayout(content_area)
        content_vbox.setContentsMargins(0, 0, 0, 0)
        content_vbox.setSpacing(0)

        # Step header bar
        self._header_bar = QWidget()
        self._header_bar.setFixedHeight(56)
        self._header_bar.setStyleSheet("background:#FFFFFF; border-bottom:1px solid #E2E5EA;")
        header_hbox = QHBoxLayout(self._header_bar)
        header_hbox.setContentsMargins(28, 0, 28, 0)
        header_hbox.setSpacing(12)

        self._step_title_lbl = QLabel("")
        self._step_title_lbl.setStyleSheet(
            "font-size:16px; font-weight:700; color:#1B2A4A; background:transparent;"
        )
        header_hbox.addWidget(self._step_title_lbl)
        header_hbox.addStretch()

        # Nav buttons
        self._btn_prev = QPushButton("← Previous")
        self._btn_prev.setFixedHeight(34)
        self._btn_prev.setCursor(Qt.PointingHandCursor)
        self._btn_prev.setStyleSheet(self._nav_btn_secondary())
        self._btn_prev.setVisible(False)
        self._btn_prev.clicked.connect(self._go_prev)
        header_hbox.addWidget(self._btn_prev)

        self._btn_next = QPushButton("Next →")
        self._btn_next.setFixedHeight(34)
        self._btn_next.setCursor(Qt.PointingHandCursor)
        self._btn_next.setStyleSheet(self._nav_btn_primary())
        self._btn_next.setVisible(False)
        self._btn_next.clicked.connect(self._go_next)
        header_hbox.addWidget(self._btn_next)

        content_vbox.addWidget(self._header_bar)

        # Stacked steps
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background:#EEF0F4;")
        content_vbox.addWidget(self._stack, stretch=1)

        root.addWidget(content_area, stretch=1)

        # ── Create steps ──────────────────────────────────────────────────
        self._step_auth = StepAuth()
        self._step_excel = StepLoadExcel()
        self._step_compose = StepCompose()
        self._step_ai = StepAIEnhance()
        self._step_test = StepTestPreview()
        self._step_send = StepSendProgress()

        for step in [
            self._step_auth, self._step_excel, self._step_compose,
            self._step_ai, self._step_test, self._step_send,
        ]:
            step.setStyleSheet("background:#EEF0F4;")
            # Wrap in a card container
            card = self._wrap_in_card(step)
            self._stack.addWidget(card)

        self._goto_step(0)

    # ── Card wrapper ──────────────────────────────────────────────────────

    def _wrap_in_card(self, widget: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:#EEF0F4;")

        outer = QWidget()
        outer.setStyleSheet("background:#EEF0F4;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(0)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background:#FFFFFF;
                border-radius:12px;
                border:1px solid #E2E5EA;
            }
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addWidget(widget)

        outer_layout.addWidget(card)
        scroll.setWidget(outer)
        return scroll

    # ── Connect signals ───────────────────────────────────────────────────

    def _connect_signals(self):
        self._step_auth.auth_complete.connect(self._on_auth_complete)
        self._step_excel.excel_loaded.connect(self._on_excel_loaded)
        self._step_ai.enhancement_ready.connect(self._on_enhancement_ready)

    # ── Signal handlers ───────────────────────────────────────────────────

    def _on_auth_complete(self, creds, user_email: str, gmail_service):
        self._state.creds = creds
        self._state.user_email = user_email
        self._state.gmail_service = gmail_service
        self._user_lbl.setText(user_email)
        self._user_lbl.setStyleSheet("color:#C9A227; font-size:11px; background:transparent;")
        self._user_icon.setText("✅")
        self._btn_signout.setVisible(True)
        self._stepper.set_state(0, "complete")
        self._goto_step(1)

    def _on_excel_loaded(self, headers: list, rows: list, mail_col: str):
        self._state.headers = headers
        self._state.rows = rows
        self._state.mail_column = mail_col
        self._step_compose.set_headers(headers)
        self._stepper.set_state(1, "complete")

    def _on_enhancement_ready(self, subject: str, html_body: str):
        self._state.ai_subject = subject
        self._state.html_body = html_body
        if subject and not self._state.subject:
            self._state.subject = subject

    # ── Navigation ────────────────────────────────────────────────────────

    def _goto_step(self, idx: int):
        self._state.current_step = idx
        self._stack.setCurrentIndex(idx)

        # Update header
        self._step_title_lbl.setText(
            f"Step {idx + 1} of {len(STEP_LABELS)} — {STEP_LABELS[idx]}"
        )

        # Update stepper sidebar
        for i in range(len(STEP_LABELS)):
            if i < idx:
                self._stepper.set_state(i, "complete")
            elif i == idx:
                self._stepper.set_state(i, "active")
            else:
                self._stepper.set_state(i, "locked")

        # Show/hide nav buttons
        self._btn_prev.setVisible(idx > 0)
        self._btn_next.setVisible(idx < len(STEP_LABELS) - 1)

        # Configure steps that need data when navigated to
        if idx == 3:  # AI Enhance
            plain = self._step_compose.get_body()
            self._step_ai.set_draft(plain, self._step_compose.get_subject())
        elif idx == 4:  # Test Preview
            self._collect_compose()
            self._collect_ai()
            self._step_test.configure(
                self._state.gmail_service,
                self._state.user_email,
                self._state.ai_subject or self._state.subject,
                self._state.html_body,
                self._state.headers,
                self._state.rows,
                self._state.att_folder,
                self._state.att_patterns,
            )
        elif idx == 5:  # Send All
            self._collect_compose()
            self._collect_ai()
            self._step_send.configure(
                self._state.gmail_service,
                self._state.user_email,
                self._state.ai_subject or self._state.subject,
                self._state.html_body,
                self._state.headers,
                self._state.rows,
                self._state.att_folder,
                self._state.att_patterns,
            )

    def _collect_compose(self):
        subject, body, folder, patterns = self._step_compose.collect()
        self._state.subject = subject
        self._state.body_plain = body
        self._state.att_folder = folder
        self._state.att_patterns = patterns

    def _collect_ai(self):
        subj = self._step_ai.get_subject()
        html = self._step_ai.get_html_body()
        if subj:
            self._state.ai_subject = subj
        if html:
            self._state.html_body = html

    def _go_prev(self):
        idx = self._state.current_step
        if idx > 0:
            self._goto_step(idx - 1)

    def _go_next(self):
        idx = self._state.current_step
        # Collect data from current step before moving
        if idx == 2:
            self._collect_compose()
        elif idx == 3:
            self._collect_ai()
        if idx < len(STEP_LABELS) - 1:
            self._goto_step(idx + 1)

    # ── Sign out ──────────────────────────────────────────────────────────

    def _sign_out(self):
        from euler_mail.auth.google_auth import sign_out
        sign_out()
        self._state = AppState()
        self._user_lbl.setText("Not signed in")
        self._user_lbl.setStyleSheet("color:#4A6080; font-size:11px; background:transparent;")
        self._user_icon.setText("👤")
        self._btn_signout.setVisible(False)
        self._goto_step(0)

    # ── Stylesheets ───────────────────────────────────────────────────────

    @staticmethod
    def _nav_btn_primary() -> str:
        return """
            QPushButton {
                background:#1B2A4A; color:#FFF; border:none; border-radius:17px;
                font-size:13px; font-weight:600; padding:0 18px;
            }
            QPushButton:hover { background:#243853; }
        """

    @staticmethod
    def _nav_btn_secondary() -> str:
        return """
            QPushButton {
                background:#EEF2FF; color:#1B2A4A; border:1.5px solid #CBD5E0;
                border-radius:17px; font-size:13px; font-weight:600; padding:0 18px;
            }
            QPushButton:hover { background:#E2E8F0; }
        """

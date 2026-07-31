"""
Step 2 — Compose Draft.
Subject, body editor, placeholder picker, attachments folder/patterns.
"""
import logging
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QFileDialog, QFrame, QSizePolicy, QScrollArea,
)
from euler_mail.ui.widgets.placeholder_picker import PlaceholderPicker

logger = logging.getLogger(__name__)


class StepCompose(QWidget):
    """
    Signals:
        compose_ready(subject: str, body: str, att_folder: Path|None, att_patterns: str)
    """
    compose_ready = Signal(str, str, object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._att_folder: Path | None = None
        self._headers: list = []
        self._build_ui()

    def set_headers(self, headers: list) -> None:
        """Called by MainWindow when Excel is loaded."""
        self._headers = headers
        self._picker.set_placeholders(headers)

    # ── Build UI ───────────────────────────────────────────────────────────

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # Outer layout holds the scroll
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        scroll.setWidget(container)

        # ── Title ──────────────────────────────────────────────────────────
        title = QLabel("Compose Email Draft")
        title.setStyleSheet("font-size:20px; font-weight:700; color:#1B2A4A;")
        layout.addWidget(title)

        desc = QLabel(
            "Write your plain-text draft. Use <b>{ColumnName}</b> placeholders "
            "that match your Excel column headers. The AI enhancement step will "
            "convert this to a styled HTML email."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#4A5568; font-size:13px;")
        layout.addWidget(desc)

        # ── Subject ────────────────────────────────────────────────────────
        layout.addWidget(self._section_label("Subject Line"))
        self._subject = QLineEdit()
        self._subject.setPlaceholderText("e.g.  Your Grade for {Course} — EUI Academic Affairs")
        self._subject.setFixedHeight(40)
        self._subject.setStyleSheet(self._input_style())
        layout.addWidget(self._subject)

        # ── Placeholder picker ────────────────────────────────────────────
        self._picker = PlaceholderPicker()
        self._picker.placeholder_clicked.connect(self._insert_placeholder)
        layout.addWidget(self._picker)

        # ── Body editor ───────────────────────────────────────────────────
        layout.addWidget(self._section_label("Email Body"))

        body_hint = QLabel(
            "Write naturally — the AI will fix spelling/grammar and convert to HTML. "
            "Include a greeting, body paragraphs, and a signature block."
        )
        body_hint.setWordWrap(True)
        body_hint.setStyleSheet("color:#6B6F76; font-size:12px;")
        layout.addWidget(body_hint)

        self._body = QPlainTextEdit()
        self._body.setPlaceholderText(
            "Dear {Name},\n\n"
            "We are pleased to inform you that your result for {Course} has been published.\n\n"
            "Your grade: {Grade}\n\n"
            "Please log in to the student portal to view the full report.\n\n"
            "Best regards,\n"
            "Dr. [Name]\n"
            "Faculty of [Department]\n"
            "Egypt University of Informatics"
        )
        self._body.setMinimumHeight(260)
        self._body.setStyleSheet("""
            QPlainTextEdit {
                background:#FAFBFC; border:1px solid #CBD5E0; border-radius:8px;
                font-family:Arial,Helvetica,sans-serif; font-size:13px;
                color:#2B2B2B; padding:12px;
            }
            QPlainTextEdit:focus { border:1.5px solid #C9A227; }
        """)
        layout.addWidget(self._body, stretch=1)

        # ── Attachments ───────────────────────────────────────────────────
        layout.addWidget(self._section_label("Attachments (Optional)"))

        # Folder picker row
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self._folder_lbl = QLabel("No folder selected")
        self._folder_lbl.setStyleSheet("color:#6B6F76; font-size:13px;")
        self._folder_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        folder_row.addWidget(self._folder_lbl)

        self._btn_folder = QPushButton("Browse…")
        self._btn_folder.setFixedHeight(34)
        self._btn_folder.setCursor(Qt.PointingHandCursor)
        self._btn_folder.setStyleSheet(self._secondary_btn_style())
        self._btn_folder.clicked.connect(self._pick_folder)
        folder_row.addWidget(self._btn_folder)

        layout.addLayout(folder_row)

        # Patterns field
        patterns_lbl = QLabel(
            "Attachment filename patterns (comma-separated, use {placeholder} tokens):"
        )
        patterns_lbl.setWordWrap(True)
        patterns_lbl.setStyleSheet("color:#4A5568; font-size:12px;")
        layout.addWidget(patterns_lbl)

        self._patterns = QLineEdit()
        self._patterns.setPlaceholderText("e.g.  {ID}.pdf, {ID}_certificate.pdf, {ID}_QR.jpg")
        self._patterns.setFixedHeight(38)
        self._patterns.setStyleSheet(self._input_style())
        layout.addWidget(self._patterns)

        inline_note = QLabel(
            "💡 Image files referenced in the HTML body (e.g. QR codes) will be "
            "embedded inline; other files will be sent as downloadable attachments."
        )
        inline_note.setWordWrap(True)
        inline_note.setStyleSheet(
            "color:#6B6F76; font-size:12px; background:#EAF1FB; "
            "border-left:3px solid #2E5EAA; border-radius:4px; padding:8px 12px;"
        )
        layout.addWidget(inline_note)

        layout.addStretch()

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size:14px; font-weight:600; color:#1B2A4A; margin-top:4px;")
        return lbl

    @staticmethod
    def _input_style() -> str:
        return """
            QLineEdit {
                background:#FFFFFF; border:1px solid #CBD5E0; border-radius:8px;
                font-size:13px; color:#2B2B2B; padding:0 12px;
            }
            QLineEdit:focus { border:1.5px solid #C9A227; }
        """

    @staticmethod
    def _secondary_btn_style() -> str:
        return """
            QPushButton {
                background:#EEF2FF; color:#1B2A4A; border:1px solid #CBD5E0;
                border-radius:17px; font-size:12px; font-weight:600; padding:0 16px;
            }
            QPushButton:hover { background:#E2E8F0; }
        """

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Attachments Folder")
        if folder:
            self._att_folder = Path(folder)
            self._folder_lbl.setText(f"📁  {self._att_folder.name}  ({folder})")
            self._folder_lbl.setStyleSheet("color:#1B2A4A; font-size:12px;")

    def _insert_placeholder(self, token: str) -> None:
        """Insert token at the body editor cursor."""
        cursor = self._body.textCursor()
        cursor.insertText(token)
        self._body.setTextCursor(cursor)
        self._body.setFocus()

    # ── Public getters ─────────────────────────────────────────────────────

    def get_subject(self) -> str:
        return self._subject.text().strip()

    def get_body(self) -> str:
        return self._body.toPlainText().strip()

    def get_att_folder(self) -> "Path | None":
        return self._att_folder

    def get_att_patterns(self) -> str:
        return self._patterns.text().strip()

    def collect(self) -> tuple:
        """Return (subject, body, att_folder, att_patterns)."""
        return self.get_subject(), self.get_body(), self._att_folder, self.get_att_patterns()

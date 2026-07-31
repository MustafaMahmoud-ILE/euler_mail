"""
Step 4 — Send Test Preview.
Pick a sample row from the Excel data, resolve placeholders, and send
the resulting email only to the signed-in user's own address.
"""
import logging
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QSizePolicy,
)
from euler_mail.email_engine.template_resolver import (
    resolve, resolve_attachment_specs, substitute_inline_cids,
)
from euler_mail.email_engine.mime_builder import build_message
from euler_mail.email_engine.html_renderer import wrap_html
from euler_mail.email_engine.gmail_sender import send_single
from euler_mail.config.settings import ASSETS_DIR

logger = logging.getLogger(__name__)


class _TestSendWorker(QObject):
    success = Signal(str)   # message_id
    failure = Signal(str)   # error

    def __init__(self, service, to_email, subject, html_body, logo_path,
                 att_folder, att_patterns, sample_row):
        super().__init__()
        self._service = service
        self._to = to_email
        self._subject = subject
        self._html_body = html_body
        self._logo = logo_path
        self._att_folder = att_folder
        self._att_patterns = att_patterns
        self._row = sample_row

    def run(self):
        try:
            # Resolve placeholders
            subject = resolve(self._subject, self._row)
            html = resolve(self._html_body, self._row)

            # Resolve absolute inline images (e.g. from [IMAGE: C:\...])
            from euler_mail.email_engine.template_resolver import resolve_absolute_inline_images
            html, abs_inline_images = resolve_absolute_inline_images(html)

            # Resolve attachments
            specs = resolve_attachment_specs(
                self._att_patterns, self._row, self._att_folder, html
            )
            html = substitute_inline_cids(html, specs)
            html = wrap_html(html)

            inline = [
                (s["path"], s["cid"])
                for s in specs if s["is_inline"] and s["path"] and s["exists"]
            ]
            inline.extend(abs_inline_images)
            
            attachments = [
                s["path"]
                for s in specs if not s["is_inline"] and s["path"] and s["exists"]
            ]

            raw = build_message(
                to=self._to,
                subject=f"[TEST] {subject}",
                html_body=html,
                inline_images=inline,
                attachments=attachments,
                logo_path=self._logo if self._logo and self._logo.exists() else None,
            )
            ok, msg_id, error = send_single(self._service, raw)
            if ok:
                self.success.emit(msg_id or "")
            else:
                self.failure.emit(error or "Unknown error")
        except Exception as exc:
            logger.exception("Test send failed")
            self.failure.emit(str(exc))


class StepTestPreview(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gmail_service = None
        self._user_email = ""
        self._subject = ""
        self._html_body = ""
        self._headers = []
        self._rows = []
        self._att_folder = None
        self._att_patterns = ""
        self._thread = None
        self._worker = None
        self._logo_path = ASSETS_DIR / "email_logo.png"
        self._build_ui()

    def configure(self, gmail_service, user_email, subject, html_body,
                  headers, rows, att_folder, att_patterns):
        self._gmail_service = gmail_service
        self._user_email = user_email
        self._subject = subject
        self._html_body = html_body
        self._headers = headers
        self._rows = rows
        self._att_folder = att_folder
        self._att_patterns = att_patterns
        self._populate_row_combo()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        title = QLabel("Send Test Preview")
        title.setStyleSheet("font-size:20px; font-weight:700; color:#1B2A4A;")
        layout.addWidget(title)

        desc = QLabel(
            "Send a rendered test email to <b>yourself</b> so you can check how it looks "
            "in Gmail, Outlook, or on mobile before the mass send. "
            "Pick any row from your Excel sheet to preview with real data."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#4A5568; font-size:13px;")
        layout.addWidget(desc)

        # ── Test email recipient info ───────────────────────────────────────
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame { background:#EAF1FB; border-left:4px solid #2E5EAA;
                     border-radius:6px; }
        """)
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_lbl = QLabel("Test email will be sent to:")
        info_lbl.setStyleSheet("color:#2E5EAA; font-size:13px; border:none;")
        info_layout.addWidget(info_lbl)
        self._to_lbl = QLabel("(sign in first)")
        self._to_lbl.setStyleSheet("color:#1B2A4A; font-size:13px; font-weight:700; border:none;")
        info_layout.addWidget(self._to_lbl)
        info_layout.addStretch()
        layout.addWidget(info_card)

        # ── Row selector ───────────────────────────────────────────────────
        row_row = QHBoxLayout()
        row_row.setSpacing(10)
        row_lbl = QLabel("Preview with data from row:")
        row_lbl.setStyleSheet("color:#4A5568; font-size:13px; font-weight:600;")
        row_row.addWidget(row_lbl)
        self._row_combo = QComboBox()
        self._row_combo.setFixedHeight(36)
        self._row_combo.setMinimumWidth(260)
        self._row_combo.setStyleSheet("""
            QComboBox { background:#FFF; border:1px solid #CBD5E0; border-radius:6px;
                        font-size:12px; padding:0 10px; }
        """)
        row_row.addWidget(self._row_combo)
        row_row.addStretch()
        layout.addLayout(row_row)

        # ── Send test button ───────────────────────────────────────────────
        self._btn_send = QPushButton("📨  Send Test to Myself")
        self._btn_send.setFixedHeight(48)
        self._btn_send.setCursor(Qt.PointingHandCursor)
        self._btn_send.setStyleSheet("""
            QPushButton {
                background:#1B2A4A; color:#FFF; border:none; border-radius:24px;
                font-size:14px; font-weight:700; padding:0 32px;
            }
            QPushButton:hover { background:#243853; }
            QPushButton:disabled { background:#AAB4C0; }
        """)
        self._btn_send.clicked.connect(self._send_test)
        layout.addWidget(self._btn_send, alignment=Qt.AlignLeft)

        # ── Status ─────────────────────────────────────────────────────────
        self._status_lbl = QLabel("")
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet("color:#6B6F76; font-size:13px;")
        layout.addWidget(self._status_lbl)

        layout.addStretch()

    def _populate_row_combo(self):
        self._to_lbl.setText(self._user_email)
        self._row_combo.clear()
        if not self._rows:
            self._row_combo.addItem("No rows loaded")
            return
        mail_col = next(
            (h for h in self._headers if h.lower() in {"mail", "email"}), None
        )
        for i, row in enumerate(self._rows):
            email = row.get(mail_col, "") if mail_col else ""
            first_vals = ", ".join(str(v) for v in list(row.values())[:3] if v)
            self._row_combo.addItem(f"Row {i + 2}  —  {email}  ({first_vals})")

    def _send_test(self):
        if not self._gmail_service:
            self._set_status("❌  Not signed in. Please complete Step 0 first.", error=True)
            return
        if not self._html_body:
            self._set_status("❌  No HTML body found. Please complete the AI Enhancement step.", error=True)
            return

        idx = self._row_combo.currentIndex()
        sample_row = self._rows[idx] if self._rows and idx < len(self._rows) else {}

        self._btn_send.setEnabled(False)
        self._btn_send.setText("⏳  Sending…")
        self._set_status("Sending test email…")

        self._worker = _TestSendWorker(
            self._gmail_service,
            self._user_email,
            self._subject,
            self._html_body,
            self._logo_path,
            self._att_folder,
            self._att_patterns,
            sample_row,
        )
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.success.connect(self._on_success)
        self._worker.failure.connect(self._on_failure)
        self._worker.success.connect(self._thread.quit)
        self._worker.failure.connect(self._thread.quit)
        self._thread.start()

    def _on_success(self, msg_id: str):
        self._btn_send.setEnabled(True)
        self._btn_send.setText("📨  Send Test to Myself")
        self._set_status(
            f"✅  Test email sent to {self._user_email}. "
            "Check your inbox (may take a few seconds to arrive).",
            success=True,
        )

    def _on_failure(self, error: str):
        self._btn_send.setEnabled(True)
        self._btn_send.setText("📨  Send Test to Myself")
        self._set_status(f"❌  {error}", error=True)

    def _set_status(self, msg: str, error: bool = False, success: bool = False):
        if error:
            style = "color:#B3261E; font-size:13px;"
        elif success:
            style = "color:#2E7D32; font-size:13px; font-weight:600;"
        else:
            style = "color:#6B6F76; font-size:13px;"
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(style)

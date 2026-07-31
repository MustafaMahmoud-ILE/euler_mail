"""
Step 5 — Send to All Recipients.
Confirmation → live progress table → Retry failed button → audit log notice.
"""
import logging
from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QMessageBox, QSizePolicy,
)
from euler_mail.data.models import Recipient, SendStatus
from euler_mail.data.excel_loader import get_mail_column
from euler_mail.email_engine.gmail_sender import SendWorker, RetryWorker
from euler_mail.email_engine.template_resolver import (
    resolve, resolve_attachment_specs, substitute_inline_cids,
)
from euler_mail.email_engine.mime_builder import build_message
from euler_mail.email_engine.html_renderer import wrap_html
from euler_mail.ui.widgets.progress_table import ProgressTable
from euler_mail.config.settings import ASSETS_DIR, SEND_LOG_DIR

logger = logging.getLogger(__name__)


class StepSendProgress(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = None
        self._user_email = ""
        self._subject = ""
        self._html_body = ""
        self._headers: List[str] = []
        self._rows: List[dict] = []
        self._att_folder: Optional[Path] = None
        self._att_patterns: str = ""
        self._recipients: List[Recipient] = []
        self._failed_indices: List[int] = []
        self._thread: Optional[QThread] = None
        self._worker = None
        self._logo_path = ASSETS_DIR / "email_logo.png"
        self._build_ui()

    def configure(self, service, user_email, subject, html_body,
                  headers, rows, att_folder, att_patterns):
        self._service = service
        self._user_email = user_email
        self._subject = subject
        self._html_body = html_body
        self._headers = headers
        self._rows = rows
        self._att_folder = att_folder
        self._att_patterns = att_patterns

        mail_col = get_mail_column(headers)
        self._recipients = [
            Recipient(
                email=row.get(mail_col, "").strip(),
                row_data=row,
                row_index=i,
            )
            for i, row in enumerate(rows)
            if row.get(mail_col, "").strip()
        ]

        # Update UI summary
        self._count_lbl.setText(
            f"Ready to send to <b>{len(self._recipients)}</b> recipient(s)."
        )
        self._btn_send.setEnabled(True)
        self._btn_retry.setVisible(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setMaximum(len(self._recipients))
        self._progress_lbl.setText("")
        self._table.populate(self._recipients)
        self._failed_indices = []

    # ── Build UI ───────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        title = QLabel("Send to All Recipients")
        title.setStyleSheet("font-size:20px; font-weight:700; color:#1B2A4A;")
        layout.addWidget(title)

        self._count_lbl = QLabel("No recipients loaded yet.")
        self._count_lbl.setWordWrap(True)
        self._count_lbl.setStyleSheet("color:#4A5568; font-size:13px;")
        layout.addWidget(self._count_lbl)

        # Warning box
        warn = QLabel(
            "⚠  This will send real emails. Please confirm you have tested the preview "
            "and are happy with the result. This action cannot be undone."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet("""
            background:#FCEEED; border-left:4px solid #B3261E; border-radius:6px;
            color:#B3261E; font-size:12px; padding:10px 14px;
        """)
        layout.addWidget(warn)

        # ── Buttons ────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._btn_send = QPushButton("🚀  Send to All Recipients")
        self._btn_send.setFixedHeight(48)
        self._btn_send.setCursor(Qt.PointingHandCursor)
        self._btn_send.setStyleSheet("""
            QPushButton {
                background:#B3261E; color:#FFF; border:none; border-radius:24px;
                font-size:14px; font-weight:700; padding:0 28px;
            }
            QPushButton:hover { background:#8E1E18; }
            QPushButton:disabled { background:#AAB4C0; }
        """)
        self._btn_send.clicked.connect(self._confirm_and_send)
        btn_row.addWidget(self._btn_send)

        self._btn_cancel = QPushButton("Stop")
        self._btn_cancel.setFixedHeight(48)
        self._btn_cancel.setVisible(False)
        self._btn_cancel.setCursor(Qt.PointingHandCursor)
        self._btn_cancel.setStyleSheet("""
            QPushButton {
                background:#EEF2FF; color:#1B2A4A; border:1.5px solid #CBD5E0;
                border-radius:24px; font-size:13px; font-weight:600; padding:0 20px;
            }
            QPushButton:hover { background:#E2E8F0; }
        """)
        self._btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self._btn_cancel)

        self._btn_retry = QPushButton("🔄  Retry Failed (0)")
        self._btn_retry.setFixedHeight(44)
        self._btn_retry.setVisible(False)
        self._btn_retry.setCursor(Qt.PointingHandCursor)
        self._btn_retry.setStyleSheet("""
            QPushButton {
                background:#E0A11C; color:#FFF; border:none; border-radius:22px;
                font-size:13px; font-weight:700; padding:0 20px;
            }
            QPushButton:hover { background:#B88015; }
        """)
        self._btn_retry.clicked.connect(self._retry_failed)
        btn_row.addWidget(self._btn_retry)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Progress bar ───────────────────────────────────────────────────
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(10)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet("""
            QProgressBar { background:#E2E5EA; border-radius:5px; border:none; }
            QProgressBar::chunk { background:#2E7D32; border-radius:5px; }
        """)
        layout.addWidget(self._progress_bar)

        self._progress_lbl = QLabel("")
        self._progress_lbl.setStyleSheet("color:#4A5568; font-size:12px;")
        layout.addWidget(self._progress_lbl)

        # ── Progress table ────────────────────────────────────────────────
        self._table = ProgressTable()
        layout.addWidget(self._table, stretch=1)

        # ── Log notice ────────────────────────────────────────────────────
        log_note = QLabel(f"📋  A send log (CSV) is saved automatically to: {SEND_LOG_DIR}")
        log_note.setStyleSheet("color:#8A9BB0; font-size:11px;")
        layout.addWidget(log_note)

    # ── Send logic ─────────────────────────────────────────────────────────

    def _confirm_and_send(self):
        n = len(self._recipients)
        reply = QMessageBox.question(
            self,
            "Confirm Send",
            f"You are about to send <b>{n}</b> email(s).<br><br>"
            "This cannot be undone. Proceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._start_send()

    def _start_send(self):
        self._btn_send.setEnabled(False)
        self._btn_send.setText("Sending…")
        self._btn_cancel.setVisible(True)
        self._btn_retry.setVisible(False)
        self._failed_indices = []
        self._progress_bar.setValue(0)
        self._progress_bar.setMaximum(max(1, len(self._recipients)))

        logo = self._logo_path if self._logo_path.exists() else None

        def build_fn(recipient: Recipient) -> Optional[str]:
            try:
                subject = resolve(self._subject, recipient.row_data)
                html = resolve(self._html_body, recipient.row_data)
                
                # Resolve absolute inline images (e.g. from [IMAGE: C:\...])
                from euler_mail.email_engine.template_resolver import resolve_absolute_inline_images
                html, abs_inline_images = resolve_absolute_inline_images(html)
                
                specs = resolve_attachment_specs(
                    self._att_patterns, recipient.row_data, self._att_folder, html
                )
                html = substitute_inline_cids(html, specs)
                html = wrap_html(html)
                inline = [
                    (s["path"], s["cid"])
                    for s in specs if s["is_inline"] and s["path"] and s["exists"]
                ]
                # Combine standard inline images with absolute path images
                inline.extend(abs_inline_images)
                attachments = [
                    s["path"]
                    for s in specs if not s["is_inline"] and s["path"] and s["exists"]
                ]
                return build_message(
                    to=recipient.email,
                    subject=subject,
                    html_body=html,
                    inline_images=inline,
                    attachments=attachments,
                    logo_path=logo,
                )
            except Exception as exc:
                logger.error(f"Build error for {recipient.email}: {exc}")
                return None

        self._worker = SendWorker(self._service, self._recipients, build_fn)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.recipient_updated.connect(self._on_recipient_update)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_recipient_update(self, index: int, email: str, status: str, error: str):
        self._table.update_row(index, email, status, error)
        if "✅" in status or "❌" in status or "Skipped" in status:
            sent = sum(
                1 for i in range(self._table.rowCount())
                if self._table.item(i, 2) and "✅" in (self._table.item(i, 2).text() or "")
            )
            done = sum(
                1 for i in range(self._table.rowCount())
                if self._table.item(i, 2) and self._table.item(i, 2).text() not in ("Pending", "Sending…", "")
            )
            self._progress_bar.setValue(done)
            self._progress_lbl.setText(
                f"{done} of {len(self._recipients)} processed  |  {sent} sent successfully"
            )
            if "❌" in status:
                self._failed_indices.append(index)

    def _on_finished(self, log_entries: list):
        self._btn_send.setEnabled(True)
        self._btn_send.setText("🚀  Send to All Recipients")
        self._btn_cancel.setVisible(False)

        n_failed = len(self._failed_indices)
        n_sent = len(self._recipients) - n_failed
        self._progress_lbl.setText(
            f"✅ Done — {n_sent} sent, {n_failed} failed."
        )

        if n_failed > 0:
            self._btn_retry.setText(f"🔄  Retry Failed ({n_failed})")
            self._btn_retry.setVisible(True)

    def _cancel(self):
        if self._worker:
            self._worker.stop()
        self._btn_cancel.setVisible(False)

    def _retry_failed(self):
        if not self._failed_indices:
            return
        logo = self._logo_path if self._logo_path.exists() else None

        def build_fn(recipient: Recipient):
            try:
                subject = resolve(self._subject, recipient.row_data)
                html = resolve(self._html_body, recipient.row_data)
                
                # Resolve absolute inline images (e.g. from [IMAGE: C:\...])
                from euler_mail.email_engine.template_resolver import resolve_absolute_inline_images
                html, abs_inline_images = resolve_absolute_inline_images(html)
                
                specs = resolve_attachment_specs(
                    self._att_patterns, recipient.row_data, self._att_folder, html
                )
                html = substitute_inline_cids(html, specs)
                html = wrap_html(html)
                inline = [(s["path"], s["cid"]) for s in specs if s["is_inline"] and s["path"] and s["exists"]]
                inline.extend(abs_inline_images)
                
                attachments = [s["path"] for s in specs if not s["is_inline"] and s["path"] and s["exists"]]
                return build_message(
                    to=recipient.email, subject=subject, html_body=html,
                    inline_images=inline, attachments=attachments, logo_path=logo,
                )
            except Exception as exc:
                logger.error(f"Build error: {exc}")
                return None

        self._btn_retry.setEnabled(False)
        self._worker = RetryWorker(
            self._service, self._recipients, build_fn, list(self._failed_indices)
        )
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.recipient_updated.connect(self._on_recipient_update)
        self._worker.finished.connect(self._on_retry_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_retry_finished(self, log_entries: list):
        self._btn_retry.setEnabled(True)
        remaining_failed = [
            i for i in self._failed_indices
            if self._table.item(i, 2) and "✅" not in (self._table.item(i, 2).text() or "")
        ]
        self._failed_indices = remaining_failed
        if remaining_failed:
            self._btn_retry.setText(f"🔄  Retry Failed ({len(remaining_failed)})")
        else:
            self._btn_retry.setVisible(False)
            self._progress_lbl.setText("✅  All retries succeeded!")

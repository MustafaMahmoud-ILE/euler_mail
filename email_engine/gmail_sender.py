"""
Gmail API sender with exponential backoff, deferred retries, and Qt-signal
progress reporting for Euler Mail.
"""
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from googleapiclient.errors import HttpError
from PySide6.QtCore import QObject, Signal, QThread

from euler_mail.config.settings import (
    SEND_DELAY_SECONDS,
    MAX_SEND_RETRIES,
    RETRY_STATUS_CODES,
    SEND_LOG_DIR,
)
from euler_mail.data.models import Recipient, SendResult, SendStatus

logger = logging.getLogger(__name__)


# ── Low-level single-send with retry ─────────────────────────────────────────

def send_single(
    service,
    raw_message: str,
) -> tuple:
    """
    Send one raw message via Gmail API.
    Returns (success: bool, message_id: str|None, error: str|None).
    """
    for attempt in range(MAX_SEND_RETRIES):
        try:
            result = service.users().messages().send(
                userId="me",
                body={"raw": raw_message},
            ).execute()
            return True, result.get("id"), None

        except HttpError as exc:
            code = exc.resp.status
            if code in RETRY_STATUS_CODES and attempt < MAX_SEND_RETRIES - 1:
                wait = 2 ** attempt
                logger.warning(
                    f"HTTP {code} on attempt {attempt + 1}; retrying in {wait}s…"
                )
                time.sleep(wait)
            else:
                msg = f"Gmail API error (HTTP {code})"
                try:
                    detail = json.loads(exc.content).get("error", {}).get("message", "")
                    if detail:
                        msg += f": {detail}"
                except Exception:
                    pass
                return False, None, msg

        except Exception as exc:
            return False, None, f"Unexpected error: {exc}"

    return False, None, "Max retries exceeded."


# ── Qt worker (runs in a QThread) ─────────────────────────────────────────────

class SendWorker(QObject):
    """
    Sends all recipients in a background thread.
    Emits per-recipient signals so the UI can update the progress table live.
    Failed sends are automatically deferred to the end of the queue.
    """

    # (row_index, email, status_label, error_message)
    recipient_updated: Signal = Signal(int, str, str, str)
    # Overall completion
    finished: Signal = Signal(list)   # list[dict] send log entries

    def __init__(
        self,
        service,
        recipients: List[Recipient],
        build_fn: Callable[[Recipient], Optional[str]],
        delay: float = SEND_DELAY_SECONDS,
    ):
        super().__init__()
        self._service = service
        self._recipients = recipients
        self._build_fn = build_fn
        self._delay = delay
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    # Called by QThread.started signal
    def run(self) -> None:
        log_entries: List[dict] = []
        failed_indices: List[int] = []

        def _process(i: int, recipient: Recipient) -> Optional[SendResult]:
            if self._stop:
                self.recipient_updated.emit(i, recipient.email, "Skipped", "Cancelled")
                return SendResult(
                    datetime.now(), recipient.email, SendStatus.SKIPPED, error="Cancelled"
                )

            self.recipient_updated.emit(i, recipient.email, "Sending…", "")

            try:
                raw = self._build_fn(recipient)
            except Exception as exc:
                err = f"Message build error: {exc}"
                self.recipient_updated.emit(i, recipient.email, "Failed ❌", err)
                return SendResult(datetime.now(), recipient.email, SendStatus.FAILED, error=err)

            if raw is None:
                err = "Failed to build email message (missing attachment?)."
                self.recipient_updated.emit(i, recipient.email, "Failed ❌", err)
                return SendResult(datetime.now(), recipient.email, SendStatus.FAILED, error=err)

            ok, msg_id, error = send_single(self._service, raw)
            if ok:
                self.recipient_updated.emit(i, recipient.email, "Sent ✅", "")
                return SendResult(
                    datetime.now(), recipient.email, SendStatus.SENT, message_id=msg_id
                )
            else:
                self.recipient_updated.emit(i, recipient.email, "Failed ❌", error or "")
                return SendResult(
                    datetime.now(), recipient.email, SendStatus.FAILED, error=error
                )

        # ── First pass (all recipients) ────────────────────────────────────
        for i, recipient in enumerate(self._recipients):
            result = _process(i, recipient)
            if result:
                log_entries.append(result.to_dict())
                if result.status == SendStatus.FAILED:
                    failed_indices.append(i)

            if i < len(self._recipients) - 1 and not self._stop:
                time.sleep(self._delay)

        # ── Retry deferred failures ────────────────────────────────────────
        if failed_indices and not self._stop:
            time.sleep(1.0)
            for i in failed_indices:
                if self._stop:
                    break
                result = _process(i, self._recipients[i])
                if result:
                    log_entries.append(result.to_dict())
                time.sleep(self._delay)

        _save_send_log(log_entries)
        self.finished.emit(log_entries)


# ── Retry-only worker ─────────────────────────────────────────────────────────

class RetryWorker(SendWorker):
    """Like SendWorker but only processes a specific subset of recipients."""

    def __init__(self, service, recipients, build_fn, indices, delay=SEND_DELAY_SECONDS):
        super().__init__(service, recipients, build_fn, delay)
        self._indices = indices

    def run(self) -> None:
        log_entries: List[dict] = []
        for i in self._indices:
            if self._stop or i >= len(self._recipients):
                break
            recipient = self._recipients[i]
            self.recipient_updated.emit(i, recipient.email, "Sending…", "")

            try:
                raw = self._build_fn(recipient)
            except Exception as exc:
                err = f"Build error: {exc}"
                self.recipient_updated.emit(i, recipient.email, "Failed ❌", err)
                log_entries.append(
                    SendResult(datetime.now(), recipient.email, SendStatus.FAILED, error=err).to_dict()
                )
                continue

            if raw is None:
                err = "Failed to build message."
                self.recipient_updated.emit(i, recipient.email, "Failed ❌", err)
                log_entries.append(
                    SendResult(datetime.now(), recipient.email, SendStatus.FAILED, error=err).to_dict()
                )
                continue

            ok, msg_id, error = send_single(self._service, raw)
            if ok:
                self.recipient_updated.emit(i, recipient.email, "Sent ✅", "")
                log_entries.append(
                    SendResult(datetime.now(), recipient.email, SendStatus.SENT, message_id=msg_id).to_dict()
                )
            else:
                self.recipient_updated.emit(i, recipient.email, "Failed ❌", error or "")
                log_entries.append(
                    SendResult(datetime.now(), recipient.email, SendStatus.FAILED, error=error).to_dict()
                )

            time.sleep(self._delay)

        _save_send_log(log_entries)
        self.finished.emit(log_entries)


# ── Send log persistence ──────────────────────────────────────────────────────

def _save_send_log(entries: List[dict]) -> None:
    if not entries:
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = SEND_LOG_DIR / f"send_{ts}.csv"
    try:
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "recipient", "status", "message_id", "error"])
            writer.writeheader()
            writer.writerows(entries)
        logger.info(f"Send log saved: {log_path}")
    except Exception as exc:
        logger.error(f"Could not save send log: {exc}")

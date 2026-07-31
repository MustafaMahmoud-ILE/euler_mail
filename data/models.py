"""
Data models for Euler Mail.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class SendStatus(Enum):
    PENDING = "Pending"
    SENDING = "Sending..."
    SENT = "Sent ✅"
    FAILED = "Failed ❌"
    SKIPPED = "Skipped"


@dataclass
class Recipient:
    email: str
    row_data: dict
    row_index: int = 0
    status: SendStatus = SendStatus.PENDING
    error_message: Optional[str] = None
    message_id: Optional[str] = None


@dataclass
class AttachmentSpec:
    pattern: str
    resolved_name: str = ""
    resolved_path: Optional[Path] = None
    exists: bool = False
    is_image: bool = False
    is_inline: bool = False
    cid: Optional[str] = None


@dataclass
class ValidationError:
    row_index: int
    email: str
    message: str


@dataclass
class SendResult:
    timestamp: datetime
    recipient_email: str
    status: SendStatus
    message_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "recipient": self.recipient_email,
            "status": self.status.value,
            "message_id": self.message_id or "",
            "error": self.error or "",
        }

"""
MIME message builder for Euler Mail.
Produces a base64url-encoded raw message string for the Gmail API.

MIME structure:
  HTML only             → multipart/alternative → text/html
  Inline images only    → multipart/related     → text/html + image/*…
  Attachments only      → multipart/mixed       → text/html + application/*…
  Both                  → multipart/mixed       → multipart/related + application/*…
"""
import base64
import logging
import mimetypes
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def build_message(
    to: str,
    subject: str,
    html_body: str,
    from_email: Optional[str] = None,
    attachments: Optional[List[Path]] = None,
    inline_images: Optional[List[Tuple[Path, str]]] = None,   # (path, cid)
    logo_path: Optional[Path] = None,
) -> str:
    """
    Build a MIME email and return the base64url-encoded raw string
    ready for Gmail API ``users.messages.send``.

    Parameters
    ----------
    to             Recipient email address.
    subject        Email subject line.
    html_body      Full HTML body (must already have cid: references resolved).
    from_email     Sender address (optional; Gmail API uses the authenticated user).
    attachments    Paths to regular file attachments.
    inline_images  [(path, cid), …] for CID-embedded images referenced in HTML.
    logo_path      Path to the EUI Logo.png — always embedded as cid:euler_logo.
    """
    attachments = attachments or []
    inline_images = inline_images or []

    logo_exists = logo_path is not None and logo_path.exists()
    has_inline = bool(inline_images) or logo_exists
    has_attach = bool(attachments)

    html_part = MIMEText(html_body, "html", "utf-8")

    # ── Build structure ────────────────────────────────────────────────────
    if has_inline and has_attach:
        root = MIMEMultipart("mixed")
        related = MIMEMultipart("related")
        related.attach(html_part)
        _attach_inline(related, inline_images, logo_path if logo_exists else None)
        root.attach(related)
        _attach_files(root, attachments)

    elif has_inline:
        root = MIMEMultipart("related")
        root.attach(html_part)
        _attach_inline(root, inline_images, logo_path if logo_exists else None)

    elif has_attach:
        root = MIMEMultipart("mixed")
        root.attach(html_part)
        _attach_files(root, attachments)

    else:
        root = MIMEMultipart("alternative")
        root.attach(html_part)

    # ── Headers ────────────────────────────────────────────────────────────
    if from_email:
        root["From"] = from_email
    root["To"] = to
    root["Subject"] = subject

    raw = base64.urlsafe_b64encode(root.as_bytes()).decode("utf-8")
    return raw


# ── Private helpers ────────────────────────────────────────────────────────────

def _attach_inline(
    msg: MIMEMultipart,
    inline_images: List[Tuple[Path, str]],
    logo_path: Optional[Path],
) -> None:
    if logo_path:
        _embed_image(msg, logo_path, "euler_logo")
    for img_path, cid in inline_images:
        if img_path.exists():
            _embed_image(msg, img_path, cid)
        else:
            logger.warning(f"Inline image not found, skipping: {img_path}")


def _embed_image(msg: MIMEMultipart, path: Path, cid: str) -> None:
    mime_type, _ = mimetypes.guess_type(str(path))
    _, subtype = (mime_type or "image/png").split("/", 1)
    with open(path, "rb") as fh:
        data = fh.read()
    img = MIMEImage(data, _subtype=subtype)
    img.add_header("Content-ID", f"<{cid}>")
    img.add_header("Content-Disposition", "inline", filename=path.name)
    msg.attach(img)


def _attach_files(msg: MIMEMultipart, attachments: List[Path]) -> None:
    for path in attachments:
        if not path.exists():
            logger.warning(f"Attachment not found, skipping: {path}")
            continue
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        with open(path, "rb") as fh:
            data = fh.read()
        part = MIMEBase(maintype, subtype)
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=path.name)
        msg.attach(part)

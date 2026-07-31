"""
Secure token storage for Euler Mail OAuth credentials.
Prefers OS keyring; falls back to a plain JSON file in the user data dir.
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SERVICE_NAME = "EulerMail"
ACCOUNT_NAME = "google_oauth_token"

try:
    import keyring as _keyring
    _KEYRING_OK = True
except Exception:
    _KEYRING_OK = False


def _token_file() -> Path:
    from euler_mail.config.settings import TOKEN_PATH
    return TOKEN_PATH


# ── Public API ────────────────────────────────────────────────────────────────

def save_token(token_data: dict) -> None:
    """Persist OAuth token dict to keyring or file."""
    payload = json.dumps(token_data)
    if _KEYRING_OK:
        try:
            _keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, payload)
            logger.debug("Token saved to OS keyring.")
            return
        except Exception as exc:
            logger.warning(f"Keyring write failed ({exc}); falling back to file.")

    path = _token_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    logger.debug(f"Token saved to file: {path}")


def load_token() -> Optional[dict]:
    """Load OAuth token dict from keyring or file. Returns None if absent."""
    if _KEYRING_OK:
        try:
            raw = _keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
            if raw:
                logger.debug("Token loaded from OS keyring.")
                return json.loads(raw)
        except Exception as exc:
            logger.warning(f"Keyring read failed ({exc}); trying file.")

    path = _token_file()
    if path.exists():
        try:
            raw = path.read_text(encoding="utf-8")
            logger.debug(f"Token loaded from file: {path}")
            return json.loads(raw)
        except Exception as exc:
            logger.warning(f"Failed to read token file: {exc}")

    return None


def clear_token() -> None:
    """Delete all stored credentials."""
    if _KEYRING_OK:
        try:
            _keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
            logger.debug("Token removed from OS keyring.")
        except Exception:
            pass

    path = _token_file()
    if path.exists():
        path.unlink()
        logger.debug(f"Token file deleted: {path}")

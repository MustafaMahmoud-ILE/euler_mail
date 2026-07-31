"""
Google OAuth 2.0 flow for Euler Mail.
Each user authenticates with their own Google account;
credentials are stored locally in the OS user-data directory.
"""
import json
import logging
from typing import Optional, Tuple

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from euler_mail.config.settings import OAUTH_SCOPES, OAUTH_CLIENT_SECRET_PATH
from euler_mail.auth.credential_store import save_token, load_token, clear_token

logger = logging.getLogger(__name__)


# ── Public helpers ─────────────────────────────────────────────────────────────

def client_secret_exists() -> bool:
    return OAUTH_CLIENT_SECRET_PATH.exists()


def get_credentials() -> Tuple[Optional[Credentials], Optional[str]]:
    """
    Return (credentials, error_message).
    Loads from storage, refreshes if expired, or runs the browser OAuth flow.
    Returns (None, error_msg) on any failure.
    """
    if not client_secret_exists():
        return None, (
            f"OAuth client secret not found at:\n{OAUTH_CLIENT_SECRET_PATH}\n\n"
            "Please copy your client_secret.json into the config/ folder."
        )

    creds: Optional[Credentials] = None
    token_data = load_token()

    if token_data:
        try:
            creds = Credentials.from_authorized_user_info(token_data, OAUTH_SCOPES)
        except Exception as exc:
            logger.warning(f"Could not restore credentials from stored token: {exc}")
            creds = None

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_token(json.loads(creds.to_json()))
            logger.info("Access token refreshed successfully.")
        except Exception as exc:
            logger.warning(f"Token refresh failed: {exc}. Re-running OAuth flow.")
            creds = None

    # Run full OAuth flow if needed
    if not creds or not creds.valid:
        try:
            from euler_mail.auth.oauth_success_page import patch_oauth_success_page
            patch_oauth_success_page()
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(OAUTH_CLIENT_SECRET_PATH),
                scopes=OAUTH_SCOPES,
            )
            creds = flow.run_local_server(
                port=0,
                prompt="consent",
                access_type="offline",
            )
            save_token(json.loads(creds.to_json()))
            logger.info("OAuth flow completed; credentials stored.")
        except Exception as exc:
            logger.error(f"OAuth flow failed: {exc}")
            return None, f"Sign-in failed:\n{exc}"

    return creds, None


def build_gmail_service(creds: Credentials):
    """Build an authenticated Gmail API service object."""
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_user_email(creds: Credentials) -> Optional[str]:
    """Fetch the authenticated user's email via the userinfo API."""
    try:
        svc = build("oauth2", "v2", credentials=creds, cache_discovery=False)
        info = svc.userinfo().get().execute()
        return info.get("email")
    except Exception as exc:
        logger.warning(f"Could not retrieve user email: {exc}")
        return None


def sign_out() -> None:
    """Delete stored credentials so the next launch triggers a fresh login."""
    clear_token()
    logger.info("User signed out — credentials cleared.")

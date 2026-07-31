"""
Euler Mail — Application-wide constants, paths, and style definitions.
"""
import os
from pathlib import Path

# ── App identity ──────────────────────────────────────────────────────────────
APP_NAME = "Euler Mail"
APP_VERSION = "1.0.0"
ORG_NAME = "EUI"

# ── Directory layout ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent          # euler_mail/
ASSETS_DIR = BASE_DIR / "assets"
CONFIG_DIR = BASE_DIR / "config"
OAUTH_CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"


def get_user_data_dir() -> Path:
    """Return the OS-appropriate per-user data directory."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home()
    data_dir = base / "EulerMail"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


USER_DATA_DIR = get_user_data_dir()
TOKEN_PATH = USER_DATA_DIR / "token.json"
LOG_DIR = USER_DATA_DIR / "logs"
SEND_LOG_DIR = USER_DATA_DIR / "send_logs"

# Ensure dirs exist at import time
LOG_DIR.mkdir(parents=True, exist_ok=True)
SEND_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Google OAuth ──────────────────────────────────────────────────────────────
OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",   # Google always adds this when userinfo.email is requested — include it to prevent scope-mismatch errors
]

# ── Gmail send rate limiting ──────────────────────────────────────────────────
SEND_DELAY_SECONDS = 0.4
MAX_SEND_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

# ── OpenRouter ────────────────────────────────────────────────────────────────
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

OPENROUTER_MODELS = [
    ("openai/gpt-4o-mini (Fast — default)", "openai/gpt-4o-mini"),
    ("google/gemini-2.5-flash (Google Fast)", "google/gemini-2.5-flash"),
    ("google/gemini-2.5-flash-lite (Google Lite)", "google/gemini-2.5-flash-lite"),
]
DEFAULT_MODEL = "openai/gpt-4o-mini"

# ── Style Palettes ────────────────────────────────────────────────────────────
# Full color token sets from Euler_Mail_Styles_and_Formatting.md
STYLE_PALETTES = {
    "Academic": {
        "label": "🎓 Academic",
        "description": "Formal university correspondence\n(grades, research, faculty notices)",
        "primary": "#1B2A4A",
        "accent": "#C9A227",
        "body_text": "#2B2B2B",
        "muted_text": "#6B6F76",
        "background": "#FFFFFF",
        "section_bg": "#F7F8FA",
        "border": "#E2E5EA",
        "link": "#1B2A4A",
        "button_bg": "#1B2A4A",
        "button_text": "#FFFFFF",
        "alert_bg": None,
        "alert_border": None,
        "tone_keyword": "Formal, restrained",
    },
    "Announcement": {
        "label": "📢 Announcement",
        "description": "General news, events, updates\nand invitations",
        "primary": "#2E5EAA",
        "accent": "#5B9BF2",
        "body_text": "#26313F",
        "muted_text": "#5F6B7A",
        "background": "#FFFFFF",
        "section_bg": "#EAF1FB",
        "border": "#CFE0F5",
        "link": "#2E5EAA",
        "button_bg": "#2E5EAA",
        "button_text": "#FFFFFF",
        "alert_bg": "#EAF1FB",
        "alert_border": "#CFE0F5",
        "tone_keyword": "Friendly, clear",
    },
    "Warning": {
        "label": "⚠️ Warning",
        "description": "Deadlines, non-compliance\nand urgent notices",
        "primary": "#B3261E",
        "accent": "#E0A11C",
        "body_text": "#2B2B2B",
        "muted_text": "#7A7A7A",
        "background": "#FFFFFF",
        "section_bg": "#FFFFFF",
        "border": "#EFC9C6",
        "link": "#B3261E",
        "button_bg": "#B3261E",
        "button_text": "#FFFFFF",
        "alert_bg": "#FCEEED",
        "alert_border": "#EFC9C6",
        "tone_keyword": "Firm, urgent",
    },
    "Informative": {
        "label": "ℹ️ Informative",
        "description": "Reports, instructions, FAQs\nand how-to notices",
        "primary": "#2F6F6B",
        "accent": "#6FBFB5",
        "body_text": "#2A2E2E",
        "muted_text": "#657372",
        "background": "#FFFFFF",
        "section_bg": "#EAF5F4",
        "border": "#CFE7E4",
        "link": "#2F6F6B",
        "button_bg": "#2F6F6B",
        "button_text": "#FFFFFF",
        "alert_bg": "#EAF5F4",
        "alert_border": "#CFE7E4",
        "tone_keyword": "Neutral, structured",
    },
}

STYLE_NAMES = list(STYLE_PALETTES.keys())

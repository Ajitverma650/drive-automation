"""Centralized configuration for GoKwik Rate Capture Automation.

Loads .env variables and exposes all settings used across the app.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(override=True)

# ── Project root ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent

# ── PDF Page Targets (1-based) ────────────────────────────────
RATE_PAGE = 2
AGREEMENT_PAGE = 2

# ── OpenAI ────────────────────────────────────────────────────

def get_openai_api_key() -> Optional[str]:
    """Return the OpenAI API key from environment variables."""
    return os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY")

# ── SMTP / Email ──────────────────────────────────────────────

def get_smtp_config() -> Optional[dict]:
    """Get SMTP configuration from environment variables."""
    host = os.getenv("SMTP_HOST")
    port = os.getenv("SMTP_PORT", "587")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("EMAIL_FROM", user)
    email_to = os.getenv("EMAIL_TO")

    if not all([host, user, password, email_to]):
        return None

    return {
        "host": host,
        "port": int(port),
        "user": user,
        "password": password,
        "from": email_from,
        "to": [e.strip() for e in email_to.split(",") if e.strip()],
        "cc": [e.strip() for e in (os.getenv("EMAIL_CC") or "").split(",") if e.strip()],
    }

# ── Google Drive ─────────────────────────────────────────────

def get_google_drive_credentials_path() -> Optional[str]:
    """Return path to Google Drive credentials JSON file."""
    env_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS")
    if env_path:
        full_path = PROJECT_ROOT / env_path if not os.path.isabs(env_path) else Path(env_path)
        if full_path.exists():
            return str(full_path)

    default_path = PROJECT_ROOT / "credentials.json"
    if default_path.exists():
        return str(default_path)

    return None

def get_google_drive_folder_id() -> Optional[str]:
    """Return the Google Drive folder ID to search in (optional)."""
    return os.getenv("GOOGLE_DRIVE_FOLDER_ID")

def get_google_drive_token_path() -> str:
    """Return path where Drive OAuth token is saved."""
    return str(PROJECT_ROOT / "token.json")

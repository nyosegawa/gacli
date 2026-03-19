from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

CONFIG_DIR = Path.home() / ".config" / "gacli"
CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"


def credentials_path(profile: str) -> Path:
    return CONFIG_DIR / "profiles" / profile / "credentials.json"


def authenticate(profile: str) -> Credentials:
    """Run OAuth flow and save credentials for a profile."""
    if not CLIENT_SECRET_PATH.exists():
        raise FileNotFoundError(
            f"Client secret not found at {CLIENT_SECRET_PATH}\n"
            "Download it from GCP Console > APIs & Services > Credentials\n"
            "and save it as: ~/.config/gacli/client_secret.json"
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET_PATH), SCOPES
    )
    creds = flow.run_local_server(port=0)

    dest = credentials_path(profile)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(creds.to_json())

    return creds


def load_credentials(profile: str) -> Credentials:
    """Load saved credentials, refreshing if expired."""
    path = credentials_path(profile)
    if not path.exists():
        raise FileNotFoundError(
            f"No credentials for profile '{profile}'. Run: gacli auth --profile {profile}"
        )

    creds = Credentials.from_authorized_user_info(
        json.loads(path.read_text()), SCOPES
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json())

    return creds

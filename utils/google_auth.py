"""
Google OAuth authentication for NeGD Dashboard.
Uses OAuth 2.0 Desktop flow (no service account key needed).
"""

import os
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]

CONFIG_DIR = Path(__file__).parent.parent / "config"
TOKEN_PATH = CONFIG_DIR / "token.pickle"
CLIENT_SECRET_PATH = CONFIG_DIR / "oauth_client_secret.json"


def get_credentials():
    """Authenticate via OAuth and return credentials.
    First run opens a browser for login. Subsequent runs use saved token.
    """
    creds = None

    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_PATH.exists():
                raise FileNotFoundError(
                    f"OAuth client secret not found at {CLIENT_SECRET_PATH}.\n"
                    "Download it from Google Cloud Console:\n"
                    "  APIs & Services > Credentials > OAuth 2.0 Client ID > Download JSON\n"
                    "Save as: config/oauth_client_secret.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        CONFIG_DIR.mkdir(exist_ok=True)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return creds

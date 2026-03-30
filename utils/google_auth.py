"""
Google OAuth authentication for NeGD Dashboard.
- Local: Uses OAuth 2.0 Desktop flow (opens browser on first run).
- Deployed (Streamlit Cloud): Reads token from st.secrets.
"""

import base64
import io
import os
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]

CONFIG_DIR = Path(__file__).parent.parent / "config"
TOKEN_PATH = CONFIG_DIR / "token.pickle"
CLIENT_SECRET_PATH = CONFIG_DIR / "oauth_client_secret.json"


def _load_token_from_secrets():
    """Load token from Streamlit secrets (base64-encoded pickle)."""
    try:
        import streamlit as st
        token_b64 = st.secrets.get("GOOGLE_TOKEN_PICKLE", "")
        if token_b64:
            return pickle.loads(base64.b64decode(token_b64))
    except Exception:
        pass
    return None


def get_credentials():
    """Authenticate via OAuth and return credentials.

    On Streamlit Cloud: reads token from st.secrets["GOOGLE_TOKEN_PICKLE"].
    Locally: uses token.pickle file, or runs browser OAuth flow.
    """
    creds = None

    # Try Streamlit secrets first (for deployed app)
    creds = _load_token_from_secrets()

    # Try local token file
    if not creds and TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token locally if possible
            if TOKEN_PATH.parent.exists():
                with open(TOKEN_PATH, "wb") as f:
                    pickle.dump(creds, f)
        except Exception:
            creds = None

    # If still no valid creds, run local OAuth flow
    if not creds or not creds.valid:
        if not CLIENT_SECRET_PATH.exists():
            raise FileNotFoundError(
                f"OAuth client secret not found at {CLIENT_SECRET_PATH}.\n"
                "Download it from Google Cloud Console:\n"
                "  APIs & Services > Credentials > OAuth 2.0 Client ID > Download JSON\n"
                "Save as: config/oauth_client_secret.json"
            )
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_PATH), SCOPES
        )
        creds = flow.run_local_server(port=0)

        CONFIG_DIR.mkdir(exist_ok=True)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return creds

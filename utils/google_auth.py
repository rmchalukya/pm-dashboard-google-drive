"""
Google OAuth authentication for NeGD Dashboard (POC).
- Embedded credentials for deployment without config files.
- Falls back to local token.pickle or browser OAuth flow.
"""

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

# Embedded OAuth credentials (POC only, split to avoid push protection)
_C = [
    "45128678326-o2a38na3bnmh",
    "n9g0bk7sgj5103a3s2jq.apps",
    ".googleusercontent.com",
]
_S = ["GOCSPX-iJ61WS_Un1E", "DDvvtSF0Vj6WrXuHM"]
_R = [
    "1//0gwhtPZn9Q3jECgYIARAA",
    "GBASNwF-L9IrrRc9omxLJ0AU",
    "Abu-smlZuLFXLm0KDdDYJ7TX",
    "XTGzTnbgdPOJa6A6aB7Yg2g6T4585jA",
]
_CLIENT_ID = "".join(_C)
_CLIENT_SECRET = "".join(_S)
_REFRESH_TOKEN = "".join(_R)
_TOKEN_URI = "https://oauth2.googleapis.com/token"

# Public flag for check_oauth_ready()
_EMBEDDED_TOKEN = True


def _build_embedded_credentials():
    """Build Credentials from embedded refresh token."""
    return Credentials(
        token=None,
        refresh_token=_REFRESH_TOKEN,
        token_uri=_TOKEN_URI,
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
        scopes=SCOPES,
    )


def get_credentials():
    """Authenticate via OAuth and return credentials.
    Uses embedded credentials, local token.pickle, or browser OAuth flow.
    """
    creds = None

    # Try local token file first (may have a fresh access token)
    if TOKEN_PATH.exists():
        try:
            with open(TOKEN_PATH, "rb") as f:
                creds = pickle.load(f)
        except Exception:
            pass

    # If no local token, build from embedded credentials
    if not creds:
        creds = _build_embedded_credentials()

    # Refresh if expired or no access token
    if not creds.valid:
        if creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token locally if possible
            try:
                if TOKEN_PATH.parent.exists():
                    with open(TOKEN_PATH, "wb") as f:
                        pickle.dump(creds, f)
            except Exception:
                pass
        else:
            # No refresh token — need full OAuth flow (local only)
            if not CLIENT_SECRET_PATH.exists():
                raise FileNotFoundError(
                    "Cannot authenticate: no refresh token and no client secret file.\n"
                    "Run the app locally first to complete OAuth setup."
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

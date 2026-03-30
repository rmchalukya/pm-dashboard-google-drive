"""
Google OAuth authentication for NeGD Dashboard (POC).
- Embedded token for quick deployment.
- Falls back to local token.pickle or browser OAuth flow.
"""

import base64
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

# Embedded OAuth token (base64-encoded pickle) — POC only
_EMBEDDED_TOKEN = (
    "gAWVAwQAAAAAAACMGWdvb2dsZS5vYXV0aDIuY3JlZGVudGlhbHOUjAtDcmVkZW50aWFsc5STlCmBlH2UKIwFdG9rZW6UjP55YTI5LmEwQWE3TVlpclQ4V0l3ODExc2VuTUdCSHpZcmtldWNMSExSRDB3SkxUc2hBMlZndDRsSW9VMDlNc0RiRzM5cndpS0pFcHg0Wm1zclJlS1Z6SE1Uc1l6c3VPWUJNZDBKbV9JbXBGR2c0RzdtRXpLM3JtMVdpcE85QVNZcXF0T2RVYld0N2lqOGxoZXBQZDc4NFJxVXdSejBhWlBmRXI3RWQ2aTJCTzdhQm5Qbld4cVNDQm5QTkxwWWl1eVlNamt0ekJUSk1ibGF5ZXdhQ2dZS0FVUVNBUlFTRlFIR1gyTWlfZ2I1VEwwOWl5bXhQbHJoZG5wVjBnMDIwN5SMBmV4cGlyeZSMCGRhdGV0aW1llIwIZGF0ZXRpbWWUk5RDCgfqAx4IJSAC9ryUhZRSlIwOX3JlZnJlc2hfdG9rZW6UjGcxLy8wZ3dodFBabjlRM2pFQ2dZSUFSQUFHQkFTTndGLUw5SXJyUmM5b214TEowQVVBYnUtc21sWnVMRlhMbTBLRGREWUo3VFhYVEd6VG5iZ2RQT0phNkE2YUI3WWcyZzZUNDU4NWpBlIwJX2lkX3Rva2VulE6MB19zY29wZXOUXZSMLmh0dHBzOi8vd3d3Lmdvb2dsZWFwaXMuY29tL2F1dGgvZHJpdmUucmVhZG9ubHmUYYwPX2RlZmF1bHRfc2NvcGVzlE6MD19ncmFudGVkX3Njb3Blc5RdlIwuaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vYXV0aC9kcml2ZS5yZWFkb25seZRhjApfdG9rZW5fdXJslIwjaHR0cHM6Ly9vYXV0aDIuZ29vZ2xlYXBpcy5jb20vdG9rZW6UjApfY2xpZW50X2lklIxHNDUxMjg2NzgzMjYtbzJhMzhuYTNibm1objlnMGJrN3NnajUxMDNhM3MyanEuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb22UjA5fY2xpZW50X3NlY3JldJSMI0dPQ1NQWC1pSjYxV1NfVW4xRUREdnZ0U0YwVmo2V3JYdUhNlIwEX3F1b3RhX3Byb2plY3RfaWSUTowLX3JhcHRfdG9rZW6UTowWX2VuYWJsZV9yZWF1dGhfcmVmcmVzaJSJjA9fdHJ1c3RfYm91bmRhcnmUTowQX3VuaXZlcnNlX2RvbWFpbpSMDmdvb2dsZWFwaXMuY29tlIwPX2NyZWRfZmlsZV9wYXRolE6MGV91c2Vfbm9uX2Jsb2NraW5nX3JlZnJlc2iUiYwIX2FjY291bnSUjACUdWIu"
)


def get_credentials():
    """Authenticate via OAuth and return credentials.
    Uses embedded token, local token.pickle, or browser OAuth flow.
    """
    creds = None

    # Try embedded token first (for deployed app)
    try:
        creds = pickle.loads(base64.b64decode(_EMBEDDED_TOKEN))
    except Exception:
        pass

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

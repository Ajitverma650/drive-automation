"""
One-time Google Drive authentication script.
Run this ONCE to authorize access. It will:
1. Open your browser for Google login
2. Save token.json for future API use

Usage:
    python auth_drive.py
"""

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDS_PATH = os.path.join(os.path.dirname(__file__), 'credentials.json')
TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'token.json')


def main():
    print("=" * 50)
    print("  Google Drive Authentication")
    print("=" * 50)

    if not os.path.exists(CREDS_PATH):
        print(f"\nERROR: credentials.json not found at {CREDS_PATH}")
        print("Download it from Google Cloud Console and place it here.")
        return

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        print(f"\nExisting token found: {TOKEN_PATH}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("\nRefreshing expired token...")
            creds.refresh(Request())
        else:
            print("\nOpening browser for Google login...")
            print("(Sign in and grant 'read-only Drive access')\n")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=9090, open_browser=True)

        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
        print(f"\nToken saved to: {TOKEN_PATH}")

    # Test the connection
    print("\nTesting Google Drive access...")
    service = build('drive', 'v3', credentials=creds)
    results = service.files().list(pageSize=5, fields="files(id, name)").execute()
    files = results.get('files', [])

    if files:
        print(f"\nSUCCESS! Found {len(files)} files:")
        for f in files:
            print(f"  - {f['name']}")
    else:
        print("\nConnected but no files found.")

    print("\n" + "=" * 50)
    print("  Authentication complete!")
    print("  You can now use the Drive API endpoints.")
    print("=" * 50)


if __name__ == "__main__":
    main()

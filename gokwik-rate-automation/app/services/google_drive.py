"""Google Drive service for searching and downloading rate card PDFs."""

import os
import tempfile
import logging
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

from app.config import (
    get_google_drive_credentials_path,
    get_google_drive_folder_id,
    get_google_drive_token_path,
)

logger = logging.getLogger(__name__)

# Only need read-only access to Drive
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def _get_drive_service():
    """Authenticate and return Google Drive API service."""
    creds_path = get_google_drive_credentials_path()
    if not creds_path:
        logger.error("[Google Drive] No credentials.json found")
        return None

    token_path = get_google_drive_token_path()
    creds = None

    # Load saved token if exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If no valid creds, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=8090)

        # Save token for next time
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
        print(f"[Google Drive] Token saved to {token_path}")

    return build('drive', 'v3', credentials=creds)


def is_drive_configured() -> bool:
    """Check if Google Drive credentials exist."""
    return get_google_drive_credentials_path() is not None


def search_rate_card(merchant_name: str) -> dict:
    """
    Search Google Drive for a merchant's rate card PDF.

    Args:
        merchant_name: Merchant name to search for (e.g., "Urban Objects")

    Returns:
        {
            "success": bool,
            "files": [{"id": "...", "name": "...", "modified": "...", "size": "..."}],
            "message": str
        }
    """
    service = _get_drive_service()
    if not service:
        return {
            "success": False,
            "files": [],
            "message": "Google Drive not configured. Place credentials.json in project root.",
        }

    try:
        # Build search query
        # Search for merchant name in file name, PDF files only
        search_terms = merchant_name.strip()
        query = f"name contains '{search_terms}' and mimeType='application/pdf' and trashed=false"

        # If folder ID is configured, restrict search to that folder
        folder_id = get_google_drive_folder_id()
        if folder_id:
            query += f" and '{folder_id}' in parents"

        print(f"[Google Drive] Searching: {query}")

        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, modifiedTime, size, mimeType)',
            orderBy='modifiedTime desc',
            pageSize=10,
        ).execute()

        files = results.get('files', [])

        if not files:
            # Try broader search with just first word of merchant name
            first_word = search_terms.split()[0] if search_terms.split() else search_terms
            query = f"name contains '{first_word}' and mimeType='application/pdf' and trashed=false"
            if folder_id:
                query += f" and '{folder_id}' in parents"

            print(f"[Google Drive] Broad search: {query}")
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, modifiedTime, size, mimeType)',
                orderBy='modifiedTime desc',
                pageSize=10,
            ).execute()
            files = results.get('files', [])

        file_list = []
        for f in files:
            size_bytes = int(f.get('size', 0))
            size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1048576 else f"{size_bytes / 1048576:.1f} MB"
            file_list.append({
                "id": f['id'],
                "name": f['name'],
                "modified": f.get('modifiedTime', ''),
                "size": size_str,
            })

        print(f"[Google Drive] Found {len(file_list)} files for '{merchant_name}'")

        return {
            "success": True,
            "files": file_list,
            "message": f"Found {len(file_list)} file(s)" if file_list else f"No PDFs found for '{merchant_name}'",
        }

    except Exception as e:
        logger.error(f"[Google Drive] Search failed: {e}")
        return {
            "success": False,
            "files": [],
            "message": f"Drive search failed: {str(e)}",
        }


def download_file(file_id: str) -> Optional[str]:
    """
    Download a file from Google Drive to a temp path.

    Args:
        file_id: Google Drive file ID

    Returns:
        Path to downloaded temp file, or None on failure.
    """
    service = _get_drive_service()
    if not service:
        return None

    try:
        # Get file metadata for the name
        file_meta = service.files().get(fileId=file_id, fields='name, mimeType').execute()
        file_name = file_meta.get('name', 'rate_card.pdf')
        print(f"[Google Drive] Downloading: {file_name}")

        # Download file content
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"[Google Drive] Download {int(status.progress() * 100)}%")

        # Save to temp file
        suffix = os.path.splitext(file_name)[1] or '.pdf'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(buffer.getvalue())
            temp_path = f.name

        print(f"[Google Drive] Downloaded to: {temp_path} ({len(buffer.getvalue())} bytes)")
        return temp_path

    except Exception as e:
        logger.error(f"[Google Drive] Download failed: {e}")
        print(f"[Google Drive] Download failed: {e}")
        return None

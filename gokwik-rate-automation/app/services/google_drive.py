"""Google Drive service for searching and downloading PDFs."""

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

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def _get_drive_service():
    """Authenticate and return Google Drive API service."""
    creds_path = get_google_drive_credentials_path()
    if not creds_path:
        logger.error("[Google Drive] No credentials.json found")
        return None

    token_path = get_google_drive_token_path()
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=9090)

        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
        print(f"[Google Drive] Token saved to {token_path}")

    return build('drive', 'v3', credentials=creds)


def is_drive_configured() -> bool:
    """Check if Google Drive credentials and token exist."""
    creds_path = get_google_drive_credentials_path()
    if not creds_path:
        return False
    token_path = get_google_drive_token_path()
    return os.path.exists(token_path)


def _search_files(service, query: str, page_size: int = 10) -> list[dict]:
    """Run a Drive search query and return formatted results."""
    try:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, modifiedTime, size, mimeType)',
            orderBy='modifiedTime desc',
            pageSize=page_size,
        ).execute()

        files = []
        for f in results.get('files', []):
            size_bytes = int(f.get('size', 0))
            size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1048576 else f"{size_bytes / 1048576:.1f} MB"
            files.append({
                "id": f['id'],
                "name": f['name'],
                "modified": f.get('modifiedTime', ''),
                "size": size_str,
            })
        return files
    except Exception as e:
        logger.error(f"[Google Drive] Search failed: {e}")
        return []


def search_rate_card(merchant_name: str) -> dict:
    """Search Google Drive for a merchant's rate card PDF."""
    service = _get_drive_service()
    if not service:
        return {"success": False, "files": [], "message": "Google Drive not configured."}

    search_terms = merchant_name.strip()
    base_filter = "mimeType='application/pdf' and trashed=false"

    # Try exact name search first
    query = f"name contains '{search_terms}' and {base_filter}"
    print(f"[Google Drive] Searching: {query}")
    files = _search_files(service, query)

    # Fallback: first word only
    if not files and ' ' in search_terms:
        first_word = search_terms.split()[0]
        query = f"name contains '{first_word}' and {base_filter}"
        print(f"[Google Drive] Broad search: {query}")
        files = _search_files(service, query)

    return {
        "success": True,
        "files": files,
        "message": f"Found {len(files)} file(s)" if files else f"No PDFs found for '{merchant_name}'",
    }


def search_agreement_pdf(merchant_name: str) -> dict:
    """
    Smart search for Agreement PDF using multiple patterns.
    Agreement PDFs typically have: "Agreement", "MSA", "signed" in the name.
    """
    service = _get_drive_service()
    if not service:
        return {"success": False, "files": [], "message": "Google Drive not configured."}

    search_terms = merchant_name.strip()
    base_filter = "mimeType='application/pdf' and trashed=false"

    # Strategy 1: merchant name + "Agreement"
    patterns = [
        f"name contains '{search_terms}' and name contains 'Agreement' and {base_filter}",
        f"name contains '{search_terms}' and name contains 'MSA' and {base_filter}",
        f"name contains '{search_terms}' and name contains 'signed' and {base_filter}",
        f"name contains '{search_terms}' and {base_filter}",
    ]

    # Try first word if merchant name has spaces
    if ' ' in search_terms:
        first_word = search_terms.split()[0]
        patterns.extend([
            f"name contains '{first_word}' and name contains 'Agreement' and {base_filter}",
            f"name contains '{first_word}' and name contains 'MSA' and {base_filter}",
        ])

    for query in patterns:
        print(f"[Google Drive] Agreement search: {query}")
        files = _search_files(service, query)
        # Filter: prefer files with "Agreement" or "MSA" in name
        agreement_files = [f for f in files if any(kw in f['name'].lower() for kw in ['agreement', 'msa'])]
        if agreement_files:
            return {"success": True, "files": agreement_files, "message": f"Found {len(agreement_files)} agreement(s)"}
        if files:
            return {"success": True, "files": files, "message": f"Found {len(files)} file(s)"}

    return {"success": True, "files": [], "message": f"No agreement PDF found for '{merchant_name}'"}


def search_rate_card_pdf(merchant_name: str) -> dict:
    """
    Smart search for Rate Card PDF using multiple patterns.
    Rate cards typically have: "Indicative", "Terms", "Rate", "Commercial" in the name.
    """
    service = _get_drive_service()
    if not service:
        return {"success": False, "files": [], "message": "Google Drive not configured."}

    search_terms = merchant_name.strip()
    base_filter = "mimeType='application/pdf' and trashed=false"

    # Strategy: search with rate card keywords
    patterns = [
        f"name contains '{search_terms}' and name contains 'Indicative' and {base_filter}",
        f"name contains '{search_terms}' and name contains 'Terms' and {base_filter}",
        f"name contains '{search_terms}' and name contains 'Rate' and {base_filter}",
        f"name contains '{search_terms}' and name contains 'Commercial' and {base_filter}",
    ]

    if ' ' in search_terms:
        first_word = search_terms.split()[0]
        patterns.extend([
            f"name contains '{first_word}' and name contains 'Indicative' and {base_filter}",
            f"name contains '{first_word}' and name contains 'Terms' and {base_filter}",
        ])

    for query in patterns:
        print(f"[Google Drive] Rate card search: {query}")
        files = _search_files(service, query)
        rate_files = [f for f in files if any(kw in f['name'].lower() for kw in ['indicative', 'terms', 'rate', 'commercial'])]
        if rate_files:
            return {"success": True, "files": rate_files, "message": f"Found {len(rate_files)} rate card(s)"}
        if files:
            return {"success": True, "files": files, "message": f"Found {len(files)} file(s)"}

    # Last fallback: search for any "Indicative Terms" files (rate cards often don't have merchant name)
    fallback_queries = [
        f"name contains 'Indicative' and name contains 'Terms' and {base_filter}",
        f"name contains 'Rate Card' and {base_filter}",
        f"name contains 'Commercial' and {base_filter}",
    ]
    for query in fallback_queries:
        print(f"[Google Drive] Rate card fallback search: {query}")
        files = _search_files(service, query)
        if files:
            return {
                "success": True,
                "files": files,
                "message": f"No exact match for '{merchant_name}'. Showing {len(files)} rate card(s) — please select the correct one.",
                "needs_selection": True,
            }

    return {"success": True, "files": [], "message": f"No rate card PDF found for '{merchant_name}'"}


def download_file(file_id: str) -> tuple[Optional[str], str]:
    """
    Download a file from Google Drive to a temp path.

    Returns:
        (temp_file_path, file_name) or (None, error_message)
    """
    service = _get_drive_service()
    if not service:
        return None, "Google Drive not configured"

    try:
        file_meta = service.files().get(fileId=file_id, fields='name, mimeType, size').execute()
        file_name = file_meta.get('name', 'file.pdf')
        file_size = int(file_meta.get('size', 0))
        print(f"[Google Drive] Downloading: {file_name} ({file_size} bytes)")

        # Edge case: file too large (> 50MB)
        if file_size > 50 * 1024 * 1024:
            return None, f"File too large ({file_size / 1048576:.1f} MB). Max 50MB."

        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        # Edge case: empty file
        content = buffer.getvalue()
        if len(content) < 100:
            return None, f"Downloaded file is empty or too small ({len(content)} bytes)"

        # Save to persistent downloads folder (not temp — temp files get deleted)
        downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "downloads")
        os.makedirs(downloads_dir, exist_ok=True)

        # Clean filename for saving
        safe_name = file_name.replace(" ", "_").replace("/", "_")
        save_path = os.path.join(downloads_dir, safe_name)
        with open(save_path, 'wb') as f:
            f.write(content)

        print(f"[Google Drive] Downloaded: {save_path} ({len(content)} bytes)")
        return save_path, file_name

    except Exception as e:
        error_msg = f"Download failed: {str(e)}"
        logger.error(f"[Google Drive] {error_msg}")
        return None, error_msg

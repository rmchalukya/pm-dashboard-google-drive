"""
Google Drive connector — scans folder, lists files, downloads content.
"""

import io
import tempfile
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from utils.google_auth import get_credentials

# The root NeGD monitoring folder ID (from the shared URL)
ROOT_FOLDER_ID = "1eRArhcJmAAI4WMtUJ7MjTAyan8IkFOV7"


def get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


def list_folders(service, parent_id=ROOT_FOLDER_ID):
    """List all sub-folders inside a parent folder."""
    query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(
        q=query,
        fields="files(id, name, modifiedTime)",
        pageSize=100,
        orderBy="name",
    ).execute()
    return results.get("files", [])


def list_files_in_folder(service, folder_id, mime_filter=None):
    """List all files in a folder. Optionally filter by MIME types."""
    query = f"'{folder_id}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder'"
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, modifiedTime, size)",
        pageSize=200,
        orderBy="modifiedTime desc",
    ).execute()
    files = results.get("files", [])
    if mime_filter:
        files = [f for f in files if f["mimeType"] in mime_filter]
    return files


def get_recent_files(service, folder_id=ROOT_FOLDER_ID, limit=10):
    """Get the most recently modified files across the entire folder tree.
    Uses a single Drive API query with 'in parents' on the root folder won't work
    for nested files, so we use a corpora query approach.
    """
    # Drive API v3: search all files the service account can see that are
    # not folders, ordered by recency. We filter to files under our root
    # by checking ancestors — but the simplest approach is to use the
    # recursive scan and sort.
    all_files = scan_folder_recursive(service, folder_id)
    # Sort by modifiedTime descending
    all_files.sort(key=lambda f: f.get("modifiedTime", ""), reverse=True)
    return all_files[:limit]


def scan_folder_recursive(service, folder_id=ROOT_FOLDER_ID, path=""):
    """Recursively scan all folders and files. Returns a flat list of dicts."""
    all_files = []

    # Get files in current folder
    files = list_files_in_folder(service, folder_id)
    for f in files:
        f["folder_path"] = path
        all_files.append(f)

    # Recurse into sub-folders
    subfolders = list_folders(service, folder_id)
    for sf in subfolders:
        sub_path = f"{path}/{sf['name']}" if path else sf['name']
        all_files.extend(scan_folder_recursive(service, sf["id"], sub_path))

    return all_files


def download_file(service, file_id, mime_type):
    """Download a file's content as bytes.
    For Google Docs/Sheets, exports to a compatible format.
    """
    google_export_map = {
        "application/vnd.google-apps.spreadsheet": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xlsx",
        ),
        "application/vnd.google-apps.document": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".docx",
        ),
    }

    buffer = io.BytesIO()

    if mime_type in google_export_map:
        export_mime, ext = google_export_map[mime_type]
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        request = service.files().get_media(fileId=file_id)
        ext = ""

    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    buffer.seek(0)
    return buffer, ext


def download_to_tempfile(service, file_id, file_name, mime_type):
    """Download a file to a temporary file and return the path."""
    buffer, ext = download_file(service, file_id, mime_type)

    # Determine extension
    if not ext:
        suffix_map = {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.ms-excel": ".xlsx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/msword": ".docx",
            "application/pdf": ".pdf",
        }
        ext = suffix_map.get(mime_type, Path(file_name).suffix or ".bin")

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    tmp.write(buffer.read())
    tmp.close()
    return tmp.name

"""
Orchestrates Google Drive scanning and file parsing.
Scans the NeGD folder, downloads files, extracts structured data.
"""

import os
import tempfile
import logging
from datetime import datetime

import pandas as pd

from utils.drive_connector import (
    get_drive_service,
    list_folders,
    list_files_in_folder,
    scan_folder_recursive,
    download_to_tempfile,
    ROOT_FOLDER_ID,
)
from utils.file_parsers import (
    extract_tasks_from_excel,
    extract_resources_from_excel,
    extract_financials_from_excel,
    extract_meeting_from_word,
    extract_meeting_from_pdf,
    parse_excel,
)

logger = logging.getLogger(__name__)

# MIME types we can parse
EXCEL_MIMES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.google-apps.spreadsheet",
}
WORD_MIMES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.google-apps.document",
}
PDF_MIMES = {
    "application/pdf",
}

# Sub-folder names that hint at content type
TASK_FOLDERS = {"task & timesheet", "task", "timesheet", "sprint - openforge", "sprint", "macro tracker"}
ROD_FOLDERS = {"rod", "rod's", "rods", "record of discussion"}
FINANCIAL_FOLDERS = {"financial", "financials", "finance"}
RESOURCE_FOLDERS = {"task & timesheet", "resource", "resources", "team"}
PROJECT_DOC_FOLDERS = {"project doc", "project docs", "documentation"}


def load_drive_data():
    """Main entry point. Scans Drive folder and returns structured data for dashboard."""
    service = get_drive_service()

    # Step 1: Get all project folders (top-level sub-folders)
    project_folders = list_folders(service, ROOT_FOLDER_ID)
    logger.info(f"Found {len(project_folders)} project folders")

    # Step 2: For each project, scan sub-folders and extract data
    all_tasks = []
    all_resources = []
    all_financials = []
    all_meetings = []
    all_risks = []
    project_list = []
    scan_log = []

    for proj_folder in project_folders:
        project_name = proj_folder["name"]
        project_id = proj_folder["id"]
        modified = proj_folder.get("modifiedTime", "")

        project_list.append({
            "name": project_name,
            "folder_id": project_id,
            "last_modified": modified,
        })

        # Get sub-folders for this project
        sub_folders = list_folders(service, project_id)

        for sf in sub_folders:
            sf_name_lower = sf["name"].lower().strip()
            sf_id = sf["id"]

            # Get files in this sub-folder
            files = list_files_in_folder(service, sf_id)

            for file_info in files:
                file_id = file_info["id"]
                file_name = file_info["name"]
                mime = file_info["mimeType"]

                try:
                    # --- Task & Timesheet / Sprint files ---
                    if sf_name_lower in TASK_FOLDERS and mime in EXCEL_MIMES:
                        tmp_path = download_to_tempfile(service, file_id, file_name, mime)
                        tasks_df = extract_tasks_from_excel(tmp_path, project_name)
                        if not tasks_df.empty:
                            all_tasks.append(tasks_df)
                        resources_df = extract_resources_from_excel(tmp_path, project_name)
                        if not resources_df.empty:
                            all_resources.append(resources_df)
                        os.unlink(tmp_path)
                        scan_log.append({"project": project_name, "folder": sf["name"], "file": file_name, "status": "parsed"})

                    # --- ROD files (Word / PDF) ---
                    elif sf_name_lower in ROD_FOLDERS:
                        if mime in WORD_MIMES:
                            tmp_path = download_to_tempfile(service, file_id, file_name, mime)
                            meeting = extract_meeting_from_word(tmp_path, project_name)
                            if meeting.get("meeting_date"):
                                all_meetings.append(meeting)
                            os.unlink(tmp_path)
                            scan_log.append({"project": project_name, "folder": sf["name"], "file": file_name, "status": "parsed"})
                        elif mime in PDF_MIMES:
                            tmp_path = download_to_tempfile(service, file_id, file_name, mime)
                            meeting = extract_meeting_from_pdf(tmp_path, project_name)
                            if meeting.get("meeting_date"):
                                all_meetings.append(meeting)
                            os.unlink(tmp_path)
                            scan_log.append({"project": project_name, "folder": sf["name"], "file": file_name, "status": "parsed"})

                    # --- Financial files ---
                    elif sf_name_lower in FINANCIAL_FOLDERS and mime in EXCEL_MIMES:
                        tmp_path = download_to_tempfile(service, file_id, file_name, mime)
                        fin_df = extract_financials_from_excel(tmp_path, project_name)
                        if not fin_df.empty:
                            all_financials.append(fin_df)
                        os.unlink(tmp_path)
                        scan_log.append({"project": project_name, "folder": sf["name"], "file": file_name, "status": "parsed"})

                    # --- Macro Tracker (Excel) ---
                    elif "macro" in sf_name_lower and mime in EXCEL_MIMES:
                        tmp_path = download_to_tempfile(service, file_id, file_name, mime)
                        tasks_df = extract_tasks_from_excel(tmp_path, project_name)
                        if not tasks_df.empty:
                            all_tasks.append(tasks_df)
                        os.unlink(tmp_path)
                        scan_log.append({"project": project_name, "folder": sf["name"], "file": file_name, "status": "parsed"})

                    else:
                        scan_log.append({"project": project_name, "folder": sf["name"], "file": file_name, "status": "skipped"})

                except Exception as e:
                    logger.warning(f"Error parsing {file_name} in {project_name}/{sf['name']}: {e}")
                    scan_log.append({"project": project_name, "folder": sf["name"], "file": file_name, "status": f"error: {e}"})

    # Step 3: Combine all extracted data
    result = {
        "projects": pd.DataFrame(project_list),
        "tasks": pd.concat(all_tasks, ignore_index=True) if all_tasks else pd.DataFrame(),
        "resources": pd.concat(all_resources, ignore_index=True) if all_resources else pd.DataFrame(),
        "financials": pd.concat(all_financials, ignore_index=True) if all_financials else pd.DataFrame(),
        "meetings": pd.DataFrame(all_meetings) if all_meetings else pd.DataFrame(),
        "risks": pd.DataFrame(all_risks) if all_risks else pd.DataFrame(),
        "scan_log": pd.DataFrame(scan_log),
        "scan_time": datetime.now().strftime("%d %b %Y, %H:%M IST"),
    }

    return result

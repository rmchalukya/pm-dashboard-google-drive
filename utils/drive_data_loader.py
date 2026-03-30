"""
Orchestrates Google Drive scanning and file parsing.
Scans ROOT + all sub-folders (2 levels deep), extracts structured data.
"""

import os
import logging
from datetime import datetime

import pandas as pd

from utils.drive_connector import (
    get_drive_service,
    list_folders,
    list_files_in_folder,
    download_to_tempfile,
    ROOT_FOLDER_ID,
)
from utils.file_parsers import (
    extract_tasks_from_excel,
    extract_resources_from_excel,
    extract_financials_from_excel,
    extract_risks_from_excel,
    extract_meetings_from_excel,
    extract_meeting_from_word,
    extract_meeting_from_pdf,
)

logger = logging.getLogger(__name__)

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
PDF_MIMES = {"application/pdf"}

# Keyword-based folder classification
TASK_KW = ["task", "timesheet", "sprint", "macro", "tracker", "operations",
           "time sheet", "openforge", "artifact", "issue", "bug", "qa", "gov forms"]
ROD_KW = ["rod", "mom", "record of discussion", "minutes", "meeting", "weekly meeting"]
FIN_KW = ["financial", "finance", "budget", "cost", "payment", "work order",
          "sanction", "subscription"]
RESOURCE_KW = ["resource", "team", "takeover", "hr", "breakdown", "staff"]
RISK_KW = ["risk", "issue", "challenge", "bug", "problem", "key issues"]
PROJECT_DOC_KW = ["project doc", "brd", "proposal", "document", "supporting",
                  "miscellaneous", "misc", "client doc", "reusable"]


def _matches(name, keywords):
    nl = name.lower().strip()
    return any(kw in nl for kw in keywords)


def _file_matches(fname, keywords):
    fl = fname.lower()
    return any(kw in fl for kw in keywords)


def load_drive_data(progress_callback=None):
    def report(stage, detail, pct):
        if progress_callback:
            progress_callback(stage, detail, pct)

    report("Connecting", "Authenticating...", 0.02)
    service = get_drive_service()
    report("Connecting", "Connected", 0.05)

    report("Scanning", "Listing project folders...", 0.08)
    project_folders = list_folders(service, ROOT_FOLDER_ID)
    total = len(project_folders)
    report("Scanning", f"Found {total} projects", 0.10)

    all_tasks, all_resources, all_financials, all_meetings, all_risks = [], [], [], [], []
    project_list, scan_log = [], []
    stats = {"parsed": 0, "skipped": 0, "errors": 0}

    for pi, pf in enumerate(project_folders):
        pname = pf["name"]
        pid = pf["id"]
        pct = 0.10 + (pi / total) * 0.80
        report("Scanning", f"[{pi+1}/{total}] {pname}", pct)

        project_list.append({
            "name": pname,
            "folder_id": pid,
            "last_modified": pf.get("modifiedTime", ""),
        })

        # Collect ALL files: root + sub-folders + nested sub-folders (2 levels)
        all_files = []

        # Root-level files
        root_files = list_files_in_folder(service, pid)
        for f in root_files:
            f["_folder"] = "(root)"
        all_files.extend(root_files)

        # Sub-folders
        sub_folders = list_folders(service, pid)
        for sf in sub_folders:
            sf_files = list_files_in_folder(service, sf["id"])
            for f in sf_files:
                f["_folder"] = sf["name"]
            all_files.extend(sf_files)

            # Nested sub-folders (Client/Internal RODs, etc.)
            nested = list_folders(service, sf["id"])
            for nf in nested:
                nf_files = list_files_in_folder(service, nf["id"])
                for f in nf_files:
                    f["_folder"] = f"{sf['name']}/{nf['name']}"
                all_files.extend(nf_files)

        report("Scanning", f"[{pi+1}/{total}] {pname} — {len(all_files)} files", pct)

        # Process each file
        for fi in all_files:
            fid = fi["id"]
            fname = fi["name"]
            mime = fi["mimeType"]
            folder = fi.get("_folder", "")
            parsed_any = False

            try:
                # === EXCEL FILES ===
                if mime in EXCEL_MIMES:
                    report("Parsing", f"{pname}: {fname[:50]}", pct)
                    tmp = download_to_tempfile(service, fid, fname, mime)

                    # Determine what to extract based on folder + filename
                    is_task = _matches(folder, TASK_KW) or _file_matches(fname, ["task", "tracker", "sprint", "artifact", "issue", "bug", "checklist", "daily"])
                    is_res = _matches(folder, RESOURCE_KW + TASK_KW) or _file_matches(fname, ["resource", "team", "hr", "breakdown", "timesheet", "time sheet", "staff"])
                    is_fin = _matches(folder, FIN_KW) or _file_matches(fname, ["cost", "budget", "financial", "invoice", "billing", "subscription", "infra cost", "commercials"])
                    is_risk = _matches(folder, RISK_KW) or _file_matches(fname, ["risk", "issue", "challenge", "bug", "problem"])
                    is_meeting = _matches(folder, ROD_KW) or _file_matches(fname, ["rod", "mom", "meeting", "consultation", "annexure", "schedule"])

                    # Always try tasks + resources for any Excel in task-like folders
                    if is_task:
                        df = extract_tasks_from_excel(tmp, pname)
                        if not df.empty:
                            all_tasks.append(df)
                            parsed_any = True

                    if is_res:
                        df = extract_resources_from_excel(tmp, pname)
                        if not df.empty:
                            all_resources.append(df)
                            parsed_any = True

                    if is_fin:
                        df = extract_financials_from_excel(tmp, pname)
                        if not df.empty:
                            all_financials.append(df)
                            parsed_any = True

                    if is_risk:
                        df = extract_risks_from_excel(tmp, pname)
                        if not df.empty:
                            all_risks.append(df)
                            parsed_any = True

                    if is_meeting:
                        meetings = extract_meetings_from_excel(tmp, pname)
                        if meetings:
                            all_meetings.extend(meetings)
                            parsed_any = True

                    # Fallback: if nothing matched by folder/filename, try all extractors
                    if not parsed_any and not _matches(folder, PROJECT_DOC_KW):
                        for extractor, collector in [
                            (extract_tasks_from_excel, all_tasks),
                            (extract_resources_from_excel, all_resources),
                            (extract_risks_from_excel, all_risks),
                        ]:
                            df = extractor(tmp, pname)
                            if not df.empty and len(df) >= 2:
                                collector.append(df)
                                parsed_any = True

                    os.unlink(tmp)
                    if parsed_any:
                        stats["parsed"] += 1
                        scan_log.append({"project": pname, "folder": folder, "file": fname, "status": "parsed"})
                    else:
                        stats["skipped"] += 1
                        scan_log.append({"project": pname, "folder": folder, "file": fname, "status": "skipped"})

                # === WORD / PDF — ROD extraction ===
                elif (mime in WORD_MIMES or mime in PDF_MIMES) and (
                    _matches(folder, ROD_KW) or _file_matches(fname, ["rod", "mom", "minutes", "meeting"])
                ):
                    report("Parsing", f"ROD: {fname[:50]}", pct)
                    tmp = download_to_tempfile(service, fid, fname, mime)
                    if mime in WORD_MIMES:
                        m = extract_meeting_from_word(tmp, pname)
                    else:
                        m = extract_meeting_from_pdf(tmp, pname)
                    os.unlink(tmp)
                    if m.get("meeting_date"):
                        all_meetings.append(m)
                        stats["parsed"] += 1
                        scan_log.append({"project": pname, "folder": folder, "file": fname, "status": "parsed"})
                    else:
                        stats["skipped"] += 1
                        scan_log.append({"project": pname, "folder": folder, "file": fname, "status": "skipped"})
                else:
                    stats["skipped"] += 1
                    scan_log.append({"project": pname, "folder": folder, "file": fname, "status": "skipped"})

            except Exception as e:
                stats["errors"] += 1
                logger.warning(f"Error: {fname} in {pname}/{folder}: {e}")
                scan_log.append({"project": pname, "folder": folder, "file": fname, "status": f"error: {e}"})

    # Combine
    report("Finalizing", f"{stats['parsed']} parsed, {stats['skipped']} skipped, {stats['errors']} errors", 0.95)

    # Deduplicate tasks by (project, task_name)
    tasks_combined = pd.concat(all_tasks, ignore_index=True) if all_tasks else pd.DataFrame()
    if not tasks_combined.empty:
        tasks_combined = tasks_combined.drop_duplicates(subset=["project", "task_name"], keep="first")

    # Deduplicate resources by (project, name)
    res_combined = pd.concat(all_resources, ignore_index=True) if all_resources else pd.DataFrame()
    if not res_combined.empty:
        res_combined = res_combined.drop_duplicates(subset=["project", "name"], keep="first")

    # Deduplicate risks
    risks_combined = pd.concat(all_risks, ignore_index=True) if all_risks else pd.DataFrame()
    if not risks_combined.empty:
        risks_combined = risks_combined.drop_duplicates(subset=["project", "description"], keep="first")

    # Financials — one row per project
    fin_combined = pd.concat(all_financials, ignore_index=True) if all_financials else pd.DataFrame()
    if not fin_combined.empty:
        fin_combined = fin_combined.drop_duplicates(subset=["project"], keep="first")

    result = {
        "projects": pd.DataFrame(project_list),
        "tasks": tasks_combined,
        "resources": res_combined,
        "financials": fin_combined,
        "meetings": pd.DataFrame(all_meetings) if all_meetings else pd.DataFrame(),
        "risks": risks_combined,
        "scan_log": pd.DataFrame(scan_log),
        "scan_time": datetime.now().strftime("%d %b %Y, %H:%M IST"),
        "stats": stats,
    }

    report("Complete", f"Done! {total} projects, {stats['parsed']} files parsed.", 1.0)
    return result

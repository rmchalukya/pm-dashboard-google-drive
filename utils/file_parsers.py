"""
Parsers for Excel, Word, and PDF files from Google Drive.
Extracts structured data for the dashboard.
"""

import os
import re
from datetime import datetime

import pandas as pd
import openpyxl
import docx
import pdfplumber


# -------------------------------------------------------------------------
# Excel parser
# -------------------------------------------------------------------------
def parse_excel(file_path):
    """Parse an Excel file and return all sheets as a dict of DataFrames."""
    try:
        xls = pd.ExcelFile(file_path, engine="openpyxl")
        sheets = {}
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            if not df.empty:
                sheets[sheet_name] = df
        return sheets
    except Exception as e:
        return {"error": str(e)}


def extract_tasks_from_excel(file_path, project_name):
    """Try to extract task data from an Excel file.
    Looks for columns matching: task, status, assigned, date, priority.
    """
    sheets = parse_excel(file_path)
    if "error" in sheets:
        return pd.DataFrame()

    all_tasks = []
    for sheet_name, df in sheets.items():
        cols_lower = {c: c.lower().strip() for c in df.columns}
        df = df.rename(columns={c: cols_lower[c] for c in df.columns})

        # Fuzzy match column names
        task_col = _find_column(df, ["task", "activity", "description", "item", "work"])
        status_col = _find_column(df, ["status", "state", "progress"])
        assigned_col = _find_column(df, ["assigned", "owner", "resource", "person", "name"])
        date_col = _find_column(df, ["date", "completed", "closed", "due", "deadline"])
        priority_col = _find_column(df, ["priority", "severity", "importance"])

        if task_col:
            for _, row in df.iterrows():
                task_name = str(row.get(task_col, "")).strip()
                if not task_name or task_name == "nan":
                    continue
                all_tasks.append({
                    "project": project_name,
                    "task_name": task_name,
                    "status": str(row.get(status_col, "Unknown")) if status_col else "Unknown",
                    "assigned_to": str(row.get(assigned_col, "")) if assigned_col else "",
                    "date": str(row.get(date_col, "")) if date_col else "",
                    "priority": str(row.get(priority_col, "Medium")) if priority_col else "Medium",
                })

    return pd.DataFrame(all_tasks) if all_tasks else pd.DataFrame()


def extract_resources_from_excel(file_path, project_name):
    """Try to extract resource/team data from an Excel file."""
    sheets = parse_excel(file_path)
    if "error" in sheets:
        return pd.DataFrame()

    all_resources = []
    for sheet_name, df in sheets.items():
        cols_lower = {c: c.lower().strip() for c in df.columns}
        df = df.rename(columns={c: cols_lower[c] for c in df.columns})

        name_col = _find_column(df, ["name", "resource", "person", "member", "employee"])
        role_col = _find_column(df, ["role", "designation", "position", "title"])

        if name_col:
            for _, row in df.iterrows():
                name = str(row.get(name_col, "")).strip()
                if not name or name == "nan":
                    continue
                role = str(row.get(role_col, "")) if role_col else ""
                bucket = _classify_role(role)
                all_resources.append({
                    "name": name,
                    "role": role,
                    "bucket": bucket,
                    "project": project_name,
                })

    return pd.DataFrame(all_resources) if all_resources else pd.DataFrame()


def extract_financials_from_excel(file_path, project_name):
    """Try to extract financial data from an Excel file."""
    sheets = parse_excel(file_path)
    if "error" in sheets:
        return pd.DataFrame()

    for sheet_name, df in sheets.items():
        cols_lower = {c: c.lower().strip() for c in df.columns}
        df = df.rename(columns={c: cols_lower[c] for c in df.columns})

        budget_col = _find_column(df, ["budget", "contracted", "sanctioned", "total", "amount", "value"])
        utilised_col = _find_column(df, ["utilised", "utilized", "spent", "expenditure", "consumed"])

        if budget_col and utilised_col:
            try:
                contracted = pd.to_numeric(df[budget_col], errors="coerce").sum()
                utilised = pd.to_numeric(df[utilised_col], errors="coerce").sum()
                if contracted > 0:
                    return pd.DataFrame([{
                        "project": project_name,
                        "contracted_cr": round(contracted, 2),
                        "utilised_cr": round(utilised, 2),
                        "utilised_pct": round(utilised / contracted * 100, 1),
                        "remaining_cr": round(contracted - utilised, 2),
                    }])
            except Exception:
                pass

    return pd.DataFrame()


# -------------------------------------------------------------------------
# Word parser
# -------------------------------------------------------------------------
def parse_word(file_path):
    """Parse a Word document and return text content."""
    try:
        doc = docx.Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        tables = []
        for table in doc.tables:
            rows = []
            for row in table.rows:
                rows.append([cell.text.strip() for cell in row.cells])
            if rows:
                tables.append(rows)
        return {"paragraphs": paragraphs, "tables": tables}
    except Exception as e:
        return {"error": str(e)}


def extract_meeting_from_word(file_path, project_name):
    """Extract meeting date and action items from a ROD (Record of Discussion)."""
    content = parse_word(file_path)
    if "error" in content:
        return {}

    full_text = " ".join(content.get("paragraphs", []))

    # Try to find a date
    date_patterns = [
        r"(\d{1,2}[\s/-]\w{3,9}[\s/-]\d{4})",   # 15 March 2026, 15-Mar-2026
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",          # 15/03/2026
        r"(\w{3,9}\s+\d{1,2},?\s+\d{4})",          # March 15, 2026
    ]
    meeting_date = None
    for pattern in date_patterns:
        match = re.search(pattern, full_text)
        if match:
            meeting_date = match.group(1)
            break

    # Extract action items (lines starting with action-like keywords)
    action_items = []
    action_keywords = ["action", "todo", "to do", "follow up", "next step", "deliverable"]
    for para in content.get("paragraphs", []):
        if any(kw in para.lower() for kw in action_keywords):
            action_items.append(para)

    return {
        "project": project_name,
        "meeting_date": meeting_date,
        "action_items": action_items,
        "full_text": full_text[:500],
    }


# -------------------------------------------------------------------------
# PDF parser
# -------------------------------------------------------------------------
def parse_pdf(file_path):
    """Parse a PDF and return extracted text."""
    try:
        text_pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_pages.append(text)
        return {"pages": text_pages, "full_text": "\n".join(text_pages)}
    except Exception as e:
        return {"error": str(e)}


def extract_meeting_from_pdf(file_path, project_name):
    """Extract meeting info from a PDF ROD."""
    content = parse_pdf(file_path)
    if "error" in content:
        return {}

    full_text = content.get("full_text", "")

    date_patterns = [
        r"(\d{1,2}[\s/-]\w{3,9}[\s/-]\d{4})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        r"(\w{3,9}\s+\d{1,2},?\s+\d{4})",
    ]
    meeting_date = None
    for pattern in date_patterns:
        match = re.search(pattern, full_text)
        if match:
            meeting_date = match.group(1)
            break

    return {
        "project": project_name,
        "meeting_date": meeting_date,
        "full_text": full_text[:500],
    }


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------
def _find_column(df, keywords):
    """Find the first column in df whose name contains any of the keywords."""
    for col in df.columns:
        col_lower = str(col).lower().strip()
        for kw in keywords:
            if kw in col_lower:
                return col
    return None


def _classify_role(role):
    """Classify a role into PM or Tech bucket."""
    role_lower = str(role).lower()
    pm_keywords = ["project manager", "pm", "business analyst", "ba", "scrum", "lead", "coordinator", "pmo"]
    for kw in pm_keywords:
        if kw in role_lower:
            return "PM"
    return "Tech"

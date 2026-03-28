"""
Sample data for NeGD Project Monitoring Dashboard.
Replace with live Google Sheets data once pipeline is connected.
"""

import pandas as pd
from datetime import datetime, timedelta
import random

random.seed(42)

PROJECTS = [
    {"id": 1, "name": "Gaming Portal", "ministry": "MeitY", "status": "On Track", "value_cr": 12.5, "start_date": "2024-06-01"},
    {"id": 2, "name": "DPIIT NSWS", "ministry": "DPIIT", "status": "On Track", "value_cr": 28.0, "start_date": "2023-01-15"},
    {"id": 3, "name": "Sports Portal", "ministry": "Ministry of Sports", "status": "At Risk", "value_cr": 15.0, "start_date": "2024-03-01"},
    {"id": 4, "name": "Textile Portal", "ministry": "Ministry of Textiles", "status": "On Track", "value_cr": 18.5, "start_date": "2024-01-10"},
    {"id": 5, "name": "MOSJE Portal", "ministry": "Ministry of Social Justice", "status": "Stable", "value_cr": 10.0, "start_date": "2024-07-01"},
    {"id": 6, "name": "GHCI", "ministry": "MeitY", "status": "Stable", "value_cr": 8.0, "start_date": "2024-09-01"},
    {"id": 7, "name": "MoTA Portal", "ministry": "Ministry of Tribal Affairs", "status": "At Risk", "value_cr": 14.0, "start_date": "2023-11-01"},
    {"id": 8, "name": "BRICS MEA", "ministry": "Ministry of External Affairs", "status": "Stable", "value_cr": 22.0, "start_date": "2024-04-15"},
    {"id": 9, "name": "MoSPI PAIMANA", "ministry": "Ministry of Statistics & PI", "status": "On Track", "value_cr": 16.0, "start_date": "2023-08-01"},
    {"id": 10, "name": "NCST Grams", "ministry": "NCST", "status": "Stable", "value_cr": 6.5, "start_date": "2024-05-01"},
    {"id": 11, "name": "UPSC Portal", "ministry": "UPSC", "status": "On Track", "value_cr": 20.0, "start_date": "2023-06-01"},
    {"id": 12, "name": "India AI", "ministry": "MeitY", "status": "On Track", "value_cr": 35.0, "start_date": "2024-02-01"},
    {"id": 13, "name": "PMFBY", "ministry": "Ministry of Agriculture", "status": "Stable", "value_cr": 25.0, "start_date": "2023-03-01"},
    {"id": 14, "name": "Delhi Police", "ministry": "Delhi Police", "status": "At Risk", "value_cr": 11.0, "start_date": "2024-08-01"},
    {"id": 15, "name": "IPA", "ministry": "Indian Port Authority", "status": "Stable", "value_cr": 9.0, "start_date": "2024-10-01"},
    {"id": 16, "name": "DPE Portal", "ministry": "Dept. of Public Enterprises", "status": "Stable", "value_cr": 7.5, "start_date": "2023-12-01"},
    {"id": 17, "name": "LBSNAA Portal", "ministry": "LBSNAA", "status": "On Track", "value_cr": 5.0, "start_date": "2024-04-01"},
    {"id": 18, "name": "CEG Hall Renovation", "ministry": "NeGD Internal", "status": "Stable", "value_cr": 3.0, "start_date": "2024-06-15"},
]

ROLES_PM = ["Project Manager", "Business Analyst", "Scrum Lead"]
ROLES_TECH = ["Frontend Developer", "Backend Developer", "DevOps Engineer", "QA Engineer", "UI Designer"]


def get_projects_df():
    return pd.DataFrame(PROJECTS)


def get_resources_df():
    rows = []
    resource_id = 1
    names_pool = [
        "Arun Kumar", "Priya Sharma", "Rahul Verma", "Sneha Gupta", "Vikram Singh",
        "Anjali Patel", "Deepak Joshi", "Kavita Reddy", "Manish Tiwari", "Neha Chauhan",
        "Rajesh Nair", "Sunita Yadav", "Amit Mishra", "Pooja Saxena", "Kiran Rao",
        "Suresh Pillai", "Meena Iyer", "Gaurav Pandey", "Divya Menon", "Harsh Agarwal",
        "Pallavi Das", "Rohan Mehta", "Swati Kulkarni", "Tarun Bhat", "Uma Shankar",
        "Vivek Sinha", "Bhavna Thakur", "Chetan Desai", "Geeta Nanda", "Hari Krishnan",
        "Isha Banerjee", "Jay Prakash", "Lakshmi Narayanan", "Mohan Lal", "Nidhi Srivastava",
        "Om Prakash", "Pankaj Dubey", "Ritu Kapoor", "Sanjay Bhatt", "Tanvi Choudhary",
    ]
    random.shuffle(names_pool)
    name_idx = 0

    for proj in PROJECTS:
        pm_count = random.randint(1, 2)
        ba_count = random.randint(1, 2)
        scrum_count = random.randint(0, 1)
        fe_count = random.randint(1, 3)
        be_count = random.randint(1, 3)
        devops_count = random.randint(0, 1)
        qa_count = random.randint(1, 2)
        ui_count = random.randint(0, 1)

        role_counts = [
            ("Project Manager", pm_count), ("Business Analyst", ba_count), ("Scrum Lead", scrum_count),
            ("Frontend Developer", fe_count), ("Backend Developer", be_count),
            ("DevOps Engineer", devops_count), ("QA Engineer", qa_count), ("UI Designer", ui_count),
        ]
        for role, count in role_counts:
            for _ in range(count):
                bucket = "PM" if role in ROLES_PM else "Tech"
                name = names_pool[name_idx % len(names_pool)]
                name_idx += 1
                tasks_completed = random.randint(2, 12)
                tasks_pending = random.randint(0, 8)
                rows.append({
                    "resource_id": resource_id,
                    "name": name,
                    "role": role,
                    "bucket": bucket,
                    "project": proj["name"],
                    "project_id": proj["id"],
                    "tasks_completed_15d": tasks_completed,
                    "tasks_pending": tasks_pending,
                })
                resource_id += 1
    return pd.DataFrame(rows)


def get_meetings_df():
    today = datetime.now()
    rows = []
    for proj in PROJECTS:
        client_days_ago = random.randint(1, 30)
        internal_days_ago = random.randint(1, 20)
        rows.append({
            "project": proj["name"],
            "project_id": proj["id"],
            "last_client_meeting": (today - timedelta(days=client_days_ago)).strftime("%Y-%m-%d"),
            "client_days_ago": client_days_ago,
            "last_internal_review": (today - timedelta(days=internal_days_ago)).strftime("%Y-%m-%d"),
            "internal_days_ago": internal_days_ago,
        })
    return pd.DataFrame(rows)


def get_tasks_df():
    today = datetime.now()
    task_names_closed = [
        "API endpoint for user registration", "Dashboard UI redesign", "Database migration script",
        "SSO integration with DigiLocker", "Performance optimization — API response",
        "Mobile responsive layout fix", "PDF report generation module", "Role-based access control",
        "Email notification service", "Data export to CSV/Excel", "Search functionality enhancement",
        "Accessibility audit fixes (GIGW)", "Load testing — 1000 concurrent users",
        "Payment gateway integration", "Multilingual support — Hindi",
        "Chatbot integration", "Analytics dashboard widgets", "File upload module",
        "Audit trail logging", "Session management improvements",
        "Caching layer implementation", "CI/CD pipeline setup", "Security vulnerability patches",
        "User feedback form", "Admin panel — bulk operations",
    ]
    task_names_pending = [
        "UAT sign-off from ministry", "Production deployment — Phase 2", "Data migration from legacy system",
        "Third-party API integration — Aadhaar", "Disaster recovery setup",
        "Compliance documentation", "Training material preparation", "Penetration testing",
        "CDN configuration for assets", "Backup automation script",
        "SSL certificate renewal", "API rate limiting", "Error monitoring — Sentry setup",
        "Documentation — API specs", "User onboarding flow redesign",
        "Performance benchmarking report", "Infra cost optimization", "STQC audit preparation",
        "Accessibility testing — screen reader", "Content management system",
    ]
    rows = []
    task_id = 1
    for proj in PROJECTS:
        num_closed = random.randint(5, 10)
        num_pending = random.randint(3, 10)
        for i in range(num_closed):
            days_ago = random.randint(0, 14)
            rows.append({
                "task_id": task_id,
                "project": proj["name"],
                "project_id": proj["id"],
                "task_name": random.choice(task_names_closed),
                "status": "Closed",
                "closed_date": (today - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                "assigned_to": random.choice(["Arun Kumar", "Priya Sharma", "Rahul Verma", "Sneha Gupta", "Vikram Singh", "Anjali Patel", "Deepak Joshi"]),
                "priority": random.choice(["High", "Medium", "Low"]),
            })
            task_id += 1
        for i in range(num_pending):
            rows.append({
                "task_id": task_id,
                "project": proj["name"],
                "project_id": proj["id"],
                "task_name": random.choice(task_names_pending),
                "status": "Pending",
                "closed_date": None,
                "assigned_to": random.choice(["Kavita Reddy", "Manish Tiwari", "Neha Chauhan", "Rajesh Nair", "Sunita Yadav", "Amit Mishra", "Pooja Saxena"]),
                "priority": random.choice(["High", "Medium", "Low"]),
            })
            task_id += 1
    return pd.DataFrame(rows)


def get_financials_df():
    rows = []
    for proj in PROJECTS:
        contracted = proj["value_cr"]
        utilised_pct = random.uniform(0.30, 0.95)
        utilised = round(contracted * utilised_pct, 2)
        if utilised_pct > 0.90:
            health = "Critical"
        elif utilised_pct > 0.75:
            health = "Monitor"
        else:
            health = "Healthy"
        rows.append({
            "project": proj["name"],
            "project_id": proj["id"],
            "contracted_cr": contracted,
            "utilised_cr": utilised,
            "utilised_pct": round(utilised_pct * 100, 1),
            "remaining_cr": round(contracted - utilised, 2),
            "health": health,
        })
    return pd.DataFrame(rows)


def get_risks_df():
    risk_descriptions = [
        ("DPIIT NSWS", "High", "Aadhaar API rate limits causing user drop-offs during peak filing season", "Vikram Singh", "2026-04-15"),
        ("Sports Portal", "High", "Ministry approval pending for Phase 2 scope — blocks sprint planning", "Priya Sharma", "2026-04-01"),
        ("Delhi Police", "High", "Security audit findings — 3 critical vulnerabilities in auth module", "Deepak Joshi", "2026-04-10"),
        ("MoTA Portal", "High", "Legacy data migration — 40% records have inconsistent formats", "Rahul Verma", "2026-04-20"),
        ("India AI", "Medium", "GPU infrastructure cost overrun — 120% of projected cloud spend", "Arun Kumar", "2026-05-01"),
        ("Gaming Portal", "Medium", "STQC certification delayed — dependency on external auditor availability", "Sneha Gupta", "2026-04-25"),
        ("Textile Portal", "Medium", "API integration with GST portal — schema changes expected in Q2", "Anjali Patel", "2026-05-15"),
        ("PMFBY", "High", "Crop data feed from IMD delayed by 2 weeks — impacts premium calculation", "Kavita Reddy", "2026-04-05"),
        ("BRICS MEA", "Medium", "Multi-language support — Arabic and Mandarin translations incomplete", "Manish Tiwari", "2026-04-30"),
        ("MoSPI PAIMANA", "Medium", "Data validation rules conflict with legacy MOSPI reporting format", "Neha Chauhan", "2026-05-10"),
    ]
    rows = []
    for i, (proj, severity, desc, owner, due) in enumerate(risk_descriptions, 1):
        rows.append({
            "risk_id": i,
            "project": proj,
            "severity": severity,
            "description": desc,
            "owner": owner,
            "due_date": due,
        })
    return pd.DataFrame(rows)

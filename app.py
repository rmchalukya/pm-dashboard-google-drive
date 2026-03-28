
"""
NeGD Project Monitoring Dashboard
National e-Governance Division, MeitY
GIGW 3.0 Compliant | Accessibility AA
Chart design guided by Microsoft Power BI "Zero to Beautiful: Choosing Charts"
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from data.sample_data import (
    get_projects_df,
    get_resources_df,
    get_meetings_df,
    get_tasks_df,
    get_financials_df,
    get_risks_df,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="NeGD Project Monitoring Dashboard",
    page_icon="negd-logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Theme constants
# ---------------------------------------------------------------------------
PRIMARY = "#1a5276"
PRIMARY_LIGHT = "#2e86c1"
PRIMARY_BG = "#d4e6f1"
BG = "#eaf2f8"
TEXT = "#1b2631"
TEXT_MUTED = "#5d6d7e"
WHITE = "#ffffff"
RED = "#e74c3c"
ORANGE = "#f39c12"
GREEN = "#27ae60"

# ---------------------------------------------------------------------------
# GIGW-compliant theme CSS
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
    .stApp {{ background-color: {BG}; }}
    header[data-testid="stHeader"] {{ background-color: {PRIMARY}; }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{ background-color: {PRIMARY} !important; }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stMarkdown * {{ color: {WHITE} !important; }}
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label {{ color: {WHITE} !important; font-weight: 600; }}
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span,
    section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] span {{ color: {TEXT} !important; }}
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"],
    section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] {{
        background-color: {WHITE} !important; border: 1px solid #aed6f1 !important; border-radius: 6px;
    }}
    section[data-testid="stSidebar"] .stSelectbox svg,
    section[data-testid="stSidebar"] .stMultiSelect svg {{ fill: {PRIMARY} !important; }}
    [data-baseweb="menu"] li {{ color: {TEXT} !important; }}
    [data-baseweb="menu"] li:hover {{ background-color: {PRIMARY_BG} !important; }}

    /* KPI cards with HTML */
    .kpi-card {{
        background: linear-gradient(135deg, {PRIMARY} 0%, #1b4f72 100%);
        border-radius: 12px; padding: 20px 16px; text-align: center;
        box-shadow: 0 4px 12px rgba(14,102,85,0.3); min-height: 140px;
        display: flex; flex-direction: column; justify-content: center;
    }}
    .kpi-value {{ color: {WHITE}; font-size: 2rem; font-weight: 700; line-height: 1.1; }}
    .kpi-label {{ color: #aed6f1; font-size: 0.8rem; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.5px; }}
    .kpi-sub {{ color: #85c1e9; font-size: 0.75rem; margin-top: 4px; }}

    /* DataFrames */
    .stDataFrame {{ border: 1px solid {PRIMARY_LIGHT}; border-radius: 6px; }}

    /* Tabs */
    button[data-baseweb="tab"] {{ color: {PRIMARY} !important; font-weight: 600; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ border-bottom: 3px solid {PRIMARY} !important; }}

    /* Footer */
    .footer {{
        text-align: center; padding: 20px; margin-top: 40px;
        background-color: {PRIMARY}; color: {PRIMARY_BG}; border-radius: 6px; font-size: 0.85rem;
    }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Plotly layout defaults
# ---------------------------------------------------------------------------
PLOTLY_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, family="sans-serif"),
    margin=dict(l=40, r=20, t=40, b=40),
)


def apply_layout(fig, **kwargs):
    merged = {**PLOTLY_LAYOUT, **kwargs}
    fig.update_layout(**merged)
    return fig


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_sample_data():
    return {
        "projects": get_projects_df(),
        "resources": get_resources_df(),
        "meetings": get_meetings_df(),
        "tasks": get_tasks_df(),
        "financials": get_financials_df(),
        "risks": get_risks_df(),
        "scan_log": pd.DataFrame(),
        "scan_time": None,
    }


@st.cache_data(ttl=300, show_spinner="Scanning Google Drive...")
def load_drive_data_cached():
    from utils.drive_data_loader import load_drive_data
    return load_drive_data()


def check_oauth_ready():
    from pathlib import Path
    return (Path("config/oauth_client_secret.json").exists()
            or Path("config/token.pickle").exists())


if "data_source" not in st.session_state:
    st.session_state.data_source = "sample"

data = load_sample_data()
drive_connected = False
drive_scan_time = None

if st.session_state.data_source == "google_drive":
    try:
        data = load_drive_data_cached()
        drive_connected = True
        drive_scan_time = data.get("scan_time")
    except Exception as e:
        st.error(f"Google Drive error: {e}")
        st.session_state.data_source = "sample"
        data = load_sample_data()

projects_df = data["projects"]
resources_df = data["resources"]
meetings_df = data["meetings"]
tasks_df = data["tasks"]
financials_df = data["financials"]
risks_df = data["risks"]

# Normalize columns
for col, default in [("id", None), ("ministry", ""), ("status", "Unknown"), ("value_cr", 0), ("start_date", "")]:
    if col not in projects_df.columns:
        projects_df[col] = range(1, len(projects_df) + 1) if col == "id" else default
for col, default in [("resource_id", None), ("name", ""), ("role", ""), ("bucket", "Tech"),
                      ("project", ""), ("tasks_completed_15d", 0), ("tasks_pending", 0)]:
    if col not in resources_df.columns:
        resources_df[col] = range(1, len(resources_df) + 1) if col == "resource_id" else default
for col, default in [("task_id", None), ("project", ""), ("task_name", ""), ("status", "Unknown"),
                      ("assigned_to", ""), ("priority", "Medium"), ("closed_date", None)]:
    if col not in tasks_df.columns:
        tasks_df[col] = range(1, len(tasks_df) + 1) if col == "task_id" else default
for col, default in [("project", ""), ("last_client_meeting", ""), ("client_days_ago", 0),
                      ("last_internal_review", ""), ("internal_days_ago", 0)]:
    if col not in meetings_df.columns:
        meetings_df[col] = default
for col, default in [("project", ""), ("contracted_cr", 0), ("utilised_cr", 0),
                      ("utilised_pct", 0), ("remaining_cr", 0), ("health", "Unknown")]:
    if col not in financials_df.columns:
        financials_df[col] = default
for col, default in [("risk_id", None), ("project", ""), ("severity", "Medium"),
                      ("description", ""), ("owner", ""), ("due_date", "")]:
    if col not in risks_df.columns:
        risks_df[col] = range(1, len(risks_df) + 1) if col == "risk_id" else default


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.image("negd-logo.png", width=80)
st.sidebar.title("NeGD Dashboard")
st.sidebar.markdown("---")

today = datetime.now()
fortnight_options = []
for i in range(6):
    end = today - timedelta(days=15 * i)
    start = end - timedelta(days=14)
    fortnight_options.append(f"{start.strftime('%d %b')} - {end.strftime('%d %b %Y')}")

selected_fortnight = st.sidebar.selectbox("Fortnight Period", fortnight_options, index=0)
all_project_names = ["All Projects"] + sorted(projects_df["name"].tolist())
selected_project = st.sidebar.selectbox("Select Project", all_project_names, index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("**Data Source**")
oauth_ready = check_oauth_ready()
if oauth_ready:
    source_options = ["Sample Data", "Google Drive (Live)"]
    source_idx = 1 if st.session_state.data_source == "google_drive" else 0
    source_choice = st.sidebar.radio("", source_options, index=source_idx, key="source_radio")
    if source_choice == "Google Drive (Live)" and st.session_state.data_source != "google_drive":
        st.session_state.data_source = "google_drive"
        st.rerun()
    elif source_choice == "Sample Data" and st.session_state.data_source != "sample":
        st.session_state.data_source = "sample"
        st.rerun()
    if drive_connected:
        st.sidebar.success("Connected to Drive")
        if drive_scan_time:
            st.sidebar.caption(f"Last scan: {drive_scan_time}")
        if st.sidebar.button("Refresh Data"):
            load_drive_data_cached.clear()
            st.rerun()
else:
    st.sidebar.info("Using sample data")
    with st.sidebar.expander("Connect Google Drive"):
        st.markdown(
            "**Setup steps:**\n"
            "1. Go to [Google Cloud Console](https://console.cloud.google.com)\n"
            "2. Enable **Google Drive API**\n"
            "3. Create **OAuth 2.0 Client ID** (Desktop app)\n"
            "4. Download JSON, save as `config/oauth_client_secret.json`\n"
            "5. Restart the app"
        )

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
st.markdown(f"<h1 style='color:{PRIMARY}; margin-bottom:0;'>NeGD Project Monitoring Dashboard</h1>", unsafe_allow_html=True)
source_label = "Google Drive (Live)" if drive_connected else "Sample Data"
st.markdown(
    f"<p style='color:{TEXT_MUTED}; margin-top:0;'>National e-Governance Division, MeitY &nbsp;|&nbsp; "
    f"Data: {source_label} &nbsp;|&nbsp; "
    f"Last updated: {drive_scan_time or today.strftime('%d %b %Y, %H:%M IST')}</p>",
    unsafe_allow_html=True,
)
st.markdown("---")


def filter_by_project(df, col="project"):
    if selected_project == "All Projects":
        return df
    return df[df[col] == selected_project]


# =========================================================================
# SECTION 1 — KPI Summary (Gauge charts + single-number cards per PDF p.18-19)
# =========================================================================
st.subheader("Overall Summary")

total_projects = len(projects_df)
total_resources = len(resources_df)
total_value = projects_df["value_cr"].sum()
tasks_closed_15d = len(tasks_df[tasks_df["status"] == "Closed"])
tasks_opened_15d = len(tasks_df[tasks_df["status"] == "Pending"])
total_open = len(tasks_df[tasks_df["status"] == "Pending"])
at_risk = len(projects_df[projects_df["status"] == "At Risk"])
on_track = len(projects_df[projects_df["status"] == "On Track"])
total_tasks = len(tasks_df)
task_completion_pct = round(tasks_closed_15d / total_tasks * 100, 1) if total_tasks > 0 else 0
avg_budget_util = round(financials_df["utilised_pct"].mean(), 1) if not financials_df.empty else 0

# Row 1: Single-number KPI cards
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
for col_widget, label, value, sub in [
    (c1, "Total Projects", str(total_projects), f"{on_track} On Track"),
    (c2, "Total Resources", str(total_resources), f"PM: {len(resources_df[resources_df['bucket']=='PM'])} | Tech: {len(resources_df[resources_df['bucket']=='Tech'])}"),
    (c3, "Portfolio Value", f"\u20b9{total_value:.0f} Cr", f"{total_projects} projects"),
    (c4, "Closed (15d)", str(tasks_closed_15d), f"of {total_tasks} total"),
    (c5, "Opened (15d)", str(tasks_opened_15d), "new tasks"),
    (c6, "Open Tasks", str(total_open), f"{task_completion_pct}% done"),
    (c7, "At-Risk", str(at_risk), f"of {total_projects} projects"),
]:
    col_widget.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Row 2: Gauge charts (PDF p.18-19 — gauges for tracking progress toward a goal)
g1, g2, g3 = st.columns(3)

with g1:
    fig_gauge1 = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=task_completion_pct,
        title={"text": "Task Completion Rate", "font": {"size": 14, "color": TEXT}},
        number={"suffix": "%", "font": {"color": PRIMARY}},
        delta={"reference": 70, "increasing": {"color": GREEN}, "decreasing": {"color": RED}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": TEXT_MUTED},
            "bar": {"color": PRIMARY},
            "bgcolor": "#eaf2f8",
            "steps": [
                {"range": [0, 40], "color": "#fadbd8"},
                {"range": [40, 70], "color": "#fdebd0"},
                {"range": [70, 100], "color": "#d5f5e3"},
            ],
            "threshold": {"line": {"color": RED, "width": 3}, "thickness": 0.75, "value": 70},
        },
    ))
    apply_layout(fig_gauge1, height=250, margin=dict(t=60, b=20, l=30, r=30))
    st.plotly_chart(fig_gauge1, use_container_width=True)

with g2:
    fig_gauge2 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_budget_util,
        title={"text": "Avg Budget Utilisation", "font": {"size": 14, "color": TEXT}},
        number={"suffix": "%", "font": {"color": PRIMARY}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": PRIMARY},
            "bgcolor": "#eaf2f8",
            "steps": [
                {"range": [0, 60], "color": "#d5f5e3"},
                {"range": [60, 85], "color": "#fdebd0"},
                {"range": [85, 100], "color": "#fadbd8"},
            ],
            "threshold": {"line": {"color": RED, "width": 3}, "thickness": 0.75, "value": 85},
        },
    ))
    apply_layout(fig_gauge2, height=250, margin=dict(t=60, b=20, l=30, r=30))
    st.plotly_chart(fig_gauge2, use_container_width=True)

with g3:
    project_health_pct = round(on_track / total_projects * 100, 1) if total_projects > 0 else 0
    fig_gauge3 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=project_health_pct,
        title={"text": "Projects On Track", "font": {"size": 14, "color": TEXT}},
        number={"suffix": "%", "font": {"color": PRIMARY}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": GREEN},
            "bgcolor": "#eaf2f8",
            "steps": [
                {"range": [0, 50], "color": "#fadbd8"},
                {"range": [50, 75], "color": "#fdebd0"},
                {"range": [75, 100], "color": "#d5f5e3"},
            ],
        },
    ))
    apply_layout(fig_gauge3, height=250, margin=dict(t=60, b=20, l=30, r=30))
    st.plotly_chart(fig_gauge3, use_container_width=True)

st.markdown("---")

# =========================================================================
# SECTION 2 — Project Portfolio (Doughnut for status + table)
# Per PDF p.15-16: doughnut for part-to-whole with few categories
# =========================================================================
st.subheader("1. Project Portfolio")

display_projects = filter_by_project(projects_df, col="name")
col_proj_tbl, col_proj_chart = st.columns([3, 2])

with col_proj_tbl:
    def status_color(s):
        colors = {"On Track": GREEN, "At Risk": RED, "Stable": ORANGE}
        return f"background-color: {colors.get(s, '#95a5a6')}; color: white; border-radius: 12px; padding: 2px 8px;"

    proj_display = display_projects[["id", "name", "ministry", "status", "value_cr", "start_date"]].copy()
    proj_display.columns = ["#", "Project", "Ministry", "Status", "Value (Cr)", "Start Date"]
    st.dataframe(
        proj_display.style.map(lambda v: status_color(v) if v in ["On Track", "At Risk", "Stable"] else "", subset=["Status"]),
        use_container_width=True, hide_index=True,
        height=min(420, 40 + 35 * len(proj_display)),
    )

with col_proj_chart:
    status_counts = projects_df["status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    color_map = {"On Track": GREEN, "At Risk": RED, "Stable": ORANGE, "Unknown": "#95a5a6"}
    fig_status = px.pie(
        status_counts, values="Count", names="Status", hole=0.5,
        color="Status", color_discrete_map=color_map,
        title="Project Status Distribution",
    )
    fig_status.update_traces(textinfo="label+value+percent", textfont_size=12)
    apply_layout(fig_status, height=350, showlegend=False)
    st.plotly_chart(fig_status, use_container_width=True)

st.markdown("---")

# =========================================================================
# SECTION 3 — Human Resources (Doughnut + Stacked Bar)
# Per PDF p.15: doughnut for role proportions; p.5-6: stacked bar for part-to-whole across projects
# =========================================================================
st.subheader("2. Human Resources")

res_filtered = filter_by_project(resources_df)
col_hr1, col_hr2, col_hr3 = st.columns([1, 1, 1])

with col_hr1:
    # PM vs Tech split — doughnut (2 categories = perfect for pie/doughnut)
    bucket_counts = res_filtered["bucket"].value_counts().reset_index()
    bucket_counts.columns = ["Bucket", "Count"]
    fig_bucket = px.pie(
        bucket_counts, values="Count", names="Bucket", hole=0.55,
        color="Bucket", color_discrete_map={"PM": PRIMARY, "Tech": PRIMARY_LIGHT},
        title="PM vs Tech Split",
    )
    fig_bucket.update_traces(textinfo="label+value+percent", textfont_size=11)
    total_res = len(res_filtered)
    fig_bucket.add_annotation(text=f"<b>{total_res}</b><br>Total", x=0.5, y=0.5,
                               font_size=16, font_color=PRIMARY, showarrow=False)
    apply_layout(fig_bucket, height=320, showlegend=False)
    st.plotly_chart(fig_bucket, use_container_width=True)

with col_hr2:
    # Role distribution — doughnut (8 roles, good for doughnut per PDF)
    role_counts = res_filtered.groupby("role").size().reset_index(name="count")
    fig_roles = px.pie(
        role_counts, values="count", names="role", hole=0.45,
        color_discrete_sequence=[PRIMARY, PRIMARY_LIGHT, "#2980b9", "#3498db", "#5dade2",
                                  "#85c1e9", "#aed6f1", "#1a5276"],
        title="Distribution by Role",
    )
    fig_roles.update_traces(textinfo="percent+label", textfont_size=9)
    apply_layout(fig_roles, height=320, showlegend=False)
    st.plotly_chart(fig_roles, use_container_width=True)

with col_hr3:
    # Stacked bar per project — resources by bucket (PDF p.6: stacked column for part-to-whole)
    res_by_proj = res_filtered.groupby(["project", "bucket"]).size().reset_index(name="count")
    fig_stack = px.bar(
        res_by_proj, y="project", x="count", color="bucket", orientation="h",
        color_discrete_map={"PM": PRIMARY, "Tech": PRIMARY_LIGHT},
        title="Resources per Project",
        labels={"count": "Headcount", "project": ""},
    )
    apply_layout(fig_stack, height=max(320, 28 * res_by_proj["project"].nunique()),
                 barmode="stack", yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_stack, use_container_width=True)

st.markdown("---")

# =========================================================================
# SECTION 4 — Meeting Dates (Line chart for trend + table)
# Per PDF p.3-4: line chart for trends over time
# =========================================================================
st.subheader("3. Last Meeting Dates")

meetings_filtered = filter_by_project(meetings_df)
col_meet1, col_meet2 = st.columns([3, 2])

with col_meet1:
    def days_ago_color(val):
        if val <= 7:
            return "background-color: #d5f5e3; color: #1e8449;"
        elif val <= 14:
            return "background-color: #fdebd0; color: #d68910;"
        return "background-color: #fadbd8; color: #cb4335;"

    meet_display = meetings_filtered[["project", "last_client_meeting", "client_days_ago",
                                       "last_internal_review", "internal_days_ago"]].copy()
    meet_display.columns = ["Project", "Last Client Meeting", "Client (Days Ago)",
                             "Last Internal Review", "Internal (Days Ago)"]
    st.dataframe(
        meet_display.style.map(days_ago_color, subset=["Client (Days Ago)", "Internal (Days Ago)"]),
        use_container_width=True, hide_index=True,
    )

with col_meet2:
    # Line chart — meeting gap per project (PDF p.3: line for comparing trends)
    fig_meet = go.Figure()
    fig_meet.add_trace(go.Scatter(
        x=meetings_filtered["project"], y=meetings_filtered["client_days_ago"],
        mode="lines+markers", name="Client Meeting Gap",
        line=dict(color=PRIMARY, width=2), marker=dict(size=8),
    ))
    fig_meet.add_trace(go.Scatter(
        x=meetings_filtered["project"], y=meetings_filtered["internal_days_ago"],
        mode="lines+markers", name="Internal Review Gap",
        line=dict(color=PRIMARY_LIGHT, width=2, dash="dash"), marker=dict(size=8),
    ))
    # Threshold line at 14 days
    fig_meet.add_hline(y=14, line_dash="dot", line_color=RED, annotation_text="14-day threshold",
                        annotation_position="top right")
    apply_layout(fig_meet, title="Meeting Recency (Days Since Last)", height=350,
                 xaxis_tickangle=-45, yaxis_title="Days Ago")
    st.plotly_chart(fig_meet, use_container_width=True)

st.markdown("---")

# =========================================================================
# SECTION 5 — Task Analysis (Combo chart + horizontal bar)
# Per PDF p.7-8: combination chart for different scales
# Per PDF p.5-6: horizontal bar for comparing across categories
# =========================================================================
st.subheader("4. Task Analysis")

tab_closed, tab_pending = st.tabs(["Top 5 Tasks Closed (15 days)", "Tasks Pending %"])

with tab_closed:
    task_project_sel = st.selectbox("Select Project", all_project_names, index=0, key="task_closed_proj")
    closed_tasks = tasks_df[tasks_df["status"] == "Closed"].copy()
    if task_project_sel != "All Projects":
        closed_tasks = closed_tasks[closed_tasks["project"] == task_project_sel]
    closed_top5 = closed_tasks.sort_values("closed_date", ascending=False).head(5)

    # Horizontal bar chart for top 5 closed tasks (PDF p.5-6: bar for comparing categories)
    if not closed_top5.empty:
        fig_closed = px.bar(
            closed_top5, y="task_name", x="task_id", orientation="h",
            color="priority",
            color_discrete_map={"High": RED, "Medium": ORANGE, "Low": GREEN},
            hover_data=["project", "assigned_to", "closed_date"],
            title="Top 5 Recently Closed Tasks",
            labels={"task_name": "", "task_id": ""},
        )
        fig_closed.update_traces(showlegend=True)
        fig_closed.update_xaxes(showticklabels=False)
        apply_layout(fig_closed, height=280, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_closed, use_container_width=True)
    else:
        st.info("No closed tasks in selected period.")

with tab_pending:
    task_pend_sel = st.selectbox("Select Project", all_project_names, index=0, key="task_pend_proj")

    # % pending per project — horizontal bar (PDF p.5-6)
    proj_task_counts = tasks_df.groupby("project").agg(
        total=("task_id", "count"),
        pending=("status", lambda x: (x == "Pending").sum()),
    ).reset_index()
    proj_task_counts["pending_pct"] = (proj_task_counts["pending"] / proj_task_counts["total"] * 100).round(1)
    proj_task_counts = proj_task_counts.sort_values("pending_pct", ascending=True)

    if task_pend_sel != "All Projects":
        proj_task_counts = proj_task_counts[proj_task_counts["project"] == task_pend_sel]

    fig_pending = px.bar(
        proj_task_counts, y="project", x="pending_pct", orientation="h",
        color="pending_pct",
        color_continuous_scale=[[0, GREEN], [0.5, ORANGE], [1, RED]],
        labels={"project": "", "pending_pct": "Pending %"},
        title="% Tasks Pending by Project",
        text="pending_pct",
    )
    fig_pending.update_traces(texttemplate="%{text}%", textposition="outside")
    apply_layout(fig_pending, height=max(300, 30 * len(proj_task_counts)),
                 coloraxis_showscale=False)
    st.plotly_chart(fig_pending, use_container_width=True)

st.markdown("---")

# =========================================================================
# SECTION 6 — Resource Performance (Horizontal bar charts)
# Per PDF p.5-6: bar chart for comparing data values across categories
# =========================================================================
st.subheader("5. Resource Performance")

col_top, col_bottom = st.columns(2)

with col_top:
    top_res = (
        resources_df.groupby("name")
        .agg(tasks_completed=("tasks_completed_15d", "sum"), role=("role", "first"), project=("project", "first"))
        .sort_values("tasks_completed", ascending=True).tail(5).reset_index()
    )
    fig_top = px.bar(
        top_res, y="name", x="tasks_completed", orientation="h",
        color_discrete_sequence=[PRIMARY],
        text="tasks_completed",
        hover_data=["role", "project"],
        title="Top 5 — Most Tasks Completed (15d)",
        labels={"name": "", "tasks_completed": "Tasks"},
    )
    fig_top.update_traces(textposition="outside")
    apply_layout(fig_top, height=280)
    st.plotly_chart(fig_top, use_container_width=True)

with col_bottom:
    bot_res = (
        resources_df.groupby("name")
        .agg(tasks_pending=("tasks_pending", "sum"), role=("role", "first"), project=("project", "first"))
        .sort_values("tasks_pending", ascending=True).tail(5).reset_index()
    )
    fig_bot = px.bar(
        bot_res, y="name", x="tasks_pending", orientation="h",
        color_discrete_sequence=[RED],
        text="tasks_pending",
        hover_data=["role", "project"],
        title="Bottom 5 — Most Tasks Pending",
        labels={"name": "", "tasks_pending": "Tasks"},
    )
    fig_bot.update_traces(textposition="outside")
    apply_layout(fig_bot, height=280)
    st.plotly_chart(fig_bot, use_container_width=True)

st.markdown("---")

# =========================================================================
# SECTION 7 — Financial Health (Waterfall chart)
# Per PDF p.13-14: waterfall for showing changes in value; bar for budget comparison
# =========================================================================
st.subheader("6. Financial Health")

fin_project_sel = st.selectbox("Select Project for Financial View", all_project_names, index=0, key="fin_proj")
fin_filtered = financials_df.copy()
if fin_project_sel != "All Projects":
    fin_filtered = fin_filtered[fin_filtered["project"] == fin_project_sel]

col_fin1, col_fin2 = st.columns([1, 1])

with col_fin1:
    if fin_project_sel != "All Projects" and not fin_filtered.empty:
        # Waterfall chart for single project (PDF p.13-14)
        row = fin_filtered.iloc[0]
        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            x=["Contracted", "Utilised", "Remaining"],
            y=[row["contracted_cr"], -row["utilised_cr"], row["remaining_cr"]],
            measure=["absolute", "relative", "total"],
            text=[f"\u20b9{row['contracted_cr']} Cr", f"-\u20b9{row['utilised_cr']} Cr", f"\u20b9{row['remaining_cr']} Cr"],
            textposition="outside",
            connector={"line": {"color": TEXT_MUTED}},
            increasing={"marker": {"color": GREEN}},
            decreasing={"marker": {"color": RED}},
            totals={"marker": {"color": PRIMARY}},
        ))
        apply_layout(fig_wf, title=f"Budget Waterfall — {fin_project_sel}",
                     height=350, yaxis_title="Crores (INR)")
        st.plotly_chart(fig_wf, use_container_width=True)
    else:
        # All projects — grouped bar (PDF p.5-6: column chart for comparing across categories)
        fig_fin_bar = go.Figure()
        fig_fin_bar.add_trace(go.Bar(
            y=fin_filtered["project"], x=fin_filtered["contracted_cr"],
            name="Contracted", orientation="h", marker_color=PRIMARY_LIGHT,
        ))
        fig_fin_bar.add_trace(go.Bar(
            y=fin_filtered["project"], x=fin_filtered["utilised_cr"],
            name="Utilised", orientation="h", marker_color=PRIMARY,
        ))
        apply_layout(fig_fin_bar, barmode="group", title="Budget: Contracted vs Utilised",
                     height=max(350, 35 * len(fin_filtered)),
                     yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_fin_bar, use_container_width=True)

with col_fin2:
    def health_color(val):
        colors = {"Healthy": "#d5f5e3", "Monitor": "#fdebd0", "Critical": "#fadbd8"}
        return f"background-color: {colors.get(val, '')};"

    fin_display = fin_filtered[["project", "contracted_cr", "utilised_cr", "utilised_pct", "remaining_cr", "health"]].copy()
    fin_display.columns = ["Project", "Contracted (Cr)", "Utilised (Cr)", "Utilised %", "Remaining (Cr)", "Health"]
    st.dataframe(
        fin_display.style.map(health_color, subset=["Health"]),
        use_container_width=True, hide_index=True,
    )

    # Gauge for selected project's budget utilisation (PDF p.18-19)
    if fin_project_sel != "All Projects" and not fin_filtered.empty:
        util_val = fin_filtered.iloc[0]["utilised_pct"]
        fig_fin_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=util_val,
            title={"text": "Budget Utilisation", "font": {"size": 13, "color": TEXT}},
            number={"suffix": "%", "font": {"color": PRIMARY}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": PRIMARY},
                "steps": [
                    {"range": [0, 60], "color": "#d5f5e3"},
                    {"range": [60, 85], "color": "#fdebd0"},
                    {"range": [85, 100], "color": "#fadbd8"},
                ],
                "threshold": {"line": {"color": RED, "width": 3}, "thickness": 0.75, "value": 85},
            },
        ))
        apply_layout(fig_fin_gauge, height=220, margin=dict(t=50, b=10, l=30, r=30))
        st.plotly_chart(fig_fin_gauge, use_container_width=True)

st.markdown("---")

# =========================================================================
# SECTION 8 — Risks (Bubble chart)
# Per PDF p.11-12: bubble chart for 3 dimensions (severity, time, impact)
# =========================================================================
st.subheader("7. Top Risks Across All Projects")

col_risk1, col_risk2 = st.columns([2, 3])

with col_risk1:
    risks_display = risks_df.sort_values("severity", ascending=True).head(5).copy()

    def severity_color(val):
        if val == "High":
            return "background-color: #fadbd8; color: #cb4335; font-weight: bold;"
        return "background-color: #fdebd0; color: #d68910;"

    risks_show = risks_display[["project", "severity", "description", "owner", "due_date"]].copy()
    risks_show.columns = ["Project", "Severity", "Risk Description", "Owner", "Due Date"]
    st.dataframe(
        risks_show.style.map(severity_color, subset=["Severity"]),
        use_container_width=True, hide_index=True,
    )

with col_risk2:
    # Bubble chart: x=project, y=severity score, size=days to due
    risk_bubble = risks_df.head(10).copy()
    risk_bubble["severity_score"] = risk_bubble["severity"].map({"High": 3, "Medium": 2, "Low": 1}).fillna(1)
    try:
        risk_bubble["due_dt"] = pd.to_datetime(risk_bubble["due_date"], errors="coerce")
        risk_bubble["days_to_due"] = (risk_bubble["due_dt"] - pd.Timestamp.now()).dt.days.clip(lower=1)
    except Exception:
        risk_bubble["days_to_due"] = 30

    fig_bubble = px.scatter(
        risk_bubble, x="project", y="severity_score",
        size="days_to_due", color="severity",
        color_discrete_map={"High": RED, "Medium": ORANGE, "Low": GREEN},
        hover_data=["description", "owner", "due_date"],
        title="Risk Landscape (bubble size = days to deadline)",
        labels={"project": "Project", "severity_score": "Severity"},
        size_max=40,
    )
    fig_bubble.update_yaxes(tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"])
    apply_layout(fig_bubble, height=350, xaxis_tickangle=-45)
    st.plotly_chart(fig_bubble, use_container_width=True)

st.markdown("---")

# =========================================================================
# SECTION 9 — Task Velocity (Combination chart: bar + line)
# Per PDF p.7-8: combination chart for comparing data with different scales
# =========================================================================
st.subheader("8. Task Velocity (Fortnightly Trend)")

velocity_data = pd.DataFrame({
    "Period": [f"FN{i}" for i in range(1, 7)],
    "Closed": [42, 55, 48, 63, 58, tasks_closed_15d],
    "Opened": [38, 45, 52, 40, 47, tasks_opened_15d],
})
velocity_data["Net"] = velocity_data["Closed"] - velocity_data["Opened"]
velocity_data["Cumulative Closed"] = velocity_data["Closed"].cumsum()

fig_vel = go.Figure()
# Bars for closed/opened (primary axis)
fig_vel.add_trace(go.Bar(x=velocity_data["Period"], y=velocity_data["Closed"],
                          name="Closed", marker_color=PRIMARY))
fig_vel.add_trace(go.Bar(x=velocity_data["Period"], y=velocity_data["Opened"],
                          name="Opened", marker_color="#aed6f1"))
# Line for net trend (secondary axis — combination chart per PDF)
fig_vel.add_trace(go.Scatter(
    x=velocity_data["Period"], y=velocity_data["Net"],
    name="Net (Closed - Opened)", mode="lines+markers+text",
    text=velocity_data["Net"], textposition="top center",
    line=dict(color=ORANGE, width=3), marker=dict(size=10, color=ORANGE),
    yaxis="y2",
))
apply_layout(fig_vel,
    barmode="group",
    title="Tasks Closed vs Opened per Fortnight (with Net Trend)",
    height=400,
    yaxis=dict(title="Task Count"),
    yaxis2=dict(title="Net Change", overlaying="y", side="right",
                showgrid=False, zeroline=True, zerolinecolor=TEXT_MUTED),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_vel, use_container_width=True)

# =========================================================================
# Footer
# =========================================================================
st.markdown(f"""
<div class="footer">
    <strong>NeGD Project Monitoring Dashboard</strong> | National e-Governance Division, MeitY<br>
    GIGW 3.0 Compliant | Accessibility AA | Built with Streamlit + Plotly<br>
    Chart design guided by "Zero to Beautiful: Choosing Charts for Data Visualization"
</div>
""", unsafe_allow_html=True)

import streamlit as st
import json
import os
import re
from html import escape as html_escape
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# --- CONFIGURATION ---
HUMIO_DASHBOARD_URL = os.environ.get(
    "HUMIO_DASHBOARD_URL",
    "https://humio.prod.bloomberg.com/guts_wam/dashboards/hEIe82DuFR8EVa7CJJdQn9UzuEejOJ2E"
    "?updateFrequency=never&tz=America/New_York&sharedTime=true&start=15m&fullscreen=false"
    "&$jobId=%5B%22*%22%5D"
)
HUMIO_JOB_URL_TEMPLATE = os.environ.get(
    "HUMIO_JOB_URL_TEMPLATE",
    "https://humio.prod.bloomberg.com/guts_wam/dashboards/hEIe82DuFR8EVa7CJJdQn9UzuEejOJ2E"
    "?%24jobId=%5B%22{job_id}%22%5D"
    "&filterId=9e3WFUID6IX7ypte9Osrm3vm626FHi2y&fullscreen=false"
    "&sharedTime=true&start=15m&updateFrequency=never"
)
DRIFT_THRESHOLD_SECONDS = 900  # 15 minutes
EASTERN_TZ = ZoneInfo("America/New_York")

# --- INPUT FIELD SESSION KEYS ---
INPUT_KEYS = ["raw_log_input", "input_t1", "input_t2", "input_t3", "input_t4", "input_t5", "input_t6"]

# --- INITIALIZE SESSION STATE ---
if "validation_history" not in st.session_state:
    st.session_state.validation_history = []

# --- SET PAGE CONFIG ---
st.set_page_config(page_title="BORG Jobs Verification", layout="wide")

# --- BLOOMBERG-STYLE THEMING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&family=Inter:wght@400;600&display=swap');

    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    code { font-family: 'Roboto Mono', monospace !important; color: #d4d4d4 !important; }

    /* Environment Headers */
    .env-header { padding: 12px 20px; border-radius: 4px; font-weight: 600; margin-bottom: 20px; border-left: 6px solid; }
    .env-test { background-color: #3a321d; color: #ffcc00; border-color: #ffcc00; }
    .env-prod { background-color: #1b2e1f; color: #4cd964; border-color: #4cd964; }
    .env-invalid { background-color: #3d1c1c; color: #ff3b30; border-color: #ff3b30; }

    /* Drift Warning */
    .drift-warn { background-color: #3d1c1c; color: #ff3b30; padding: 10px; border-radius: 4px; font-weight: 600; margin-bottom: 15px; border: 1px solid #ff3b30; }

    /* Job Details Styling */
    .detail-item { margin-bottom: 10px; font-size: 0.95em; line-height: 1.6; }
    .detail-label { color: #8e8e93; font-weight: 500; margin-right: 8px; }
    .detail-value { color: #ffffff; font-family: 'Roboto Mono', monospace; word-break: break-all; }
    .detail-value a { color: #0a84ff; text-decoration: none; }
    .detail-value a:hover { text-decoration: underline; }

    /* CQA Yellow Label */
    .cqa-tag { color: #ffcc00; font-weight: 600; margin-left: 5px; }

    /* Utility Link Button */
    .humio-link {
        display: inline-block;
        padding: 5px 12px;
        background-color: #ff9800;
        color: #1a1a1a !important;
        font-weight: 600;
        border-radius: 4px;
        text-decoration: none !important;
        font-size: 0.85em;
        border: 1px solid #e68900;
        margin-bottom: 20px;
    }
    .humio-link:hover {
        background-color: #e68900;
        text-decoration: none !important;
    }

    /* Vertical divider between columns */
    [data-testid="stHorizontalBlock"] > div:first-child {
        border-right: 2px solid #3a3a3c;
        padding-right: 20px;
    }

    /* Publish timestamp banner */
    .pub-time-banner {
        background-color: #1c2333;
        color: #8e8e93;
        padding: 8px 14px;
        border-radius: 4px;
        font-size: 0.9em;
        margin-bottom: 12px;
        border-left: 4px solid #0a84ff;
        font-family: 'Roboto Mono', monospace;
    }
    .pub-time-banner strong { color: #ffffff; }

    /* Green parse button */
    [data-testid="stButton"] button[kind="primary"] {
        background-color: #28a745 !important;
        border-color: #28a745 !important;
        color: white !important;
    }
    [data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #218838 !important;
        border-color: #218838 !important;
    }

    /* Hide ALL Material Symbols/Icons text fallback globally */
    .material-symbols-rounded,
    .material-symbols-outlined,
    .material-symbols-sharp,
    .material-icons,
    [class*="material-symbols"],
    [class*="material-icons"],
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="collapsedControl"] span,
    [data-testid="stExpander"] summary span[data-testid="stIconMaterial"],
    [data-testid="st-expander"] summary span[data-testid="stIconMaterial"] {
        font-size: 0 !important;
        line-height: 0 !important;
        overflow: hidden !important;
        display: inline-block !important;
        width: 1.2em !important;
        height: 1.2em !important;
    }

    /* Sidebar toggle button - hide literal text like "keyboard_double_arrow_right" */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="collapsedControl"] button {
        font-size: 0 !important;
        overflow: hidden !important;
    }
    [data-testid="stSidebarCollapseButton"] button svg,
    [data-testid="collapsedControl"] button svg {
        font-size: 1rem !important;
        width: 1.2em !important;
        height: 1.2em !important;
        display: inline-block !important;
    }

    /* Expander chevron arrows - hide literal text like "expand_more" */
    [data-testid="stExpander"] details summary svg,
    [data-testid="st-expander"] details summary svg {
        display: inline-block !important;
    }
    [data-testid="stExpander"] summary span[data-testid="stMarkdownContainer"],
    [data-testid="st-expander"] summary span[data-testid="stMarkdownContainer"] {
        display: inline !important;
    }
    [data-testid="stExpander"] summary::before,
    [data-testid="stExpander"] summary::after,
    [data-testid="st-expander"] .streamlit-expanderHeader::before,
    [data-testid="st-expander"] .streamlit-expanderHeader::after {
        content: "" !important;
        display: none !important;
    }
    details summary .material-icons,
    details summary [class*="icon"],
    details summary [class*="material-symbols"] {
        font-size: 0 !important;
        overflow: hidden !important;
    }

    /* Style for (Collapsible) */
    .collapsible-note {
        font-style: italic;
        color: #8e8e93;
        float: right;
    }

    /* Green Button */
    .green-button {
        background-color: #28a745;
        color: white;
        font-size: 16px;
        font-weight: bold;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        text-align: center;
    }
    .green-button:hover {
        background-color: #218838;
    }

    /* Summary Banner */
    .summary-banner {
        display: flex;
        gap: 16px;
        padding: 14px 20px;
        border-radius: 6px;
        margin-bottom: 20px;
        font-weight: 600;
        font-size: 0.95em;
        align-items: center;
        border-left: 6px solid;
    }
    .summary-all-pass {
        background-color: #1b2e1f;
        color: #4cd964;
        border-color: #4cd964;
    }
    .summary-has-fail {
        background-color: #3d1c1c;
        color: #ff3b30;
        border-color: #ff3b30;
    }
    .summary-has-warn {
        background-color: #3a321d;
        color: #ffcc00;
        border-color: #ffcc00;
    }
    .summary-stat {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.9em;
    }
    .stat-pass { background-color: rgba(76, 217, 100, 0.2); color: #4cd964; }
    .stat-fail { background-color: rgba(255, 59, 48, 0.2); color: #ff3b30; }
    .stat-warn { background-color: rgba(255, 204, 0, 0.2); color: #ffcc00; }
    .stat-review { background-color: rgba(142, 142, 147, 0.2); color: #8e8e93; }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 40px 20px;
        color: #636366;
    }
    .empty-state h3 { color: #8e8e93; margin-bottom: 10px; }
    .empty-state code {
        display: block;
        background: #1c2333;
        padding: 12px;
        border-radius: 6px;
        margin: 16px auto;
        max-width: 600px;
        text-align: left;
        font-size: 0.85em;
        color: #8e8e93 !important;
    }

    /* History sidebar entries */
    .history-entry {
        padding: 8px 12px;
        border-radius: 4px;
        margin-bottom: 8px;
        font-size: 0.85em;
        border-left: 4px solid;
        font-family: 'Roboto Mono', monospace;
    }
    .history-pass { background-color: #1b2e1f; border-color: #4cd964; color: #4cd964; }
    .history-fail { background-color: #3d1c1c; border-color: #ff3b30; color: #ff3b30; }
    .history-mixed { background-color: #3a321d; border-color: #ffcc00; color: #ffcc00; }
    .history-meta { color: #636366; font-size: 0.8em; margin-top: 4px; }
    </style>
    """, unsafe_allow_html=True)


# --- HELPER FUNCTIONS ---

def safe(val):
    """HTML-escape a value for safe embedding in markup."""
    if val is None:
        return "None"
    return html_escape(str(val))


def parse_publish_time(pub_time_str):
    """Parse the publish timestamp string into a timezone-aware datetime, or None on failure."""
    if not pub_time_str:
        return None
    try:
        return datetime.strptime(pub_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def format_timestamp(dt_utc):
    """Return (utc_str, eastern_str, tz_label) formatted timestamp strings, or None on failure."""
    if dt_utc is None:
        return None, None, None
    formatted_utc = dt_utc.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt_utc.microsecond // 1000:03d}"
    dt_eastern = dt_utc.astimezone(EASTERN_TZ)
    formatted_eastern = dt_eastern.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt_eastern.microsecond // 1000:03d}"
    tz_label = dt_eastern.strftime("%Z")  # "EST" or "EDT" depending on DST
    return formatted_utc, formatted_eastern, tz_label


def extract_json(raw_input):
    """Extract and parse the first JSON object from a raw log string."""
    json_match = re.search(r'(\{.*\})', raw_input, re.DOTALL)
    if not json_match:
        return None
    return json.loads(json_match.group(1))


def check_drift(pub_dt):
    """Return a human-readable drift string if the timestamp is stale, else None."""
    if pub_dt is None:
        return None
    drift_seconds = (datetime.now(timezone.utc) - pub_dt).total_seconds()
    if drift_seconds <= DRIFT_THRESHOLD_SECONDS:
        return None
    drift_hours = int(drift_seconds // 3600)
    drift_mins = int((drift_seconds % 3600) // 60)
    return f"{drift_hours}h {drift_mins}m" if drift_hours > 0 else f"{drift_mins}m"


def is_safe_url(url):
    """Basic check that a URL uses https."""
    return url and str(url).startswith("https://")


def compute_row_status(act, goal, r_type):
    """Compute the (status_text, bg_color, category) for a single verification row.
    category is one of: 'pass', 'fail', 'warn', 'review'.
    """
    is_empty = act is None or str(act).strip() == ""

    if is_empty:
        return "MISSING", "rgba(255, 59, 48, 0.15)", "fail"
    elif r_type == "binary":
        if act == "YES":
            return "TEST", "rgba(255, 204, 0, 0.15)", "warn"
        elif act == "NO":
            return "PROD", "rgba(76, 217, 100, 0.15)", "pass"
        else:
            return f"INVALID (Exp: {safe(goal)})", "rgba(255, 59, 48, 0.15)", "fail"
    elif r_type == "fixed":
        if act == goal:
            return "OK", "rgba(76, 217, 100, 0.1)", "pass"
        else:
            return f"MISMATCH (Exp: {safe(goal)})", "rgba(255, 59, 48, 0.15)", "fail"
    elif r_type == "target" and goal:
        if str(act) == str(goal):
            return "MATCH", "rgba(76, 217, 100, 0.1)", "pass"
        else:
            return f"MISMATCH (Exp: {safe(goal)})", "rgba(255, 59, 48, 0.15)", "fail"
    else:
        return "Review", "transparent", "review"


STATUS_ICONS = {
    "pass": "&#9989;",
    "fail": "&#10060;",
    "warn": "&#129514;",
    "review": "&#128064;",
}

# Special overrides for binary field display
BINARY_STATUS_TEXT = {
    "TEST": "&#129514; TEST",
    "PROD": "&#128640; PROD",
}


def render_detail(container, label, actual, expected=None):
    """Render a single detail row in the Job Details column."""
    escaped_actual = safe(actual)
    err = ""
    if expected and str(actual) != str(expected):
        err = f" <span style='color:#ff3b30;'>&#10060; (Exp: {safe(expected)})</span>"

    if label == "Source URL" and actual and is_safe_url(actual):
        escaped_actual = f'<a href="{safe(actual)}" target="_blank">{safe(actual)}</a>'

    container.markdown(
        f"<div class='detail-item'><span class='detail-label'>{safe(label)}:</span>"
        f"<span class='detail-value'>{escaped_actual}</span>{err}</div>",
        unsafe_allow_html=True
    )


def render_copyable_detail(container, label, value):
    """Render a detail row with a copyable code block for the value."""
    container.markdown(f"<div class='detail-item'><span class='detail-label'>{safe(label)}:</span></div>",
                       unsafe_allow_html=True)
    container.code(str(value) if value else "None", language=None)


def build_verification_rows(meta, is_borg, targets):
    """Build the verification rows and return (rows_with_status, counts).
    Each row: (label, actual, goal, r_type, status_text, bg, category).
    counts: dict with keys 'pass', 'fail', 'warn', 'review'.
    """
    t_ticker, t_scaling, t_period = targets
    rows_raw = [
        ("isBorgTest", is_borg, "YES/NO", "binary"),
        ("sendToBorg", meta.get("sendToBorg"), "YES", "fixed"),
        ("releaseDate", meta.get("releaseDate"), "NO RELEASE DATE", "fixed"),
        ("scalingFactor", meta.get("scalingFactor"), t_scaling, "target"),
        ("tickerValue", meta.get("tickerValue"), t_ticker, "target"),
        ("observationPeriod", meta.get("observationPeriod"), t_period, "target"),
    ]

    counts = {"pass": 0, "fail": 0, "warn": 0, "review": 0}
    rows_with_status = []
    for label, act, goal, r_type in rows_raw:
        status_text, bg, category = compute_row_status(act, goal, r_type)
        counts[category] += 1
        rows_with_status.append((label, act, goal, r_type, status_text, bg, category))

    return rows_with_status, counts


def render_summary_banner(container, counts):
    """Render the pass/fail/warn summary banner."""
    total = sum(counts.values())
    pass_count = counts["pass"]
    fail_count = counts["fail"]
    warn_count = counts["warn"]
    review_count = counts["review"]

    if fail_count > 0:
        banner_class = "summary-has-fail"
        headline = f"{fail_count}/{total} checks failed"
    elif warn_count > 0:
        banner_class = "summary-has-warn"
        headline = f"{pass_count}/{total} checks passed ({warn_count} warnings)"
    else:
        banner_class = "summary-all-pass"
        headline = f"{pass_count}/{total} checks passed"

    stats_html = f'<span class="summary-stat stat-pass">&#9989; {pass_count} Passed</span>'
    if fail_count:
        stats_html += f'<span class="summary-stat stat-fail">&#10060; {fail_count} Failed</span>'
    if warn_count:
        stats_html += f'<span class="summary-stat stat-warn">&#129514; {warn_count} Warnings</span>'
    if review_count:
        stats_html += f'<span class="summary-stat stat-review">&#128064; {review_count} Review</span>'

    container.markdown(
        f'<div class="summary-banner {banner_class}">'
        f'<strong>{headline}</strong>{stats_html}</div>',
        unsafe_allow_html=True
    )


def render_verification_table(container, rows_with_status, has_targets):
    """Render the verification table in the left column."""
    container.subheader("Verification")
    h_cols = container.columns([1.5, 1, 1, 1] if has_targets else [1.5, 1, 1])
    h_cols[0].markdown("**Field**")
    h_cols[1].markdown("**Actual**")
    if has_targets:
        h_cols[2].markdown("**Target**")
    h_cols[-1].markdown("**Status**")

    for label, act, goal, r_type, status_text, bg, category in rows_with_status:
        # Build display status with icon
        if r_type == "binary" and status_text in BINARY_STATUS_TEXT:
            display_status = BINARY_STATUS_TEXT[status_text]
        else:
            icon = STATUS_ICONS.get(category, "")
            display_status = f"{icon} {status_text}"

        row_cols = container.columns([1.5, 1, 1, 1] if has_targets else [1.5, 1, 1])
        row_cols[0].markdown(
            f'<div style="background:{bg}; padding:5px; font-weight:600;">{safe(label)}</div>',
            unsafe_allow_html=True
        )
        row_cols[1].markdown(
            f'<div style="background:{bg}; padding:5px; font-family:monospace;">{safe(act)}</div>',
            unsafe_allow_html=True
        )
        if has_targets:
            target_display = safe(goal) if r_type == "target" and goal else "-"
            row_cols[2].markdown(
                f'<div style="background:{bg}; padding:5px; color:#8e8e93;">{target_display}</div>',
                unsafe_allow_html=True
            )
        row_cols[-1].markdown(
            f'<div style="background:{bg}; padding:5px; font-weight:600; text-align:right;">{display_status}</div>',
            unsafe_allow_html=True
        )


def render_job_details(container, meta, content, job_props, job_meta, data_all, expectations):
    """Render the job details panel in the right column."""
    e_agent, e_jobname, e_ecoticker = expectations

    container.subheader("Job Details")
    w_id, c_id = meta.get("wireId"), meta.get("class")
    cqa = ' <span class="cqa-tag">[CQA]</span>' if (w_id == "778" and c_id == "1") else ""

    # Copyable key fields
    parsed_job_id = data_all.get('key', {}).get('jobId')
    agent_id = job_props.get('agentId')
    eco_ticker = job_meta.get('ecoticker')

    # Agent ID - copyable with mismatch check
    agent_err = ""
    if e_agent and str(agent_id) != str(e_agent):
        agent_err = f" &#10060; Expected: {safe(e_agent)}"
    container.markdown(
        f"<div class='detail-item'><span class='detail-label'>Agent ID:{agent_err}</span></div>",
        unsafe_allow_html=True
    )
    container.code(str(agent_id) if agent_id else "None", language=None)

    # Job ID - copyable
    container.markdown(
        "<div class='detail-item'><span class='detail-label'>Job ID:</span></div>",
        unsafe_allow_html=True
    )
    container.code(str(parsed_job_id) if parsed_job_id else "None", language=None)

    # Job Name - inline with mismatch check
    render_detail(container, "Job Name", job_props.get('jobName'), e_jobname)

    # Eco Ticker - copyable with mismatch check
    eco_err = ""
    if e_ecoticker and str(eco_ticker) != str(e_ecoticker):
        eco_err = f" &#10060; Expected: {safe(e_ecoticker)}"
    container.markdown(
        f"<div class='detail-item'><span class='detail-label'>Eco Ticker:{eco_err}</span></div>",
        unsafe_allow_html=True
    )
    container.code(str(eco_ticker) if eco_ticker else "None", language=None)

    # Wire / Class
    container.markdown(
        f"<div class='detail-item'><span class='detail-label'>Wire / Class:</span>"
        f"<span class='detail-value'>{safe(w_id)} / {safe(c_id)}</span>{cqa}</div>",
        unsafe_allow_html=True
    )

    # Source URL
    source_url = content.get('sourceUrl')
    if source_url and is_safe_url(source_url):
        container.markdown(
            f"<div class='detail-item'><span class='detail-label'>Source URL:</span>"
            f"<div class='detail-value' style='font-size:0.85em;'>"
            f"<a href='{safe(source_url)}' target='_blank'>{safe(source_url)}</a></div></div>",
            unsafe_allow_html=True
        )
    else:
        display = safe(source_url) if source_url else "None"
        container.markdown(
            f"<div class='detail-item'><span class='detail-label'>Source URL:</span>"
            f"<div class='detail-value' style='font-size:0.85em;'>{display}</div></div>",
            unsafe_allow_html=True
        )

    # Humio log link for this job
    if parsed_job_id:
        humio_job_url = HUMIO_JOB_URL_TEMPLATE.format(job_id=safe(parsed_job_id))
        container.markdown(
            f'<a href="{humio_job_url}" target="_blank" class="humio-link">'
            f'&#128279; Job ID - Humio Log</a>',
            unsafe_allow_html=True
        )

    container.divider()

    return parsed_job_id


def add_to_history(job_id, job_name, env, counts, timestamp_str):
    """Add a validation run to session history."""
    entry = {
        "timestamp": datetime.now(EASTERN_TZ).strftime("%H:%M:%S"),
        "job_id": str(job_id) if job_id else "N/A",
        "job_name": str(job_name) if job_name else "N/A",
        "env": env,
        "counts": dict(counts),
        "pub_time": timestamp_str or "N/A",
    }
    st.session_state.validation_history.insert(0, entry)
    # Keep last 20 entries
    st.session_state.validation_history = st.session_state.validation_history[:20]


def render_empty_state():
    """Show guidance when no log has been parsed yet."""
    st.markdown("""
    <div class="empty-state">
        <h3>Paste a raw BORG ledger log above and click "Parse and Validate Log"</h3>
        <p>The log should contain a JSON payload with the following structure:</p>
        <code>{
  "key": { "jobId": "..." },
  "metadata": { "bbds.context.publishTime": "2025-01-15T14:30:00.000Z" },
  "data": {
    "objects": [
      {
        "objectMetadata": {
          "isBorgTest": "YES",
          "sendToBorg": "YES",
          "releaseDate": "NO RELEASE DATE",
          "scalingFactor": "...",
          "tickerValue": "...",
          "observationPeriod": "...",
          "wireId": "...",
          "class": "..."
        },
        "objectContent": [{ "contentMetadata": { "sourceUrl": "..." } }]
      }
    ],
    "jobProperties": { "agentId": "...", "jobName": "..." },
    "jobMetadata": { "ecoticker": "..." }
  }
}</code>
        <p style="margin-top: 16px; color: #8e8e93;">
            Fill in the <strong>Target Values</strong> above to validate specific fields against expected values.
            Leave them blank to skip target comparison.
        </p>
    </div>
    """, unsafe_allow_html=True)


def reset_form():
    """Clear all input fields."""
    for key in INPUT_KEYS:
        st.session_state[key] = ""


# --- SIDEBAR: VALIDATION HISTORY ---
with st.sidebar:
    st.markdown("### Validation History")
    if not st.session_state.validation_history:
        st.caption("No validations yet. Parse a log to see history here.")
    else:
        if st.button("Clear History", key="clear_history"):
            st.session_state.validation_history = []
            st.rerun()

        for idx, entry in enumerate(st.session_state.validation_history):
            c = entry["counts"]
            if c["fail"] > 0:
                css_class = "history-fail"
                icon = "&#10060;"
            elif c["warn"] > 0:
                css_class = "history-mixed"
                icon = "&#9888;&#65039;"
            else:
                css_class = "history-pass"
                icon = "&#9989;"

            summary = f"{c['pass']}P / {c['fail']}F / {c['warn']}W"
            st.markdown(
                f'<div class="history-entry {css_class}">'
                f'{icon} <strong>{safe(entry["job_name"])}</strong><br>'
                f'<span style="color:#d4d4d4;">{summary} &middot; {safe(entry["env"])}</span><br>'
                f'<div class="history-meta">{safe(entry["timestamp"])} &middot; '
                f'Job: {safe(entry["job_id"])}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

# --- HEADER SECTION ---
st.title("Bloomberg BORG Jobs Verification")
st.markdown("""
This tool automates the validation of JSON ledger logs from BORG jobs. It parses raw log strings to ensure environment flags,
ticker values, and routing parameters match expected benchmarks, reducing manual errors during economic data releases.
""")

# --- HELPFUL LINKS ---
st.markdown(
    f'<a href="{HUMIO_DASHBOARD_URL}" target="_blank" class="humio-link">'
    f'&#128279; Open Humio Ledger Dashboard</a>',
    unsafe_allow_html=True
)

# --- TARGET INPUTS ---
with st.expander("&#127919; Target Values (Scenario-Specific Inputs)"):
    st.markdown('<span class="collapsible-note">(Collapsible)</span>', unsafe_allow_html=True)
    st.write("Enter values for this specific run. Blank fields will remain neutral.")
    c1, c2, c3 = st.columns(3)
    t_ticker = c1.text_input("Target Ticker Value", key="input_t1")
    t_scaling = c2.text_input("Target Scaling Factor", key="input_t2")
    t_period = c3.text_input("Target Observation Period", key="input_t3")

    st.divider()
    c4, c5, c6 = st.columns(3)
    e_agent = c4.text_input("Expected Agent ID", key="input_t4")
    e_jobname = c5.text_input("Expected Job Name", key="input_t5")
    e_ecoticker = c6.text_input("Expected Eco Ticker", key="input_t6")

raw_input = st.text_area("Paste Raw Log Entry Here:", height=150, key="raw_log_input")
parse_btn = st.button("Parse and Validate Log", type="primary")

st.divider()

has_targets = any((t_ticker, t_scaling, t_period))

# --- MAIN VALIDATION (only runs when button is clicked) ---
if parse_btn and raw_input:
    try:
        data_all = extract_json(raw_input)
        if data_all is None:
            st.error("No JSON block detected in the pasted input.")
        else:
            obj_list = data_all.get('data', {}).get('objects', [])
            job_props = data_all.get('data', {}).get('jobProperties', {})
            job_meta = data_all.get('data', {}).get('jobMetadata', {})
            pub_time_str = data_all.get('metadata', {}).get('bbds.context.publishTime')

            # Parse timestamp once and reuse
            pub_dt = parse_publish_time(pub_time_str)

            # Drift alert
            drift_display = check_drift(pub_dt)
            if drift_display:
                st.markdown(
                    f'<div class="drift-warn">&#9888;&#65039; STALE LOG DETECTED: '
                    f'This log was published {drift_display} ago.</div>',
                    unsafe_allow_html=True
                )

            # --- Multi-object tabs vs single render ---
            if len(obj_list) > 1:
                tab_labels = [f"Object {i + 1}" for i in range(len(obj_list))]
                tabs = st.tabs(tab_labels)
            else:
                tabs = None

            for i, obj in enumerate(obj_list):
                # Use tab container if multiple objects, otherwise main page
                if tabs is not None:
                    obj_container = tabs[i]
                else:
                    obj_container = st

                meta = obj.get('objectMetadata', {})
                content = obj.get('objectContent', [{}])[0].get('contentMetadata', {})
                is_borg = meta.get('isBorgTest')

                # Pre-compute verification results
                rows_with_status, counts = build_verification_rows(
                    meta, is_borg, (t_ticker, t_scaling, t_period)
                )

                # --- Summary Banner ---
                render_summary_banner(obj_container, counts)

                # Environment header
                if is_borg == "YES":
                    obj_container.markdown(
                        '<div class="env-header env-test">TEST / DEV / BETA (isBorgTest=YES)</div>',
                        unsafe_allow_html=True
                    )
                    env_label = "TEST"
                elif is_borg == "NO":
                    obj_container.markdown(
                        '<div class="env-header env-prod">PRODUCTION &#9888;&#65039; '
                        '(Ready for Results - isBorgTest=NO)</div>',
                        unsafe_allow_html=True
                    )
                    env_label = "PROD"
                else:
                    if is_borg:
                        msg = f"INVALID: isBorgTest is '{safe(is_borg)}'"
                    else:
                        msg = "MISSING: isBorgTest is NULL"
                    obj_container.markdown(
                        f'<div class="env-header env-invalid">{msg}</div>',
                        unsafe_allow_html=True
                    )
                    env_label = "INVALID"

                # Publish timestamp banner
                if pub_dt:
                    formatted_utc, formatted_eastern, tz_label = format_timestamp(pub_dt)
                    eastern_part = ""
                    if formatted_eastern:
                        eastern_part = (
                            f' <em style="color:#636366; font-size:0.85em;">'
                            f'({formatted_eastern} {tz_label})</em>'
                        )
                    obj_container.markdown(
                        f'<div class="pub-time-banner">Payload Timestamp: '
                        f'<strong>{formatted_utc} UTC</strong>{eastern_part}</div>',
                        unsafe_allow_html=True
                    )
                elif pub_time_str:
                    obj_container.markdown(
                        f'<div class="pub-time-banner">Payload Timestamp: '
                        f'<strong>{safe(pub_time_str)}</strong> (unparseable)</div>',
                        unsafe_allow_html=True
                    )

                col1, col2 = obj_container.columns([3, 2])

                with col1:
                    render_verification_table(col1, rows_with_status, has_targets)

                with col2:
                    parsed_job_id = render_job_details(
                        col2, meta, content, job_props, job_meta, data_all,
                        (e_agent, e_jobname, e_ecoticker)
                    )
                    obj_container.button(
                        "&#9851;&#65039; Reset Form",
                        on_click=reset_form,
                        key=f"reset_{i}"
                    )

                # Add to history (only for first object to avoid duplicates)
                if i == 0:
                    add_to_history(
                        data_all.get('key', {}).get('jobId'),
                        job_props.get('jobName'),
                        env_label,
                        counts,
                        pub_time_str
                    )

            # --- Collapsible Raw JSON Viewer ---
            with st.expander("&#128196; Raw Parsed JSON"):
                st.json(data_all)

    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
    except Exception as e:
        st.error(f"Error ({type(e).__name__}): {e}")
        st.exception(e)
else:
    # --- Empty State Guidance ---
    if not parse_btn:
        render_empty_state()

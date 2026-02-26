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

    /* Fix for expander chevron arrows - hide literal icon text */
    [data-testid="stExpander"] details summary svg,
    [data-testid="st-expander"] details summary svg {
        display: inline-block !important;
    }
    [data-testid="stExpander"] summary span[data-testid="stMarkdownContainer"],
    [data-testid="st-expander"] summary span[data-testid="stMarkdownContainer"] {
        display: inline !important;
    }
    /* Hide raw Material Icon text fallback */
    [data-testid="stExpander"] summary::before,
    [data-testid="stExpander"] summary::after,
    [data-testid="st-expander"] .streamlit-expanderHeader::before,
    [data-testid="st-expander"] .streamlit-expanderHeader::after {
        content: "" !important;
        display: none !important;
    }
    details summary .material-icons,
    details summary [class*="icon"] {
        font-size: 0 !important;
        overflow: hidden !important;
    }
    details summary .material-icons::before,
    details summary [class*="icon"]::before {
        font-size: 1rem !important;
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


def render_verification_table(container, meta, is_borg, has_targets, targets):
    """Render the verification table in the left column."""
    t_ticker, t_scaling, t_period = targets

    container.subheader("Verification")
    h_cols = container.columns([1.5, 1, 1, 1] if has_targets else [1.5, 1, 1])
    h_cols[0].markdown("**Field**")
    h_cols[1].markdown("**Actual**")
    if has_targets:
        h_cols[2].markdown("**Target**")
    h_cols[-1].markdown("**Status**")

    rows = [
        ("isBorgTest", is_borg, "YES/NO", "binary"),
        ("sendToBorg", meta.get("sendToBorg"), "YES", "fixed"),
        ("releaseDate", meta.get("releaseDate"), "NO RELEASE DATE", "fixed"),
        ("scalingFactor", meta.get("scalingFactor"), t_scaling, "target"),
        ("tickerValue", meta.get("tickerValue"), t_ticker, "target"),
        ("observationPeriod", meta.get("observationPeriod"), t_period, "target"),
    ]

    for label, act, goal, r_type in rows:
        status, bg = "&#128064; Review", "transparent"
        is_empty = act is None or str(act).strip() == ""

        if is_empty:
            status, bg = "&#10060; MISSING", "rgba(255, 59, 48, 0.15)"
        elif r_type == "binary":
            if act == "YES":
                status, bg = "&#129514; TEST", "rgba(255, 204, 0, 0.15)"
            elif act == "NO":
                status, bg = "&#128640; PROD", "rgba(76, 217, 100, 0.15)"
            else:
                status, bg = f"&#10060; INVALID (Exp: {safe(goal)})", "rgba(255, 59, 48, 0.15)"
        elif r_type == "fixed":
            if act == goal:
                status, bg = "&#9989; OK", "rgba(76, 217, 100, 0.1)"
            else:
                status, bg = f"&#10060; MISMATCH (Exp: {safe(goal)})", "rgba(255, 59, 48, 0.15)"
        elif r_type == "target" and goal:
            if str(act) == str(goal):
                status, bg = "&#9989; MATCH", "rgba(76, 217, 100, 0.1)"
            else:
                status, bg = f"&#10060; MISMATCH (Exp: {safe(goal)})", "rgba(255, 59, 48, 0.15)"

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
            f'<div style="background:{bg}; padding:5px; font-weight:600; text-align:right;">{status}</div>',
            unsafe_allow_html=True
        )


def render_job_details(container, meta, content, job_props, job_meta, data_all, expectations):
    """Render the job details panel in the right column."""
    e_agent, e_jobname, e_ecoticker = expectations

    container.subheader("Job Details")
    w_id, c_id = meta.get("wireId"), meta.get("class")
    cqa = ' <span class="cqa-tag">[CQA]</span>' if (w_id == "778" and c_id == "1") else ""

    render_detail(container, "Agent ID", job_props.get('agentId'), e_agent)
    parsed_job_id = data_all.get('key', {}).get('jobId')
    render_detail(container, "Job ID", parsed_job_id)
    render_detail(container, "Job Name", job_props.get('jobName'), e_jobname)
    render_detail(container, "Eco Ticker", job_meta.get('ecoticker'), e_ecoticker)
    container.markdown(
        f"<div class='detail-item'><span class='detail-label'>Wire / Class:</span>"
        f"<span class='detail-value'>{safe(w_id)} / {safe(c_id)}</span>{cqa}</div>",
        unsafe_allow_html=True
    )

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


def reset_form():
    """Clear all input fields."""
    for key in INPUT_KEYS:
        st.session_state[key] = ""


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

            for i, obj in enumerate(obj_list):
                meta = obj.get('objectMetadata', {})
                content = obj.get('objectContent', [{}])[0].get('contentMetadata', {})
                is_borg = meta.get('isBorgTest')

                # Environment header
                if is_borg == "YES":
                    st.markdown(
                        '<div class="env-header env-test">TEST / DEV / BETA (isBorgTest=YES)</div>',
                        unsafe_allow_html=True
                    )
                elif is_borg == "NO":
                    st.markdown(
                        '<div class="env-header env-prod">PRODUCTION &#9888;&#65039; '
                        '(Ready for Results - isBorgTest=NO)</div>',
                        unsafe_allow_html=True
                    )
                else:
                    if is_borg:
                        msg = f"INVALID: isBorgTest is '{safe(is_borg)}'"
                    else:
                        msg = "MISSING: isBorgTest is NULL"
                    st.markdown(
                        f'<div class="env-header env-invalid">{msg}</div>',
                        unsafe_allow_html=True
                    )

                # Publish timestamp banner
                if pub_dt:
                    formatted_utc, formatted_eastern, tz_label = format_timestamp(pub_dt)
                    eastern_part = ""
                    if formatted_eastern:
                        eastern_part = (
                            f' <em style="color:#636366; font-size:0.85em;">'
                            f'({formatted_eastern} {tz_label})</em>'
                        )
                    st.markdown(
                        f'<div class="pub-time-banner">Payload Timestamp: '
                        f'<strong>{formatted_utc} UTC</strong>{eastern_part}</div>',
                        unsafe_allow_html=True
                    )
                elif pub_time_str:
                    st.markdown(
                        f'<div class="pub-time-banner">Payload Timestamp: '
                        f'<strong>{safe(pub_time_str)}</strong> (unparseable)</div>',
                        unsafe_allow_html=True
                    )

                col1, col2 = st.columns([3, 2])

                with col1:
                    render_verification_table(
                        col1, meta, is_borg, has_targets,
                        (t_ticker, t_scaling, t_period)
                    )

                with col2:
                    render_job_details(
                        col2, meta, content, job_props, job_meta, data_all,
                        (e_agent, e_jobname, e_ecoticker)
                    )
                    st.button("&#9851;&#65039; Reset Form", on_click=reset_form, key=f"reset_{i}")

    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
    except Exception as e:
        st.error(f"Error ({type(e).__name__}): {e}")
        st.exception(e)

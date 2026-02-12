import streamlit as st
import json
import re
from datetime import datetime, timezone

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
    .detail-value a { color: #0a84ff; text-decoration: none; } /* Make URLs clickable */
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

# --- HEADER SECTION ---
st.title("Bloomberg BORG Jobs Verification")
st.markdown("""
This tool automates the validation of JSON ledger logs from BORG jobs. It parses raw log strings to ensure environment flags,
ticker values, and routing parameters match expected benchmarks, reducing manual errors during economic data releases.
""")

# --- HELPFUL LINKS ---
humio_url = "https://humio.prod.bloomberg.com/guts_wam/dashboards/hEIe82DuFR8EVa7CJJdQn9UzuEejOJ2E?updateFrequency=never&tz=America/New_York&sharedTime=true&start=15m&fullscreen=false&$jobId=%5B%22*%22%5D"
st.markdown(f'<a href="{humio_url}" target="_blank" class="humio-link">🔗 Open Humio Ledger Dashboard</a>', unsafe_allow_html=True)

# --- 1. TARGET INPUTS ---
# Use Streamlit's expander with "(Collapsible)" styled
with st.expander("🎯 Target Values (Scenario-Specific Inputs)"):
    st.markdown('<span class="collapsible-note">(Collapsible)</span>', unsafe_allow_html=True)
    st.write("Enter values for this specific run. Blank fields will remain neutral.")
    c1, c2, c3 = st.columns([1.2, 1.2, 1.2])  # Adjusted column widths for better spacing
    t_ticker = c1.text_input("Target Ticker Value", key="input_t1")
    t_scaling = c2.text_input("Target Scaling Factor", key="input_t2")
    t_period = c3.text_input("Target Observation Period", key="input_t3")

    st.divider()
    c4, c5, c6 = st.columns([1.2, 1.2, 1.2])  # Adjusted column widths for better spacing
    e_agent = c4.text_input("Expected Agent ID", key="input_t4")
    e_jobname = c5.text_input("Expected Job Name", key="input_t5")
    e_ecoticker = c6.text_input("Expected Eco Ticker", key="input_t6")

raw_input = st.text_area("Paste Raw Log Entry Here:", height=150, key="raw_log_input")
parse_btn = st.button("Parse and Validate Log", type="primary")

# Add a horizontal line below the button
st.divider()

has_targets = any([t_ticker, t_scaling, t_period])

if raw_input:
    try:
        json_match = re.search(r'(\{.*\})', raw_input)
        if json_match:
            data_all = json.loads(json_match.group(1))
            obj_list = data_all.get('data', {}).get('objects', [])
            job_props = data_all.get('data', {}).get('jobProperties', {})
            job_meta = data_all.get('data', {}).get('jobMetadata', {})
            pub_time_str = data_all.get('metadata', {}).get('bbds.context.publishTime')

            # --- DRIFT ALERT LOGIC (Set to 15 mins) ---
            if pub_time_str:
                pub_time = datetime.strptime(pub_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                drift_seconds = (datetime.now(timezone.utc) - pub_time).total_seconds()
                if drift_seconds > 900:  # 15 Minutes
                    drift_hours = int(drift_seconds // 3600)
                    drift_mins = int((drift_seconds % 3600) // 60)
                    drift_display = f"{drift_hours}h {drift_mins}m" if drift_hours > 0 else f"{drift_mins}m"
                    st.markdown(f'<div class="drift-warn">⚠️ STALE LOG DETECTED: This log was published {drift_display} ago.</div>', unsafe_allow_html=True)

            for i, obj in enumerate(obj_list):
                meta = obj.get('objectMetadata', {})
                content = obj.get('objectContent', [{}])[0].get('contentMetadata', {})
                is_borg = meta.get('isBorgTest')

                # --- ENVIRONMENT HEADER ---
                if is_borg == "YES":
                    st.markdown('<div class="env-header env-test">TEST / DEV / BETA (isBorgTest=YES)</div>', unsafe_allow_html=True)
                elif is_borg == "NO":
                    st.markdown('<div class="env-header env-prod">PRODUCTION ⚠️ (Ready for Results - isBorgTest=NO)</div>', unsafe_allow_html=True)
                else:
                    msg = f"INVALID: isBorgTest is '{is_borg}'" if is_borg else "MISSING: isBorgTest is NULL"
                    st.markdown(f'<div class="env-header env-invalid">{msg}</div>', unsafe_allow_html=True)

                # --- PUBLISH TIMESTAMP ---
                if pub_time_str:
                    try:
                        pt = datetime.strptime(pub_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                        formatted_pub = pt.strftime("%Y-%m-%d %H:%M:%S.") + f"{pt.microsecond // 1000:03d}"
                    except Exception:
                        formatted_pub = pub_time_str
                    st.markdown(f'<div class="pub-time-banner">Payload Timestamp: <strong>{formatted_pub} UTC</strong></div>', unsafe_allow_html=True)

                col1, col2 = st.columns([3, 2])

                with col1:
                    st.subheader("Verification")
                    h_cols = st.columns([1.5, 1, 1, 1] if has_targets else [1.5, 1, 1])
                    h_cols[0].markdown("**Field**")
                    h_cols[1].markdown("**Actual**")
                    if has_targets: h_cols[2].markdown("**Target**")
                    h_cols[-1].markdown("**Status**")

                    # Organized Table: isBorgTest, sendToBorg, releaseDate, scalingFactor, tickerValue, observationPeriod
                    rows = [
                        ("isBorgTest", is_borg, "YES/NO", "binary"),
                        ("sendToBorg", meta.get("sendToBorg"), "YES", "fixed"),
                        ("releaseDate", meta.get("releaseDate"), "NO RELEASE DATE", "fixed"),
                        ("scalingFactor", meta.get("scalingFactor"), t_scaling, "target"),
                        ("tickerValue", meta.get("tickerValue"), t_ticker, "target"),
                        ("observationPeriod", meta.get("observationPeriod"), t_period, "target")
                    ]

                    for label, act, goal, r_type in rows:
                        status, bg = "👀 Review", "transparent"
                        is_empty = act is None or str(act).strip() == ""

                        if is_empty:
                            status, bg = "❌ MISSING", "rgba(255, 59, 48, 0.15)"
                        elif r_type == "binary":
                            if act == "YES": status, bg = "🧪 TEST", "rgba(255, 204, 0, 0.15)"
                            elif act == "NO": status, bg = "🚀 PROD", "rgba(76, 217, 100, 0.15)"
                            else: status, bg = f"❌ INVALID (Exp: {goal})", "rgba(255, 59, 48, 0.15)"
                        elif r_type == "fixed":
                            if act == goal: status, bg = "✅ OK", "rgba(76, 217, 100, 0.1)"
                            else: status, bg = f"❌ MISMATCH (Exp: {goal})", "rgba(255, 59, 48, 0.15)"
                        elif r_type == "target" and goal:
                            if str(act) == str(goal): status, bg = "✅ MATCH", "rgba(76, 217, 100, 0.1)"
                            else: status, bg = f"❌ MISMATCH (Exp: {goal})", "rgba(255, 59, 48, 0.15)"

                        row_cols = st.columns([1.5, 1, 1, 1] if has_targets else [1.5, 1, 1])
                        row_cols[0].markdown(f'<div style="background:{bg}; padding:5px; font-weight:600;">{label}</div>', unsafe_allow_html=True)
                        row_cols[1].markdown(f'<div style="background:{bg}; padding:5px; font-family:monospace;">{act}</div>', unsafe_allow_html=True)
                        if has_targets:
                            row_cols[2].markdown(f'<div style="background:{bg}; padding:5px; color:#8e8e93;">{goal if r_type=="target" and goal else "-"}</div>', unsafe_allow_html=True)
                        row_cols[-1].markdown(f'<div style="background:{bg}; padding:5px; font-weight:600; text-align:right;">{status}</div>', unsafe_allow_html=True)

                with col2:
                    st.subheader("Job Details")
                    w_id, c_id = meta.get("wireId"), meta.get("class")
                    cqa = f' <span class="cqa-tag">[CQA]</span>' if (w_id == "778" and c_id == "1") else ""

                    def render_detail(label, actual, expected):
                        err = f" <span style='color:#ff3b30;'>❌ (Exp: {expected})</span>" if expected and str(actual) != str(expected) else ""
                        # Make source URLs clickable
                        if label == "Source URL" and actual:
                            actual = f'<a href="{actual}" target="_blank">{actual}</a>'
                        st.markdown(f"<div class='detail-item'><span class='detail-label'>{label}:</span><span class='detail-value'>{actual}</span>{err}</div>", unsafe_allow_html=True)

                    render_detail("Agent ID", job_props.get('agentId'), e_agent)
                    parsed_job_id = data_all.get('key', {}).get('jobId')
                    render_detail("Job ID", parsed_job_id, None)
                    render_detail("Job Name", job_props.get('jobName'), e_jobname)
                    render_detail("Eco Ticker", job_meta.get('ecoticker'), e_ecoticker)
                    st.markdown(f"<div class='detail-item'><span class='detail-label'>Wire / Class:</span><span class='detail-value'>{w_id} / {c_id}</span>{cqa}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='detail-item'><span class='detail-label'>Source URL:</span><div class='detail-value' style='font-size:0.85em;'>{content.get('sourceUrl')}</div></div>", unsafe_allow_html=True)

                    # --- HUMIO LOG LINK ---
                    if parsed_job_id:
                        humio_job_url = f"https://humio.prod.bloomberg.com/guts_wam/dashboards/hEIe82DuFR8EVa7CJJdQn9UzuEejOJ2E?%24jobId=%5B%22{parsed_job_id}%22%5D&filterId=9e3WFUID6IX7ypte9Osrm3vm626FHi2y&fullscreen=false&sharedTime=true&start=15m&updateFrequency=never"
                        st.markdown(f'<a href="{humio_job_url}" target="_blank" class="humio-link">🔗 Job ID - Humio Log</a>', unsafe_allow_html=True)

                    st.divider()
                    def reset_form():
                        st.session_state["raw_log_input"] = ""
                    st.button("♻️ Reset Form", on_click=reset_form)

        else: st.error("No JSON block detected.")
    except Exception as e: st.error(f"Error: {e}")

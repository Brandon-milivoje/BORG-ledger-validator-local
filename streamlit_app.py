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
    .env-header { padding: 12px 20px; border-radius: 4px; font-weight: 600; margin-bottom: 10px; border-left: 6px solid; }
    .env-test { background-color: #3a321d; color: #ffcc00; border-color: #ffcc00; }
    .env-prod { background-color: #1b2e1f; color: #4cd964; border-color: #4cd964; }
    .env-invalid { background-color: #3d1c1c; color: #ff3b30; border-color: #ff3b30; }
    .drift-warn { background-color: #3d1c1c; color: #ff3b30; padding: 10px; border-radius: 4px; font-weight: 600; margin-bottom: 15px; border: 1px solid #ff3b30; }
    .detail-item { margin-bottom: 10px; font-size: 0.95em; line-height: 1.6; }
    .detail-label { color: #8e8e93; font-weight: 500; margin-right: 8px; }
    .detail-value { color: #ffffff; font-family: 'Roboto Mono', monospace; word-break: break-all; }
    .cqa-tag { color: #ffcc00; font-weight: 600; margin-left: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'history' not in st.session_state:
    st.session_state.history = []

# --- HEADER SECTION ---
st.title("Bloomberg BORG Jobs Verification")
col_h1, col_h2 = st.columns([2, 1])

with col_h1:
    st.markdown("Automated validation for BORG JSON ledger logs. Ensures environment flags and data points match benchmarks.")
    humio_url = "https://humio.prod.bloomberg.com/guts_wam/dashboards/hEIe82DuFR8EVa7CJJdQn9UzuEejOJ2E?updateFrequency=never&tz=America/New_York&sharedTime=true&start=15m&fullscreen=false&$jobId=%5B%22*%22%5D"
    st.markdown(f'<a href="{humio_url}" target="_blank" style="text-decoration:none; color:#0a84ff; font-size:0.9em;">🔗 Open Humio Ledger Dashboard</a>', unsafe_allow_html=True)

# --- 1. TARGET INPUTS ---
with st.expander("🎯 Target Values (Scenario-Specific Inputs)", expanded=False):
    c1, c2, c3 = st.columns(3)
    t_ticker = c1.text_input("Target Ticker Value", key="t1")
    t_scaling = c2.text_input("Target Scaling Factor", key="t2")
    t_period = c3.text_input("Target Observation Period", key="t3")
    st.divider()
    c4, c5, c6 = st.columns(3)
    e_agent = c4.text_input("Expected Agent ID", key="t4")
    e_jobname = c5.text_input("Expected Job Name", key="t5")
    e_ecoticker = c6.text_input("Expected Eco Ticker", key="t6")

# --- 2. INPUT AREA ---
raw_input = st.text_area("Paste Raw Log Entry Here:", height=150)
parse_btn = st.button("Parse and Validate Log")

if raw_input and parse_btn:
    try:
        json_match = re.search(r'(\{.*\})', raw_input)
        if json_match:
            data_all = json.loads(json_match.group(1))
            obj_list = data_all.get('data', {}).get('objects', [])
            job_meta = data_all.get('data', {}).get('jobMetadata', {})
            job_props = data_all.get('data', {}).get('jobProperties', {})
            pub_time_str = data_all.get('metadata', {}).get('bbds.context.publishTime')

            # --- DRIFT ALERT LOGIC ---
            if pub_time_str:
                pub_time = datetime.strptime(pub_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                drift_seconds = (now - pub_time).total_seconds()
                if drift_seconds > 300: # 5 Minutes
                    st.markdown(f'<div class="drift-warn">⚠️ STALE LOG DETECTED: This log was published {int(drift_seconds/60)} minutes ago. Verify you are looking at the current run.</div>', unsafe_allow_html=True)

            for i, obj in enumerate(obj_list):
                meta = obj.get('objectMetadata', {})
                content = obj.get('objectContent', [{}])[0].get('contentMetadata', {})
                is_borg = meta.get('isBorgTest')
                
                # Update Session History
                history_entry = {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "ticker": job_meta.get('ecoticker', 'N/A'),
                    "env": "TEST" if is_borg == "YES" else "PROD",
                    "status": "Checked"
                }
                st.session_state.history.insert(0, history_entry)

                # --- UI DISPLAY ---
                if is_borg == "YES": st.markdown('<div class="env-header env-test">TEST / DEV / BETA (isBorgTest=YES)</div>', unsafe_allow_html=True)
                elif is_borg == "NO": st.markdown('<div class="env-header env-prod">PRODUCTION ⚠️ (isBorgTest=NO)</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns([3, 2])
                with col1:
                    st.subheader("Verification")
                    has_targets = any([t_ticker, t_scaling, t_period])
                    h_cols = st.columns([1.5, 1, 1, 1] if has_targets else [1.5, 1, 1])
                    h_cols[0].write("**Field**"); h_cols[1].write("**Actual**")
                    if has_targets: h_cols[2].write("**Target**")
                    h_cols[-1].write("**Status**")

                    rows = [
                        ("isBorgTest", is_borg, "YES/NO", "binary"),
                        ("sendToBorg", meta.get("sendToBorg"), "YES", "fixed"),
                        ("releaseDate", meta.get("releaseDate"), "NO RELEASE DATE", "fixed"),
                        ("scalingFactor", meta.get("scalingFactor"), t_scaling, "target"),
                        ("tickerValue", meta.get("tickerValue"), t_ticker, "target"),
                        ("observationPeriod", meta.get("observationPeriod"), t_period, "target")
                    ]

                    slack_summary = f"*Verification Summary: {job_meta.get('ecoticker')}*\n"
                    for label, act, goal, r_type in rows:
                        bg = "transparent"; status = "Review"
                        if not act: status, bg = "MISSING", "rgba(255, 59, 48, 0.15)"
                        elif r_type == "binary":
                            if act == "YES": status, bg = "🧪 TEST", "rgba(255, 204, 0, 0.15)"
                            elif act == "NO": status, bg = "🚀 PROD", "rgba(76, 217, 100, 0.15)"
                            else: status, bg = "INVALID", "rgba(255, 59, 48, 0.15)"
                        elif r_type == "fixed":
                            status, bg = ("✅ OK", "rgba(76, 217, 100, 0.1)") if act == goal else ("❌ FAIL", "rgba(255, 59, 48, 0.15)")
                        elif r_type == "target" and goal:
                            status, bg = ("✅ MATCH", "rgba(76, 217, 100, 0.1)") if str(act) == str(goal) else ("❌ FAIL", "rgba(255, 59, 48, 0.15)")

                        r_cols = st.columns([1.5, 1, 1, 1] if has_targets else [1.5, 1, 1])
                        r_cols[0].markdown(f'<div style="background:{bg}; padding:5px;">{label}</div>', unsafe_allow_html=True)
                        r_cols[1].markdown(f'<div style="background:{bg}; padding:5px; font-family:monospace;">{act}</div>', unsafe_allow_html=True)
                        if has_targets: r_cols[2].markdown(f'<div style="background:{bg}; padding:5px; color:gray;">{goal if r_type=="target" else "-"}</div>', unsafe_allow_html=True)
                        r_cols[-1].markdown(f'<div style="background:{bg}; padding:5px; text-align:right; font-weight:600;">{status}</div>', unsafe_allow_html=True)
                        slack_summary += f"• {label}: {act} ({status})\n"

                with col2:
                    st.subheader("Job Details")
                    w_id, c_id = meta.get("wireId"), meta.get("class")
                    cqa = ' <span class="cqa-tag">[CQA]</span>' if (w_id == "778" and c_id == "1") else ""
                    st.markdown(f"<div class='detail-item'><span class='detail-label'>Agent ID:</span><span class='detail-value'>{job_props.get('agentId')}</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='detail-item'><span class='detail-label'>Job Name:</span><span class='detail-value'>{job_props.get('jobName')}</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='detail-item'><span class='detail-label'>Wire/Class:</span><span class='detail-value'>{w_id}/{c_id}</span>{cqa}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='detail-item'><span class='detail-label'>Source URL:</span><div class='detail-value'>{content.get('sourceUrl')}</div></div>", unsafe_allow_html=True)
                    st.divider()
                    st.text_area("Copy for Team (Slack/Teams):", value=slack_summary, height=150)
                    if st.button("♻️ Reset Form"): st.rerun()

    except Exception as e: st.error(f"Error: {e}")

# --- 3. SESSION HISTORY SIDEBAR ---
with st.sidebar:
    st.header("🕒 Recently Parsed")
    if not st.session_state.history: st.write("No history yet.")
    for h in st.session_state.history[:10]:
        st.markdown(f"**{h['ticker']}** ({h['time']})  \n`Env: {h['env']}`")
        st.divider()

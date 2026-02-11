import streamlit as st
import json
import re
from datetime import datetime

# --- SET PAGE CONFIG ---
st.set_page_config(page_title="BORG Jobs Verification", layout="wide")

# --- BLOOMBERG-STYLE THEMING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&family=Inter:wght@400;600&display=swap');
    
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    code { font-family: 'Roboto Mono', monospace !important; color: #d4d4d4 !important; background: none !important; padding: 0 !important; }

    /* Fix for overlapping text in expanders */
    .st-emotion-cache-p4mowd { overflow: visible !important; }

    /* Environment Headers */
    .env-header { padding: 12px 20px; border-radius: 4px; font-weight: 600; margin-bottom: 20px; border-left: 6px solid; }
    .env-test { background-color: #3a321d; color: #ffcc00; border-color: #ffcc00; }
    .env-prod { background-color: #1b2e1f; color: #4cd964; border-color: #4cd964; }
    .env-invalid { background-color: #3d1c1c; color: #ff3b30; border-color: #ff3b30; }

    /* Neutral Job Details */
    .detail-item { margin-bottom: 10px; font-size: 0.95em; line-height: 1.6; }
    .detail-label { color: #8e8e93; font-weight: 500; margin-right: 8px; }
    .detail-value { color: #ffffff; font-family: 'Roboto Mono', monospace; word-break: break-all; }
    
    /* CQA Yellow Label */
    .cqa-tag { color: #ffcc00; font-weight: 600; margin-left: 5px; }

    /* Utility Link Button */
    .humio-link {
        display: inline-block;
        padding: 5px 12px;
        background-color: #2c2c2e;
        color: #0a84ff !important;
        border-radius: 4px;
        text-decoration: none;
        font-size: 0.85em;
        border: 1px solid #3e3e3e;
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
st.write("")

# --- 1. TARGET INPUTS ---
with st.expander("🎯 Target Values (Scenario-Specific Inputs)", expanded=False):
    st.write("Enter values for this specific run. Blank fields will remain neutral.")
    c1, c2, c3 = st.columns(3)
    t_ticker = c1.text_input("Target Ticker Value", key="t1")
    t_scaling = c2.text_input("Target Scaling Factor", key="t2")
    t_period = c3.text_input("Target Observation Period", key="t3")
    
    st.divider()
    c4, c5, c6 = st.columns(3)
    e_agent = c4.text_input("Expected Agent ID", key="t4")
    e_jobname = c5.text_input("Expected Job Name", key="t5")
    e_ecoticker = c6.text_input("Expected Eco Ticker", key="t6")

# --- 2. PASTE AREA ---
raw_input = st.text_area("Paste Raw Log Entry Here:", height=150)
parse_btn = st.button("Parse and Validate Log")

has_targets = any([t_ticker, t_scaling, t_period])

if raw_input and parse_btn:
    try:
        json_match = re.search(r'(\{.*\})', raw_input)
        if json_match:
            data_all = json.loads(json_match.group(1))
            obj_list = data_all.get('data', {}).get('objects', [])
            job_props = data_all.get('data', {}).get('jobProperties', {})
            job_meta = data_all.get('data', {}).get('jobMetadata', {})

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
                    msg = f"INVALID: isBorgTest is '{is_borg}' (Expected YES or NO)" if is_borg else "MISSING: isBorgTest is NULL"
                    st.markdown(f'<div class="env-header env-invalid">{msg}</div>', unsafe_allow_html=True)

                col1, col2 = st.columns([3, 2])

                with col1:
                    st.subheader("Verification")
                    
                    # Columns setup
                    header_cols = st.columns([1.5, 1, 1, 1] if has_targets else [1.5, 1, 1])
                    header_cols[0].markdown("**Field**")
                    header_cols[1].markdown("**Actual**")
                    if has_targets: header_cols[2].markdown("**Target**")
                    header_cols[-1].markdown("**Status**")

                    # Order: isBorgTest, sendToBorg, releaseDate, scalingFactor, tickerValue, observationPeriod
                    rows = [
                        ("isBorgTest", is_borg, "YES/NO", "binary"),
                        ("sendToBorg", meta.get("sendToBorg"), "YES", "fixed"),
                        ("releaseDate", meta.get("releaseDate"), "NO RELEASE DATE", "fixed"),
                        ("scalingFactor", meta.get("scalingFactor"), t_scaling, "target"),
                        ("tickerValue", meta.get("tickerValue"), t_ticker, "target"),
                        ("observationPeriod", meta.get("observationPeriod"), t_period, "target")
                    ]

                    for label, act, goal, r_type in rows:
                        status = "👀 Review"
                        bg = "transparent"
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

                        # Build Row
                        row_cols = st.columns([1.5, 1, 1, 1] if has_targets else [1.5, 1, 1])
                        with row_cols[0]: st.markdown(f'<div style="background:{bg}; padding:5px; font-weight:600;">{label}</div>', unsafe_allow_html=True)
                        with row_cols[1]: st.markdown(f'<div style="background:{bg}; padding:5px; font-family:monospace;">{act}</div>', unsafe_allow_html=True)
                        
                        if has_targets:
                            target_display = goal if (r_type == "target" and goal) else "-"
                            with row_cols[2]: st.markdown(f'<div style="background:{bg}; padding:5px; color:#8e8e93;">{target_display}</div>', unsafe_allow_html=True)
                        
                        with row_cols[-1]: st.markdown(f'<div style="background:{bg}; padding:5px; font-weight:600; text-align:right;">{status}</div>', unsafe_allow_html=True)

                with col2:
                    st.subheader("Job Details")
                    
                    w_id, c_id = meta.get("wireId"), meta.get("class")
                    cqa = f' <span class="cqa-tag">[CQA]</span>' if (w_id == "778" and c_id == "1") else ""
                    
                    def render_detail(label, actual, expected):
                        err = ""
                        if expected and str(actual) != str(expected):
                            err = f" <span style='color:#ff3b30;'>❌ (Exp: {expected})</span>"
                        st.markdown(f"<div class='detail-item'><span class='detail-label'>{label}:</span><span class='detail-value'>{actual}</span>{err}</div>", unsafe_allow_html=True)

                    render_detail("Agent ID", job_props.get('agentId'), e_agent)
                    render_detail("Job Name", job_props.get('jobName'), e_jobname)
                    render_detail("Eco Ticker", job_meta.get('ecoticker'), e_ecoticker)
                    st.markdown(f"<div class='detail-item'><span class='detail-label'>Wire / Class:</span><span class='detail-value'>{w_id} / {c_id}</span>{cqa}</div>", unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='detail-item'><span class='detail-label'>Source URL:</span><div class='detail-value' style='font-size:0.85em;'>{content.get('sourceUrl')}</div></div>", unsafe_allow_html=True)
                    
                    st.divider()
                    if st.button("♻️ Reset Form"): st.rerun()

        else: st.error("No JSON block detected.")
    except Exception as e: st.error(f"Error: {e}")

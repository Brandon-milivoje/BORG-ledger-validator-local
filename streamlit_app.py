import streamlit as st
import json
import re
from datetime import datetime

# --- SET PAGE CONFIG ---
st.set_page_config(page_title="Borg Ledger Validator", layout="wide")

# --- BLOOMBERG-STYLE THEMING (BBGitHub Aesthetics) ---
st.markdown("""
    <style>
    /* Global Font Overrides */
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&family=Inter:wght@400;600&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    code, .stCodeBlock {
        font-family: 'Roboto Mono', monospace !important;
        background-color: #1e1e1e !important;
        color: #d4d4d4 !important;
    }

    /* Table & Row Styling */
    .row-container { 
        padding: 10px 15px; 
        border-bottom: 1px solid #3e3e3e; 
        display: flex; 
        justify-content: space-between;
        align-items: center;
    }

    /* Environment Headers */
    .env-header {
        padding: 12px 20px;
        border-radius: 4px;
        font-weight: 600;
        margin-bottom: 20px;
        border-left: 6px solid;
    }
    .env-test { background-color: #3a321d; color: #ffcc00; border-color: #ffcc00; }
    .env-prod { background-color: #1b2e1f; color: #4cd964; border-color: #4cd964; }
    .env-null { background-color: #3d1c1c; color: #ff3b30; border-color: #ff3b30; }

    /* Neutral text for Job Details */
    .detail-label { color: #8e8e93; font-weight: 500; margin-right: 8px; }
    .detail-value { color: #d1d1d6; font-family: 'Roboto Mono', monospace; }
    </style>
    """, unsafe_allow_html=True)

st.title("Bloomberg Ledger Log Validator")

# --- 1. USER INPUTS: TARGETS ---
with st.expander("🎯 Target Values (Scenario-Specific Inputs)", expanded=False):
    st.caption("Enter values you are looking for in this specific run. Blank fields will remain neutral (Review).")
    c1, c2, c3 = st.columns(3)
    t_ticker = c1.text_input("Target Ticker Value")
    t_scaling = c2.text_input("Target Scaling Factor")
    t_period = c3.text_input("Target Observation Period")
    
    st.divider()
    st.caption("Job Descriptive Expectations")
    c4, c5, c6 = st.columns(3)
    e_agent = c4.text_input("Expected Agent ID")
    e_jobname = c5.text_input("Expected Job Name")
    e_ecoticker = c6.text_input("Expected Eco Ticker")

# --- 2. PASTE AREA ---
raw_input = st.text_area("Paste Raw Log Entry Here:", height=150, placeholder="2026-02-11T... root { ...")
parse_btn = st.button("Parse and Validate Log")

# --- 3. EXPLANATION FOR USER ---
st.info("**Expected vs. Target:** 'Expected' values are strict requirements (e.g., YES/NO). 'Target' values are scenario-specific data (e.g., 0.6) entered by you for automated comparison.")

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
                send_borg = meta.get('sendToBorg')

                # --- HEADER LOGIC ---
                if is_borg == "YES":
                    st.markdown('<div class="env-header env-test">TEST / DEV / BETA (isBorgTest=YES)</div>', unsafe_allow_html=True)
                elif is_borg == "NO":
                    st.markdown('<div class="env-header env-prod">PRODUCTION ⚠️ (Ready for Results - isBorgTest=NO)</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="env-header env-null">NULL/MISSING FLAG: isBorgTest is "{is_borg}"</div>', unsafe_allow_html=True)

                col1, col2 = st.columns([3, 2])

                with col1:
                    st.subheader(f"Object {i+1} Verification")
                    
                    # Logic: (Label, Actual, Expected/Target, Type)
                    # types: 'binary', 'fixed', 'target'
                    rows = [
                        ("isBorgTest", is_borg, "YES/NO", "binary"),
                        ("sendToBorg", send_borg, "YES", "fixed"),
                        ("releaseDate", meta.get("releaseDate"), "NO RELEASE DATE", "fixed"),
                        ("tickerValue", meta.get("tickerValue"), t_ticker, "target"),
                        ("scalingFactor", meta.get("scalingFactor"), t_scaling, "target"),
                        ("observationPeriod", meta.get("observationPeriod"), t_period, "target")
                    ]

                    for label, act, goal, r_type in rows:
                        status = "👀 Review"
                        bg = "transparent"
                        display_goal = f" (Target: {goal})" if (goal and goal.strip() != "" and r_type == "target") else ""
                        
                        # Handle Nulls immediately
                        if act is None or str(act).strip() == "" or str(act).lower() == "null":
                            status = "❌ NULL/BLANK"
                            bg = "rgba(255, 59, 48, 0.15)"
                        
                        # binary check (isBorgTest)
                        elif r_type == "binary":
                            if act == "YES": 
                                status = "🧪 TEST"
                                bg = "rgba(255, 204, 0, 0.15)"
                            elif act == "NO":
                                status = "🚀 PROD ⚠️"
                                bg = "rgba(76, 217, 100, 0.15)"
                            else:
                                status = "❌ INVALID"
                                bg = "rgba(255, 59, 48, 0.15)"
                                
                        # fixed check (Strict requirements)
                        elif r_type == "fixed":
                            if act == goal:
                                status = "✅ OK"
                                bg = "rgba(76, 217, 100, 0.1)"
                            else:
                                status = "❌ MISMATCH"
                                bg = "rgba(255, 59, 48, 0.1)"
                        
                        # target check (Scenario specific)
                        elif r_type == "target" and goal and goal.strip() != "":
                            if str(act) == str(goal):
                                status = "✅ MATCH"
                                bg = "rgba(76, 217, 100, 0.1)"
                            else:
                                status = "❌ MISMATCH"
                                bg = "rgba(255, 59, 48, 0.1)"

                        st.markdown(f"""
                            <div class="row-container" style="background-color:{bg};">
                                <div><span style="font-weight:600; width:140px; display:inline-block;">{label}</span>
                                <span style="font-family:'Roboto Mono';"><code>{act}</code></span>{display_goal}</div>
                                <div style="font-weight:600; font-size: 0.85em;">{status}</div>
                            </div>
                        """, unsafe_allow_html=True)

                with col2:
                    st.subheader("Job Details")
                    
                    # CQA logic
                    w_id, c_id = meta.get("wireId"), meta.get("class")
                    cqa = " <span style='color:#4cd964; font-weight:600;'>[CQA]</span>" if (w_id == "778" and c_id == "1") else ""
                    
                    def render_detail(label, actual, expected):
                        mismatch = ""
                        if expected and expected.strip() != "" and str(actual) != str(expected):
                            mismatch = " <span style='color:#ff3b30;'>❌ Mismatch</span>"
                        st.markdown(f"<span class='detail-label'>{label}:</span><span class='detail-value'>{actual}</span>{mismatch}", unsafe_allow_html=True)

                    render_detail("Agent ID", job_props.get('agentId'), e_agent)
                    render_detail("Job Name", job_props.get('jobName'), e_jobname)
                    render_detail("Eco Ticker", job_meta.get('ecoticker'), e_ecoticker)
                    
                    st.markdown(f"<span class='detail-label'>Wire / Class:</span><span class='detail-value'>{w_id} / {c_id}</span>{cqa}", unsafe_allow_html=True)
                    st.markdown(f"<span class='detail-label'>Source URL:</span><span class='detail-value' style='font-size:0.7em;'>{content.get('sourceUrl')}</span>", unsafe_allow_html=True)
                    
                    st.divider()
                    if st.button("♻️ Reset Form"):
                        st.rerun()

        else:
            st.error("Invalid Log: No JSON data detected.")
    except Exception as e:
        st.error(f"Error parsing log: {e}")

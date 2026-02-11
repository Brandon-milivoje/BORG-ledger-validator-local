import streamlit as st
import json
import re
from datetime import datetime

# --- SET PAGE CONFIG ---
st.set_page_config(page_title="Borg Ledger Validator", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stTable td { font-size: 14px; }
    .env-prod { background-color: #28a745; color: white; padding: 15px; border-radius: 5px; font-weight: bold; border: 2px solid #1e7e34; margin-bottom: 20px; }
    .env-test { background-color: #ffc107; color: black; padding: 15px; border-radius: 5px; font-weight: bold; border: 2px solid #e0a800; margin-bottom: 20px; }
    .row-container { padding:8px; border-radius:4px; margin-bottom:4px; border-left: 5px solid transparent; border-bottom: 1px solid #f0f0f0; }
    </style>
    """, unsafe_allow_html=True)

st.title("📑 Bloomberg Ledger BORG Log Validator")

# --- 1. OPTIONAL EXPECTED VALUES ---
with st.expander("🎯 Expected Values (Optional Comparison)", expanded=False):
    c1, c2, c3 = st.columns(3)
    exp_ticker = c1.text_input("Expected Ticker Value")
    exp_scaling = c2.text_input("Expected Scaling Factor")
    exp_period = c3.text_input("Expected Observation Period")
    
    st.caption("Job Descriptive Expectations")
    c4, c5, c6 = st.columns(3)
    exp_agent = c4.text_input("Expected Agent ID")
    exp_jobname = c5.text_input("Expected Job Name")
    exp_ecoticker = c6.text_input("Expected Eco Ticker")

# --- 2. INPUT AREA ---
raw_input = st.text_area("Paste Raw Log Entry Here:", height=150)
parse_btn = st.button("Parse and Validate Log")

if raw_input and parse_btn:
    try:
        json_match = re.search(r'(\{.*\})', raw_input)
        if json_match:
            full_data = json.loads(json_match.group(1))
            data_sec = full_data.get('data', {})
            objects = data_sec.get('objects', [])
            job_props = data_sec.get('jobProperties', {})
            job_meta = data_sec.get('jobMetadata', {})

            for i, obj in enumerate(objects):
                obj_meta = obj.get('objectMetadata', {})
                content_meta = obj.get('objectContent', [{}])[0].get('contentMetadata', {})
                
                is_borg = obj_meta.get('isBorgTest')
                send_borg = obj_meta.get('sendToBorg')
                
                # Header Logic
                if is_borg == "YES":
                    st.markdown(f'<div class="env-test">🟡 ENVIRONMENT: TEST / DEV / BETA</div>', unsafe_allow_html=True)
                elif is_borg == "NO":
                    st.markdown(f'<div class="env-prod">🟢 ENVIRONMENT: PRODUCTION ⚠️</div>', unsafe_allow_html=True)

                col1, col2 = st.columns([3, 2])

                with col1:
                    st.subheader(f"Verification Table (Object {i+1})")
                    st.markdown("**Field | Actual | Target/Expected | Status**")
                    
                    rows = [
                        ("isBorgTest", is_borg, "YES or NO", "is_borg"),
                        ("sendToBorg", send_borg, "YES", "fixed"),
                        ("releaseDate", obj_meta.get("releaseDate"), "NO RELEASE DATE", "fixed"),
                        ("tickerValue", obj_meta.get("tickerValue"), exp_ticker, "variable"),
                        ("scalingFactor", obj_meta.get("scalingFactor"), exp_scaling, "variable"),
                        ("observationPeriod", obj_meta.get("observationPeriod"), exp_period, "variable")
                    ]

                    for f, act, tar, t_type in rows:
                        status = "👀 Review"
                        bg_color = "transparent"
                        
                        # --- Special isBorgTest Logic ---
                        if t_type == "is_borg":
                            if act == "YES":
                                status = "🧪 TEST MODE"
                                bg_color = "rgba(255, 193, 7, 0.3)" # Yellow
                            elif act == "NO":
                                status = "🚀 PROD ⚠️"
                                bg_color = "rgba(40, 167, 69, 0.3)" # Green
                            else:
                                status = "❌ INVALID VALUE"
                                bg_color = "rgba(220, 53, 69, 0.3)" # Red
                        
                        elif t_type == "fixed":
                            if str(act) == tar:
                                status = "✅ Match"
                                bg_color = "rgba(40, 167, 69, 0.1)"
                            else:
                                status = "❌ Mismatch"
                                bg_color = "rgba(220, 53, 69, 0.1)"
                        
                        elif t_type == "variable":
                            if tar and tar.strip() != "":
                                if str(act) == tar:
                                    status = "✅ Match"
                                    bg_color = "rgba(40, 167, 69, 0.1)"
                                else:
                                    status = "❌ Mismatch"
                                    bg_color = "rgba(220, 53, 69, 0.1)"

                        st.markdown(f"""<div class="row-container" style="background-color:{bg_color}; border-left-color:{bg_color.replace('0.1', '0.8').replace('0.3', '0.9')};">
                                    <span style="font-weight:bold; width:150px; display:inline-block;">{f}</span> 
                                    <span style="width:200px; display:inline-block;"><code>{act}</code></span>
                                    <span style="font-size:0.8em; color:gray; width:150px; display:inline-block;">Target: {tar}</span>
                                    <span style="float:right; font-weight:bold;">{status}</span>
                                    </div>""", unsafe_allow_html=True)

                with col2:
                    st.subheader("Job Details")
                    w_id, c_id = obj_meta.get("wireId"), obj_meta.get("class")
                    cqa_label = " (CQA)" if (w_id == "778" and c_id == "1") else ""
                    
                    desc_fields = [
                        ("Agent ID", job_props.get('agentId'), exp_agent),
                        ("Job Name", job_props.get('jobName'), exp_jobname),
                        ("Eco Ticker", job_meta.get('ecoticker'), exp_ecoticker)
                    ]

                    for label, act, exp in desc_fields:
                        flag = ""
                        if exp and exp.strip() != "" and str(act) != exp:
                            flag = " ❌ **Mismatch!**"
                        st.write(f"**{label}:** {act}{flag}")

                    st.write(f"**Wire / Class:** {w_id} / {c_id}{cqa_label}")
                    st.write(f"**Aux Tickers:** {job_meta.get('auxEcoTickers') or 'None'}")
                    st.write(f"**Source URL:** {content_meta.get('sourceUrl')}")

        else:
            st.error("No JSON found.")
    except Exception as e:
        st.error(f"Error: {e}")

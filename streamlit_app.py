import streamlit as st
import json
import re
from datetime import datetime  # <--- The missing piece that caused the error!

# --- SET PAGE CONFIG ---
st.set_page_config(page_title="Borg Ledger Validator", layout="wide")

# --- CUSTOM CSS FOR HIGHLIGHTING & STYLING ---
st.markdown("""
    <style>
    .stTable td { font-size: 14px; }
    /* Success/Green for PROD */
    .env-prod { background-color: #28a745; color: white; padding: 15px; border-radius: 5px; font-weight: bold; border: 2px solid #1e7e34; }
    /* Warning/Yellow for TEST */
    .env-test { background-color: #ffc107; color: black; padding: 15px; border-radius: 5px; font-weight: bold; border: 2px solid #e0a800; }
    </style>
    """, unsafe_allow_html=True)

st.title("📑 Bloomberg Ledger Log Validator")

# --- SIDEBAR LEGEND ---
with st.sidebar:
    st.header("Status Legend")
    st.write("✅ **Match**: Value matches your expectation.")
    st.write("👀 **Review**: No expectation provided; check manually.")
    st.write("❌ **Mismatch/Missing**: Data does not match target or is empty.")
    st.divider()
    if st.button("♻️ Reset App"):
        st.rerun()

# --- 1. OPTIONAL EXPECTED VALUES ---
with st.expander("🎯 Expected Values (Optional Comparison)", expanded=False):
    st.info("Leave these blank if you only want to parse without a comparison.")
    c1, c2, c3 = st.columns(3)
    exp_ticker = c1.text_input("Expected Ticker Value (e.g. 3.2)")
    exp_scaling = c2.text_input("Expected Scaling Factor (e.g. 1)")
    exp_period = c3.text_input("Expected Observation Period (e.g. 12 2025)")

# --- 2. INPUT AREA ---
raw_input = st.text_area("Paste Raw Log Entry Here:", height=200, placeholder="Paste the log string starting with the date or { ...")
parse_btn = st.button("Parse and Validate Log")

if raw_input and parse_btn:
    try:
        # Extract JSON block
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
                
                # --- 3. DYNAMIC ENVIRONMENT HEADER ---
                if is_borg == "YES":
                    st.markdown(f'<div class="env-test">🟡 ENVIRONMENT: TEST / DEV / BETA (isBorgTest=YES)</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="env-prod">🟢 ENVIRONMENT: PRODUCTION ⚠️ (Live Release Ready - isBorgTest=NO)</div>', unsafe_allow_html=True)

                st.write("") # Spacer
                col1, col2 = st.columns([3, 2])

                with col1:
                    st.subheader(f"Data Object {i+1} Verification")
                    
                    # Logic for Table Highlighting Status
                    def get_row_status(current, expected, is_fixed=False):
                        if current is None or str(current).strip() == "": return "❌ Missing"
                        if is_fixed:
                            return "✅ Match" if str(current) == str(expected) else "❌ Mismatch"
                        if not expected or expected.strip() == "": return "👀 Review"
                        return "✅ Match" if str(current) == str(expected) else "❌ Mismatch"

                    # Data for Verification Table
                    check_rows = [
                        ("isBorgTest", is_borg, "YES" if is_borg == "YES" else "NO", True),
                        ("sendToBorg", send_borg, "YES", True),
                        ("releaseDate", obj_meta.get("releaseDate"), "NO RELEASE DATE", True),
                        ("tickerValue", obj_meta.get("tickerValue"), exp_ticker, False),
                        ("scalingFactor", obj_meta.get("scalingFactor"), exp_scaling, False),
                        ("observationPeriod", obj_meta.get("observationPeriod"), exp_period, False),
                        ("wireId", obj_meta.get("wireId"), "778", True),
                    ]

                    # Display logic with color coding
                    audit_text = f"Audit Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    audit_text += f"Job Name: {job_props.get('jobName')}\n"
                    audit_text += "-"*50 + "\n"
                    
                    st.markdown("**Field | Actual | Expected | Status**")
                    for f, act, exp, fixed in check_rows:
                        status = get_row_status(act, exp, fixed)
                        # Light Red/Green backgrounds for the rows
                        bg_color = "rgba(40, 167, 69, 0.15)" if "✅" in status else ("rgba(220, 53, 69, 0.15)" if "❌" in status else "rgba(255, 193, 7, 0.05)")
                        
                        st.markdown(f"""<div style="background-color:{bg_color}; padding:8px; border-radius:4px; margin-bottom:4px; border-left: 5px solid {bg_color};">
                                    <span style="font-weight:bold; width:150px; display:inline-block;">{f}</span> 
                                    <span style="display:inline-block; width:200px;">Value: <code>{act}</code></span>
                                    <span style="font-size:0.85em; color:gray;">(Target: {exp if exp else 'N/A'})</span>
                                    <span style="float:right; font-weight:bold;">{status}</span>
                                    </div>""", unsafe_allow_html=True)
                        audit_text += f"{f}: {act} | Expected: {exp} | {status}\n"

                with col2:
                    st.subheader("Job Descriptive Details")
                    w_id, c_id = obj_meta.get("wireId"), obj_meta.get("class")
                    wire_dest = "CQA" if (w_id == "778" and c_id == "1") else "Other"
                    
                    st.info(f"🔹 **Job Name:** {job_props.get('jobName')}\n\n"
                            f"🔹 **Agent ID:** {job_props.get('agentId')}\n\n"
                            f"🔹 **Eco Ticker:** {job_meta.get('ecoticker')}\n\n"
                            f"🔹 **Wire / Class:** {w_id} / {c_id} ({wire_dest})\n\n"
                            f"🔹 **Source:** {content_meta.get('sourceUrl')}")
                    
                    # Audit Copy Button
                    st.download_button("📥 Download Audit Report (.txt)", audit_text, file_name=f"audit_{job_meta.get('ecoticker')}_{datetime.now().strftime('%H%M%S')}.txt")

                if is_borg == "YES" and send_borg == "NO":
                    st.error("🚨 **ROUTING ALERT:** isBorgTest is 'YES' but sendToBorg is 'NO'. Data will NOT reach the testing destination.")

        else:
            st.error("❌ No JSON found. Ensure you copied the full string.")
    except Exception as e:
        st.error(f"⚠️ Parsing error: {e}")

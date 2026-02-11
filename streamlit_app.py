import streamlit as st
import json
import re

# --- SET PAGE CONFIG ---
st.set_page_config(page_title="Borg Ledger Validator", layout="wide")

# --- CUSTOM CSS FOR HIGHLIGHTING ---
st.markdown("""
    <style>
    .val-match { background-color: rgba(40, 167, 69, 0.2); padding: 5px; border-radius: 3px; }
    .val-mismatch { background-color: rgba(220, 53, 69, 0.2); padding: 5px; border-radius: 3px; }
    .stTable td { font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📑 Bloomberg Ledger Log Validator")

# --- 1. OPTIONAL EXPECTED VALUES ---
with st.expander("🎯 Expected Values (Optional Comparison)", expanded=False):
    st.info("Leave these blank if you only want to parse the log without comparison.")
    c1, c2, c3 = st.columns(3)
    exp_ticker = c1.text_input("Expected Ticker Value (e.g. 0.6)")
    exp_scaling = c2.text_input("Expected Scaling Factor (e.g. 1)")
    exp_period = c3.text_input("Expected Observation Period (e.g. 12 2025)")

# --- 2. INPUT AREA ---
raw_input = st.text_area("Paste Raw Log Entry Here:", height=200)
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
                
                # --- 3. DYNAMIC ENVIRONMENT HEADER ---
                if is_borg == "YES":
                    st.warning("🟡 ENVIRONMENT: TEST / DEV / BETA")
                else:
                    st.success("🟢 ENVIRONMENT: PRODUCTION ⚠️ (Live Release Ready)")

                st.divider()
                col1, col2 = st.columns([3, 2])

                with col1:
                    st.subheader(f"Data Object {i+1} Verification")
                    
                    # Logic for Table Highlighting
                    def get_row_style(current, expected, is_fixed=False):
                        if not current: return "❌ Missing"
                        if is_fixed: # For things like NO RELEASE DATE
                            return "✅" if current == expected else "❌ Mismatch"
                        if not expected: return "👀 Review"
                        return "✅ Match" if str(current) == str(expected) else "❌ Mismatch"

                    # Data for Table
                    check_rows = [
                        ("isBorgTest", is_borg, "YES" if is_borg == "YES" else "NO", True),
                        ("sendToBorg", send_borg, "YES", True),
                        ("releaseDate", obj_meta.get("releaseDate"), "NO RELEASE DATE", True),
                        ("tickerValue", obj_meta.get("tickerValue"), exp_ticker, False),
                        ("scalingFactor", obj_meta.get("scalingFactor"), exp_scaling, False),
                        ("observationPeriod", obj_meta.get("observationPeriod"), exp_period, False),
                        ("wireId", obj_meta.get("wireId"), "778", True),
                    ]

                    # Display formatted validation
                    st.markdown("**Field | Actual | Expected | Status**")
                    audit_text = f"Audit Report - {datetime.now()}\n"
                    for f, act, exp, fixed in check_rows:
                        status = get_row_style(act, exp, fixed)
                        color = "rgba(40, 167, 69, 0.1)" if "✅" in status else ("rgba(220, 53, 69, 0.1)" if "❌" in status else "transparent")
                        st.markdown(f"""<div style="background-color:{color}; padding:5px; border-bottom:1px solid #eee;">
                                    <b>{f}</b>: {act} <small>(Exp: {exp if exp else 'N/A'})</small> — {status}
                                    </div>""", unsafe_allow_html=True)
                        audit_text += f"{f}: {act} | Status: {status}\n"

                with col2:
                    st.subheader("Job Details")
                    w_id, c_id = obj_meta.get("wireId"), obj_meta.get("class")
                    wire_dest = "CQA" if (w_id == "778" and c_id == "1") else "Other"
                    
                    st.write(f"🔹 **Job Name:** {job_props.get('jobName')}")
                    st.write(f"🔹 **Eco Ticker:** {job_meta.get('ecoticker')}")
                    st.write(f"🔹 **Wire/Class:** {w_id} / {c_id} ({wire_dest})")
                    st.write(f"🔹 **Source:** {content_meta.get('sourceUrl')}")
                    
                    # Audit Copy Button
                    st.download_button("📋 Download Audit Log", audit_text, file_name=f"audit_{job_meta.get('ecoticker')}.txt")

                if is_borg == "YES" and send_borg == "NO":
                    st.error("🚨 ROUTING ERROR: isBorgTest is YES but sendToBorg is NO!")

        else:
            st.error("Invalid log format.")
    except Exception as e:
        st.error(f"Error: {e}")

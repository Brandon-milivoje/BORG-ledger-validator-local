import streamlit as st
import json
import re
from datetime import datetime

st.set_page_config(page_title="Borg Ledger Validator", layout="wide")

# Sidebar Legend for quick reference
with st.sidebar:
    st.header("Status Legend")
    st.write("✅ **Verified**: Correct for environment.")
    st.write("👀 **Manual**: Value varies; verify manually.")
    st.write("⚠️ **Review**: Deviation from standard.")
    st.write("❌ **Missing**: Field is empty/null.")
    st.divider()
    st.info("Note: Wire 778 + Class 1 = CQA")

st.title("📑 Bloomberg Ledger Log Validator")

raw_input = st.text_area("Paste Raw Log Entry Here:", height=250, placeholder="2026-02-11T20... root { ... }")

# Explicit Parse Button
if st.button("Parse and Validate Log"):
    if not raw_input:
        st.warning("Please paste a log entry first.")
    else:
        try:
            json_match = re.search(r'(\{.*\})', raw_input)
            if not json_match:
                st.error("❌ Could not find a valid JSON block in the pasted text.")
            else:
                full_data = json.loads(json_match.group(1))
                data_sec = full_data.get('data', {})
                objects = data_sec.get('objects', [])
                job_props = data_sec.get('jobProperties', {})
                job_meta = data_sec.get('jobMetadata', {})

                for i, obj in enumerate(objects):
                    obj_meta = obj.get('objectMetadata', {})
                    content_meta = obj.get('objectContent', [{}])[0].get('contentMetadata', {})
                    
                    # --- Logic Checks ---
                    is_borg = obj_meta.get('isBorgTest')
                    send_borg = obj_meta.get('sendToBorg')
                    env_label = "TEST/DEV/BETA (YES)" if is_borg == "YES" else "PRODUCTION (NO)"
                    
                    st.divider()
                    st.subheader(f"Data Object {i+1} of {len(objects)}")
                    
                    col1, col2 = st.columns([3, 2])
                    
                    with col1:
                        st.markdown("### Critical Confirmations")
                        check_list = [
                            {"Field": "isBorgTest", "Value": is_borg, "Target": None},
                            {"Field": "sendToBorg", "Value": send_borg, "Target": "YES"},
                            {"Field": "wireId", "Value": obj_meta.get("wireId"), "Target": "778"},
                            {"Field": "tickerValue", "Value": obj_meta.get("tickerValue"), "Target": "MANUAL"},
                            {"Field": "scalingFactor", "Value": obj_meta.get("scalingFactor"), "Target": "MANUAL"},
                            {"Field": "observationPeriod", "Value": obj_meta.get("observationPeriod"), "Target": "MANUAL"},
                            {"Field": "headline", "Value": obj_meta.get("headline"), "Target": "MANUAL"},
                            {"Field": "releaseDate", "Value": obj_meta.get("releaseDate"), "Target": "NO RELEASE DATE"}
                        ]
                        
                        # Process Status for Table
                        formatted_checks = []
                        for item in check_list:
                            val = str(item["Value"])
                            status = "✅"
                            if not val or val == "None" or val.strip() == "":
                                status = "❌"
                            elif item["Target"] == "MANUAL":
                                status = "👀"
                            elif item["Target"] and val != item["Target"]:
                                status = "⚠️"
                            
                            formatted_checks.append({"Field": item["Field"], "Value": val, "Status": status})
                        
                        st.table(formatted_checks)

                    with col2:
                        st.markdown("### Job Descriptives")
                        st.success(f"**Environment Setting:** {env_label}")
                        
                        # Wire/Class Logic
                        w_id, c_id = obj_meta.get("wireId"), obj_meta.get("class")
                        wire_dest = "CQA" if (w_id == "778" and c_id == "1") else "Other"
                        
                        st.write(f"🔹 **Agent ID:** {job_props.get('agentId')}")
                        st.write(f"🔹 **Job Name:** {job_props.get('jobName')}")
                        st.write(f"🔹 **Eco Ticker:** {job_meta.get('ecoticker')}")
                        st.write(f"🔹 **Aux Tickers:** {job_meta.get('auxEcoTickers') or 'None'}")
                        st.write(f"🔹 **Wire / Class:** {w_id} / {c_id} ({wire_dest})")
                        st.write(f"🔹 **Source URL:** {content_meta.get('sourceUrl')}")

                    # Borg Consistency Alert
                    if is_borg == "YES" and send_borg == "NO":
                        st.error("🚨 ALERT: isBorgTest is YES but sendToBorg is NO! This may cause routing issues.")

        except Exception as e:
            st.error(f"Failed to parse log. Error: {e}")
